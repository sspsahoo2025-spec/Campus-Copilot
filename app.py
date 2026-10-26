from pathlib import Path
import tempfile
import pandas as pd
import streamlit as st
from services.data_store import load_roles, load_companies
from services.skill_engine import extract_skills, role_match, preparation_plan
from services.rag_engine import search, retrieval_status
from services.answer_engine import generate_answer
from services.test_engine import series as test_series, get_test, score as test_score, combined_readiness
from services.predictor_engine import load_bundle, predict as predict_placement
from services.resume_matcher import match_resume
from services.document_engine import read_file as read_document
from services import ocr_engine

BASE=Path(__file__).resolve().parent
DOCS=BASE/'documents'
st.set_page_config(page_title='Campus Copilot', page_icon='🎓', layout='wide')


@st.cache_resource
def placement_bundle():
    return load_bundle()


st.title('🎓 Campus Copilot')
st.caption('Academic assistant + placement and career intelligence platform')
roles=load_roles(); companies=load_companies()

tab1,tab2,tab3,tab4,tab5,tab6,tab7,tab8=st.tabs([
    '🏫 Academic Assistant','🎯 Career Matcher','🏢 Hiring Explorer','🗺️ Preparation Guide',
    '🧪 Skills Test','📈 Placement Predictor','🧾 Resume Matcher','✍️ Notes → PDF'])

with tab1:
    st.subheader('Campus knowledge assistant')
    st.caption(f'Retrieval mode: {retrieval_status()}')
    uploads=st.file_uploader('Add campus PDF, DOCX, or TXT files', type=['pdf','docx','txt'], accept_multiple_files=True)
    for f in uploads:
        (DOCS/f.name).write_bytes(f.getbuffer())
    if uploads:
        st.success(f'Added {len(uploads)} file(s) to the knowledge base.')

    st.session_state.setdefault('chat', [])
    if st.button('Clear chat'):
        st.session_state.chat=[]

    for msg in st.session_state.chat:
        with st.chat_message(msg['role']):
            st.markdown(msg['content'])
            if msg.get('sources'):
                with st.expander('Sources and relevance'):
                    for source,text,score in msg['sources']:
                        st.markdown(f'**{source}** • relevance {score:.2f}')
                        st.write(text)

    prompt=st.chat_input('Ask about attendance, fees, placements, syllabus...')
    if prompt:
        st.session_state.chat.append({'role':'user','content':prompt})
        with st.chat_message('user'):
            st.markdown(prompt)
        with st.chat_message('assistant'):
            with st.spinner('Searching approved documents...'):
                hits=search(DOCS,prompt,top_k=4)
                answer,mode=generate_answer(prompt,hits)
            st.markdown(answer)
            badge={'llm':'LLM (grounded in sources)','extractive':'Extractive (grounded in sources)','no_context':'No confident source found'}.get(mode,mode)
            st.caption(f'Answer mode: {badge}')
            shown=hits if mode!='no_context' else hits[:2]
            if shown:
                with st.expander('Sources and relevance'):
                    for source,text,score in shown:
                        st.markdown(f'**{source}** • relevance {score:.2f}')
                        st.write(text)
        st.session_state.chat.append({'role':'assistant','content':answer,'sources':shown})
    st.info('The assistant answers only from approved documents and cites its sources. It does not invent an answer when no source matches.')

with tab2:
    st.subheader('Match current skills to roles')
    profile=st.text_area('Paste skills or resume text', placeholder='Python, SQL, Excel, Power BI...')
    if st.button('Analyze role fit') and profile:
        skills=extract_skills(profile)
        st.write('Detected skills:', ', '.join(skills) if skills else 'None from current skill dictionary')
        results=[]
        for _,r in roles.iterrows():
            score,present,missing=role_match(skills,r.core_skills)
            results.append({'Role':r.role,'Match %':score,'Matched':', '.join(present),'Missing':', '.join(missing)})
        st.dataframe(pd.DataFrame(results).sort_values('Match %',ascending=False),use_container_width=True,hide_index=True)

with tab3:
    st.subheader('Companies and role requirements')
    role=st.selectbox('Select role',roles.role.tolist(),key='hiring_role')
    data=companies[companies.role==role].copy()
    st.warning('Current rows are clearly labeled demo seed data. Replace them with verified job postings before presentation.')
    if data.empty: st.info('No company records yet for this role.')
    else:
        st.dataframe(data[['company','location','ctc_min_lpa','ctc_max_lpa','requirements','status','last_verified']],use_container_width=True,hide_index=True)
    st.download_button('Download hiring data CSV',data.to_csv(index=False),file_name=f'{role}_hiring.csv',mime='text/csv')

with tab4:
    st.subheader('Role-specific preparation guide')
    role=st.selectbox('Target role',roles.role.tolist(),key='prep_role')
    row=roles[roles.role==role].iloc[0]
    known=st.multiselect('Skills already known',[x.strip() for x in row.core_skills.split(',')])
    score,present,missing=role_match(known,row.core_skills)
    st.metric('Readiness based on listed core skills',f'{score}%')
    st.write('**Core skills:**',row.core_skills)
    st.write('**Missing skills:**',', '.join(missing) if missing else 'None')
    for i,(phase,items) in enumerate(preparation_plan(role,missing),1):
        with st.expander(f'Phase {i}: {phase}',expanded=True):
            for item in items: st.write('•',item)
    st.markdown('**Evaluator explanation:** The score is a transparent skill-overlap percentage, not an employment prediction.')

with tab5:
    st.subheader('Three-part skills test')
    st.caption('Three medium-to-hard series — CS fundamentals (MCQ), programming/DSA, and aptitude & reasoning. '
               'Your average across the series feeds the Placement Predictor. In a hurry? Skip and self-rate below.')
    st.session_state.setdefault('test_scores',{})
    names=test_series()
    inner=st.tabs([f'① {names[0]}',f'② {names[1]}',f'③ {names[2]}'])
    for si,sname in enumerate(names):
        with inner[si]:
            qkey=f'testq::{sname}'
            if qkey not in st.session_state:
                st.session_state[qkey]=get_test(sname,5,seed=sum(map(ord,sname)))
            quiz=st.session_state[qkey]
            with st.form(f'testform::{sname}'):
                answers={}
                for i,item in enumerate(quiz):
                    answers[i]=st.radio(f'Q{i+1}. {item["q"]}',options=list(range(len(item['options']))),
                                        format_func=lambda x,it=item: it['options'][x],
                                        key=f'testans::{sname}::{i}',index=None)
                submitted=st.form_submit_button(f'Submit — {sname}')
            if submitted:
                clean={i:(a if a is not None else -1) for i,a in answers.items()}
                pct,correct,total=test_score(quiz,clean)
                st.session_state['test_scores'][sname]=pct
                st.metric(f'{sname} score',f'{pct}%',help=f'{correct} of {total} correct')
                with st.expander('Review answers',expanded=True):
                    for i,item in enumerate(quiz):
                        user=clean.get(i,-1)
                        ok=user==item['answer']
                        st.markdown(f'**Q{i+1}. {item["q"]}**')
                        picked=item['options'][user] if user>=0 else '— (left blank)'
                        st.write(('✅ ' if ok else '❌ ')+'Your answer: '+picked)
                        if not ok:
                            st.write('Correct answer: '+item['options'][item['answer']])
                        if item.get('explain'): st.caption(item['explain'])
    scores=st.session_state.get('test_scores',{})
    if scores:
        combined=combined_readiness(scores)
        st.session_state['mcq_readiness']=combined
        st.success(f'Combined readiness: **{combined}%** from {len(scores)}/3 series. This auto-fills the Placement Predictor.')
    st.divider()
    st.markdown('**In a hurry?** Skip the test and self-rate your readiness.')
    colA,colB=st.columns([3,1])
    self_rate=colA.slider('Self-rated readiness',0,100,int(st.session_state.get('mcq_readiness') or 60),key='self_rate')
    if colB.button('Use self-rating'):
        st.session_state['mcq_readiness']=self_rate
        st.success(f'Using {self_rate}% as your readiness score.')

with tab6:
    st.subheader('Placement predictor and expected package')
    st.caption('Two ML models trained on a synthetic, reproducible dataset. All metrics below come from a held-out test split.')
    bundle=placement_bundle()
    c1,c2=st.columns(2)
    with c1:
        cgpa=st.slider('CGPA',4.5,10.0,7.5,0.1)
        skills_count=st.slider('Number of relevant skills',0,14,6)
        projects=st.slider('Projects completed',0,8,2)
        internships=st.slider('Internships',0,3,1)
    with c2:
        backlogs=st.slider('Active backlogs',0,6,0)
        default_score=int(st.session_state.get('mcq_readiness',60))
        test_score=st.slider('Domain test score',0,100,default_score,
                             help='Auto-filled from your Skills Test result when available.')
        communication=st.slider('Communication (1-10)',1,10,6)
        certifications=st.slider('Certifications',0,6,1)
    if st.session_state.get('mcq_readiness') is not None:
        st.caption(f"Using your Skills Test readiness ({st.session_state['mcq_readiness']}%) as the default test score.")
    if st.button('Predict placement'):
        feats={'cgpa':cgpa,'skills_count':skills_count,'projects':projects,'internships':internships,
               'backlogs':backlogs,'test_score':test_score,'communication':communication,'certifications':certifications}
        res=predict_placement(feats,bundle)
        m1,m2=st.columns(2)
        m1.metric('Placement probability',f"{res['placement_probability']*100:.1f}%")
        m2.metric('Likely outcome','Placed' if res['placed'] else 'Not placed yet')
        st.progress(min(1.0,res['placement_probability']))
        if res['placed']:
            st.metric('Estimated package',f"{res['expected_package_lpa']} LPA")
        else:
            st.info(f"If placed, the model estimates about {res['package_if_placed_lpa']} LPA. Improve the highest-impact factors below to cross the line.")
    with st.expander('Model evaluation (held-out test set)'):
        cm=bundle['cls_metrics']; rm=bundle['reg_metrics']
        a1,a2,a3=st.columns(3)
        a1.metric('Classifier accuracy',f"{cm['accuracy']*100:.1f}%")
        a2.metric('ROC-AUC',f"{cm['roc_auc']:.3f}")
        a3.metric('Test samples',cm['n_test'])
        st.write('Confusion matrix (rows = actual, columns = predicted):')
        st.table(pd.DataFrame(cm['confusion'],index=['actual: not placed','actual: placed'],
                              columns=['pred: not placed','pred: placed']))
        b1,b2,b3=st.columns(3)
        b1.metric('Salary RMSE',f"{rm['rmse']:.2f} LPA")
        b2.metric('Salary MAE',f"{rm['mae']:.2f} LPA")
        b3.metric('Salary R²',f"{rm['r2']:.3f}")
        st.write('Feature importance (placement classifier):')
        st.bar_chart(pd.Series(bundle['importances']).sort_values(ascending=False))
    st.caption('Educational estimate from synthetic data — not a guarantee of employment.')

with tab7:
    st.subheader('Resume to role and company matcher')
    st.caption('Upload a resume; the app ranks the best-fit roles and companies using semantic similarity.')
    up=st.file_uploader('Upload resume (PDF, DOCX, or TXT)',type=['pdf','docx','txt'],key='resume_up')
    resume_text=''
    if up is not None:
        with tempfile.NamedTemporaryFile(delete=False,suffix=Path(up.name).suffix) as tmp:
            tmp.write(up.getbuffer()); tmp_path=tmp.name
        resume_text=read_document(tmp_path)
    pasted=st.text_area('...or paste resume text',height=140,placeholder='Python, SQL, built a dashboard project, ML internship...')
    resume_text=(resume_text+'\n'+pasted).strip()
    if st.button('Find best-fit roles') and resume_text:
        res=match_resume(resume_text,roles,companies,top_k=5)
        st.caption(f"Matching backend: {res['backend']}")
        st.write('**Detected skills:**',', '.join(res['detected_skills']) or 'None recognized from the skill dictionary')
        st.markdown('### Best-fit roles')
        st.dataframe(pd.DataFrame([{'Role':r['role'],'Fit %':round(r['score']*100)} for r in res['roles']]),
                     hide_index=True,use_container_width=True)
        if res['best_role']:
            st.markdown(f"### Top role: {res['best_role']}")
            st.write('**You already have:**',', '.join(res['present_skills']) or '—')
            st.write('**Consider adding:**',', '.join(res['missing_skills']) or 'None — strong match')
        if res['companies']:
            st.markdown('### Suggested companies for the top role')
            st.dataframe(pd.DataFrame([{'Company':c['company'],'Location':c['location'],'CTC':c['ctc'],
                                        'Fit %':round(c['score']*100)} for c in res['companies']]),
                         hide_index=True,use_container_width=True)
        else:
            st.info('No seed companies for the top role yet. Add rows to data/companies.csv.')

with tab8:
    st.subheader('Handwritten notes to searchable PDF')
    st.caption('High-accuracy handwriting recognition via a cloud OCR service, exported as a clean PDF.')
    providers=ocr_engine.available_providers()
    if not providers:
        st.warning('No cloud OCR provider is configured yet. Set one of these, then restart the app:')
        st.code('setx GOOGLE_VISION_API_KEY "your-key"\n:: or Azure AI Vision\nsetx AZURE_VISION_ENDPOINT "https://<resource>.cognitiveservices.azure.com/"\nsetx AZURE_VISION_KEY "your-key"',language='bat')
        st.caption('Keys are read from environment variables and are never stored by the app.')
    img=st.file_uploader('Upload a photo or scan of handwritten notes',type=['png','jpg','jpeg','bmp','tiff','webp'],key='ocr_up')
    provider=st.selectbox('OCR provider',providers or ['(none configured)'],key='ocr_provider')
    embed_img=st.checkbox('Include the source image in the PDF',value=True)
    if img is not None:
        st.image(img,caption='Uploaded note')
    if st.button('Recognize and build PDF',disabled=(not providers or img is None)):
        try:
            image_bytes=img.getvalue()
            with st.spinner('Recognizing handwriting...'):
                text=ocr_engine.ocr_image(image_bytes,provider=provider)
            if not text:
                st.warning('No text was detected. Try a clearer, well-lit, higher-resolution image.')
            else:
                st.text_area('Recognized text',text,height=200)
                pdf_bytes=ocr_engine.text_to_pdf(text,image_bytes=image_bytes if embed_img else None)
                st.download_button('Download PDF',pdf_bytes,file_name='digitized_notes.pdf',mime='application/pdf')
                st.download_button('Download plain text',text,file_name='digitized_notes.txt',mime='text/plain')
        except Exception as exc:
            st.error(f'OCR failed: {exc}')
