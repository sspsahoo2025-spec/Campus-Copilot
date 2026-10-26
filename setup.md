# Campus Copilot 1.0 — Setup & Guide

Campus Copilot is an offline-first **RAG academic assistant + placement/career intelligence platform**.
Version **1.0** is the original 8-tab layout (each feature on its own tab), with an enriched sample
dataset so every tab shows meaningful content out of the box.

---

## 1. Prerequisites
- **Windows** with **Python 3.10 – 3.12** installed and on PATH (`python --version`).
- An **internet connection for the first setup only** (to install packages and download the
  ~80 MB embedding model the first time you ask a question).

## 2. Install (one time)
Double-click **`setup.bat`**. It will:
1. create a local virtual environment (`.venv`),
2. install everything in `requirements.txt`,
3. pre-train the placement models so the app opens instantly.

> No PATH changes are needed — the scripts always use the venv's own Python and run from their own
> folder, so there are no path issues wherever you copy this folder.

## 3. Run
Double-click **`run.bat`**. The app opens at **http://localhost:8501**.
Stop it with `Ctrl+C` in the black window (or just close the window).

If Windows blocks the script, run this once in PowerShell, then retry:
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

---

## The 8 tabs
1. **🏫 Academic Assistant** — RAG chatbot. Answers *only* from the documents in `documents/`,
   cites its sources, and refuses when nothing relevant is found. Upload your own PDF/DOCX/TXT to
   extend the knowledge base live.
2. **🎯 Career Matcher** — paste your skills; it scores your fit against every role.
3. **🏢 Hiring Explorer** — sample companies, locations, CTC ranges and requirements per role.
4. **🗺️ Preparation Guide** — a phased prep plan for a target role based on your missing skills.
5. **🧪 Skills Test** — a short domain MCQ quiz; the score feeds the Placement Predictor.
6. **📈 Placement Predictor** — two gradient-boosted ML models estimate placement probability and
   expected package, with held-out evaluation metrics.
7. **🧾 Resume Matcher** — upload a resume; it ranks best-fit roles and companies by semantic similarity.
8. **✍️ Notes → PDF** — handwriting OCR to a clean PDF (needs a free Google Vision or Azure Vision key).

## Data you can edit
- `documents/campus_handbook.txt` — the sample knowledge base (replace with your college's real docs).
- `data/roles.csv`, `data/companies.csv` — roles and hiring data shown across the career tabs.
- `data/mcq_bank.json` — the Skills Test question bank.
- `data/placement_dataset.csv` + `models/` — auto-generated on setup; delete them to regenerate.

## Notes
- All company/CTC rows are clearly labeled **“Representative sample”** — replace with verified
  postings before any official use.
- The placement models are trained on a **synthetic, reproducible** dataset; the mechanism is real
  ML and swapping in real records needs no code change.
- **OCR is optional** and cloud-based. Without a key, the other seven tabs work fully.

## Troubleshooting
| Problem | Fix |
|---|---|
| `python` not found | Install Python 3.10–3.12 and tick “Add to PATH”, then re-run `setup.bat`. |
| Script won’t start | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` in PowerShell, then retry. |
| First question is slow | It’s downloading the embedding model once; later questions are fast. |
| Port already in use | `.venv\Scripts\python.exe -m streamlit run app.py --server.port 8502` |
