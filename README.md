# ApplyLens — Job Application Intelligence Platform

A portfolio-grade career CRM built with **Python (Flask) only** — the entire UI is
**server-rendered HTML + CSS with zero JavaScript**.

Every analysis feature is **rule-based and transparent**: no black-box "AI score"
anywhere. Each claim (a skill matched, a check failed) shows the evidence it came from.

## Features

| Area | What you get |
|---|---|
| **Auth** | Signup/login (Flask-Login), per-user data isolation (verified by tests) |
| **Resume intelligence** | PDF/DOCX extraction, section detection, skills, contact, education, experience, projects, certifications |
| **Version management** | Unlimited versions, archive/restore/delete, side-by-side comparison (skills added/lost, score deltas) |
| **Health analyzer** | Transparent 100-point checklist (contact, structure, skills evidence, quantified impact, action verbs) — explicitly *not* an objective measure |
| **JD analyzer** | Paste a posting → structured record (role, company, location, salary, experience, remote) + required vs preferred skills |
| **Keyword explorer** | Technical + soft-skill frequency profile of every posting |
| **Matching engine** | Resume ↔ job coverage with per-skill bars, mention counts, and quoted evidence from your resume |
| **Skill gap analyzer** | Have / need-to-strengthen / not-detected triage + self-tracking (Not Started → Expert) |
| **Application tracker** | 9 statuses, pipeline board, CSV export |
| **Interview tracking** | Rounds, modes, outcomes, upcoming feed |
| **Analytics** | Funnel, applied-vs-rejected over 8 weeks, company stats, skill demand across your JDs, resume usage |
| **Reports** | 4 PDF report types (reportlab) + text/CSV exports |
| **Search** | Full-text search across company/role/notes/JD + filters (status, company, technology, remote) and 5 sort orders |

## Run it

```bash
pip install -r requirements.txt
python run.py          # http://127.0.0.1:5000
```

The SQLite database (`instance/app.db`) is created automatically on first run.

## Test it

```bash
python smoke_test.py   # 35 end-to-end checks via Flask test client
```

## Project structure

```
run.py                  entry point
config.py               configuration
app/
  __init__.py           app factory
  extensions.py         db, login manager
  models.py             User, Resume, Job, Application, Interview, UserSkill
  routes/               auth, dashboard, resumes, jobs, applications, analytics, reports
  utils/
    skills.py           curated skill dictionary (200+ aliases) & soft skills
    extract.py          PDF (pdfplumber) / DOCX (python-docx) text extraction
    parser.py           section detection, skill evidence, JD parsing, keywords
    analyzer.py         resume health checklist scorer
    matcher.py          transparent resume↔job matching with evidence
    diff.py             resume version comparison
    pdf_reports.py      reportlab PDF report builders
  templates/            Jinja2 (HTML only)
  static/css/style.css  all styling (CSS only)
```

## Notes / limitations (honest ones)

- Scanned/image PDFs can't be parsed (no OCR) — the app tells you when extraction fails.
- Matching coverage is a **weighted ratio** (required ×3, preferred ×1), not a prediction.
- JD skill extraction relies on a curated dictionary; unknown skills land in the
  keyword profile instead of the skill list.
- Health score weights are visible heuristics, deliberately not presented as truth.
