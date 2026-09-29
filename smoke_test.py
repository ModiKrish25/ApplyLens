"""End-to-end smoke test using Flask's test client (no server needed)."""
import os
import sys
import io

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User, Resume, Job, Application, Interview

app = create_app()

RESUME_TEXT = """Ada Lovelace
ada@example.com | +91 98765 43210
linkedin.com/in/adalovelace | github.com/ada

SUMMARY
Backend developer with 3 years of experience building REST APIs.

SKILLS
Python, Django, Flask, PostgreSQL, MySQL, Docker, Git, Redis, HTML, CSS

EXPERIENCE
Software Engineer - Jan 2022 - Present
- Built and maintained 12 REST endpoints using Django and PostgreSQL
- Improved query performance by 40% and reduced latency by 200ms
- Automated deployments with Docker and GitHub Actions, saving 5 hours weekly

Junior Developer - Aug 2020 - Dec 2021
- Developed 8 features for the company dashboard used by 2000 users
- Wrote pytest tests increasing coverage from 40% to 85%

EDUCATION
B.Tech Computer Science, Example University, 2020

PROJECTS
- Job board scraper: Built with Python and PostgreSQL, processed 10k listings

CERTIFICATIONS
AWS Certified Cloud Practitioner
"""

JOB_TEXT = """Company: TechCorp
Role: Backend Developer
Location: Remote
Job Type: Full-time
Experience: 2+ years

Required skills:
- Python, Django, REST API development
- PostgreSQL and Docker
- Git

Preferred:
Redis, Celery, AWS, Kubernetes

Responsibilities:
- Design and build REST APIs with Django
- Work with PostgreSQL databases
- Communication and teamwork are important
"""


def run():
    client = app.test_client()
    ok = []

    def check(name, cond, extra=""):
        ok.append((name, bool(cond)))
        print(("PASS" if cond else "FAIL"), name, extra)

    # --- auth
    r = client.post("/signup", data={"email": "ada@example.com", "name": "Ada",
                                     "password": "Secret1!", "confirm": "Secret1!"},
                    follow_redirects=True)
    check("signup", r.status_code == 200 and b"Dashboard" in r.data)

    # --- upload a generated DOCX resume
    import docx as docxlib
    d = docxlib.Document()
    for line in RESUME_TEXT.splitlines():
        d.add_paragraph(line)
    buf = io.BytesIO()
    d.save(buf)
    buf.seek(0)
    r = client.post("/resumes/upload",
                    data={"title": "Backend Resume v1", "file": (buf, "resume.docx")},
                    content_type="multipart/form-data", follow_redirects=True)
    check("docx upload+analyze", r.status_code == 200 and b"Backend Resume v1" in r.data)
    resume = Resume.query.first()
    check("skills detected", resume is not None and len(resume.skills_json) > 10)
    check("contact detected", "ada@example.com" in resume.contact_json)
    check("health score", resume.health_score is not None and resume.health_score > 0,
          f"score={resume.health_score if resume else None}")

    r = client.get(f"/resumes/{resume.id}")
    check("resume detail page", r.status_code == 200 and b"Health score" in r.data)
    r = client.get(f"/resumes/{resume.id}/export")
    check("resume txt export", r.status_code == 200 and b"SKILLS DETECTED" in r.data)

    # --- job
    r = client.post("/jobs/new", data={"description": JOB_TEXT, "company": "", "role": ""},
                    follow_redirects=True)
    check("job analyze", r.status_code == 200 and b"TechCorp" in r.data)
    job = Job.query.first()
    check("jd skills", "Python" in job.required_skills, f"req={job.required_skills}")
    check("jd remote", job.remote is True)
    check("jd keywords", "technical" in job.keywords_json)

    r = client.get(f"/jobs/{job.id}")
    check("job detail page", r.status_code == 200 and b"Keyword profile" in r.data)
    r = client.get(f"/jobs/{job.id}/export_keywords")
    check("keywords export", r.status_code == 200 and b"KEYWORD PROFILE" in r.data)

    # --- matching
    r = client.get(f"/jobs/{job.id}/match")
    check("match overview", r.status_code == 200 and b"Backend Resume v1" in r.data)
    r = client.get(f"/jobs/{job.id}/match/{resume.id}")
    check("match detail", r.status_code == 200 and b"Coverage" in r.data and b"Skill gap" in r.data)

    # --- application + interview
    r = client.post("/applications/new",
                    data={"job_id": job.id, "status": "Applied", "resume_id": resume.id,
                          "applied_on": "2026-09-20", "notes": "referred by Sam"},
                    follow_redirects=True)
    check("application created", r.status_code == 200 and b"Applied" in r.data)
    app_row = Application.query.first()

    r = client.post(f"/applications/{app_row.id}/update",
                    data={"status": "Interview", "resume_id": resume.id,
                          "applied_on": "2026-09-20", "notes": "referred by Sam"},
                    follow_redirects=True)
    check("application update", r.status_code == 200)

    r = client.post(f"/applications/{app_row.id}/interviews/new",
                    data={"round_name": "Technical R1", "scheduled_at": "2026-10-05T15:30",
                          "mode": "Video", "outcome": "Pending", "notes": "Django deep dive"},
                    follow_redirects=True)
    check("interview added", r.status_code == 200 and b"Technical R1" in r.data)

    # --- status history + follow-up
    r = client.post(f"/applications/{app_row.id}/update",
                    data={"status": "Final Interview", "resume_id": resume.id,
                          "applied_on": "2026-09-20", "notes": "referred by Sam",
                          "status_note": "on-site scheduled"},
                    follow_redirects=True)
    r = client.get(f"/applications/{app_row.id}")
    check("status timeline", r.status_code == 200 and b"Status timeline" in r.data
          and b"Final Interview" in r.data and b"on-site scheduled" in r.data)

    r = client.post(f"/applications/{app_row.id}/followup", follow_redirects=True)
    check("followup logged", r.status_code == 200 and b"Follow-up logged" in r.data)

    # --- offers
    r = client.get("/applications/offers")
    check("offers empty state", r.status_code == 200)
    client.post(f"/applications/{app_row.id}/update",
                data={"status": "Offer", "resume_id": resume.id,
                      "applied_on": "2026-09-20", "notes": "referred by Sam"},
                follow_redirects=True)
    r = client.get("/applications/offers")
    check("offers comparison", r.status_code == 200 and b"TechCorp" in r.data and b"#1" in r.data)

    # --- tracker pages
    for path, needle in [
        ("/applications/", b"TechCorp"),
        ("/applications/board", b"Pipeline board"),
        ("/applications/export", b"Company,Role,Status"),
        ("/applications/interviews", b"Technical R1"),
        ("/analytics/", b"Pipeline funnel"),
        ("/analytics/skills", b"My skills"),
        ("/reports/", b"Resume reports"),
        ("/resumes/compare", b"Compare resume versions"),
        ("/resumes/compare/results?a=1&b=1", b"checklist"),
        ("/", b"Dashboard"),
    ]:
        r = client.get(path)
        check(f"GET {path}", r.status_code == 200 and needle in r.data)

    # --- skill self-tracking
    r = client.post("/analytics/skills", data={"name": "Redis", "level": "Learning"},
                    follow_redirects=True)
    check("skill tracked", r.status_code == 200 and b"Redis" in r.data)

    # --- PDF reports
    r = client.get(f"/reports/resume/{resume.id}")
    check("resume PDF", r.status_code == 200 and r.data[:4] == b"%PDF")
    r = client.get(f"/reports/resume/{resume.id}/document")
    check("clean resume PDF", r.status_code == 200 and r.data[:4] == b"%PDF")
    r = client.get(f"/reports/job/{job.id}/{resume.id}")
    check("job match PDF", r.status_code == 200 and r.data[:4] == b"%PDF")
    r = client.get(f"/reports/application/{app_row.id}")
    check("application PDF", r.status_code == 200 and r.data[:4] == b"%PDF")
    r = client.get("/reports/analytics")
    check("analytics PDF", r.status_code == 200 and r.data[:4] == b"%PDF")

    # --- auth isolation
    client.get("/logout")
    client.post("/signup", data={"email": "eve@example.com", "name": "Eve",
                                 "password": "Secret1!", "confirm": "Secret1!"})
    r = client.get(f"/resumes/{resume.id}")
    check("user isolation (404)", r.status_code == 404)
    r = client.get(f"/jobs/{job.id}/match")
    check("job isolation (404)", r.status_code == 404)

    failed = [n for n, passed in ok if not passed]
    print(f"\n{len(ok) - len(failed)}/{len(ok)} passed")
    if failed:
        print("FAILED:", failed)
        sys.exit(1)


if __name__ == "__main__":
    with app.app_context():
        db.drop_all()
        db.create_all()
        run()
