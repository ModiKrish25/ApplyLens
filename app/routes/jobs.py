import json
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, abort, Response)
from flask_login import login_required, current_user
from ..extensions import db
from ..models import Job, Application, Resume, APPLICATION_STATUSES, STATUS_CLASS
from ..utils.parser import parse_job_description, analyze_resume_text
from ..utils.matcher import match_resume_to_job, verdict
from ..utils.analyzer import health_checklist
from ..utils.semantic import semantic_match
from ..utils.rewriter import suggest_bullets
from ..utils.skills import skill_category

jobs_bp = Blueprint("jobs", __name__, url_prefix="/jobs")


def get_own_job(job_id):
    job = db.session.get(Job, job_id)
    if job is None or job.user_id != current_user.id:
        abort(404)
    return job


def rebuild_job_analysis(job):
    """Re-parse stored JD text to recompute keywords on the fly."""
    return parse_job_description(job.source_text or "")


@jobs_bp.route("/")
@login_required
def index():
    jobs = Job.query.filter_by(user_id=current_user.id).order_by(Job.created_at.desc()).all()
    return render_template("jobs.html", jobs=jobs)


@jobs_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    if request.method == "POST":
        text = request.form.get("description", "").strip()
        if len(text.split()) < 20:
            flash("Paste a fuller job description (at least ~20 words).", "error")
            return render_template("job_new.html")
        parsed = parse_job_description(text)
        job = Job(
            user_id=current_user.id,
            company=request.form.get("company", "").strip() or parsed["company"],
            role=request.form.get("role", "").strip() or parsed["role"],
            location=parsed["location"], remote=parsed["remote"],
            salary=parsed["salary"], experience=parsed["experience"],
            work_type=parsed["work_type"], source_text=text,
            required_skills_json=json.dumps(parsed["required_skills"]),
            preferred_skills_json=json.dumps(parsed["preferred_skills"]),
            keywords_json=json.dumps(parsed["keywords"]),
        )
        if not job.role:
            job.role = (request.form.get("role_hint") or "Untitled Role").strip()
        db.session.add(job)
        db.session.commit()
        flash("Job description analyzed and saved.", "success")
        return redirect(url_for("jobs.detail", job_id=job.id))
    return render_template("job_new.html")


@jobs_bp.route("/<int:job_id>")
@login_required
def detail(job_id):
    job = get_own_job(job_id)
    keywords = json.loads(job.keywords_json or "{}")
    resumes = Resume.query.filter_by(user_id=current_user.id, is_archived=False).all()
    app_ = Application.query.filter_by(job_id=job.id).first()
    return render_template("job_detail.html", job=job, keywords=keywords,
                           resumes=resumes, app=app_,
                           statuses=APPLICATION_STATUSES, STATUS_CLASS=STATUS_CLASS)


@jobs_bp.route("/<int:job_id>/delete", methods=["POST"])
@login_required
def delete(job_id):
    job = get_own_job(job_id)
    db.session.delete(job)
    db.session.commit()
    flash("Job deleted.", "success")
    return redirect(url_for("jobs.index"))


@jobs_bp.route("/<int:job_id>/match")
@login_required
def match(job_id):
    """Match every resume version against this job."""
    job = get_own_job(job_id)
    resumes = Resume.query.filter_by(user_id=current_user.id, is_archived=False).all()
    results = []
    for r in resumes:
        analysis = analyze_resume_text(r.raw_text)
        analysis["full_text"] = r.raw_text
        m = match_resume_to_job(analysis, job)
        results.append((r, m))
    results.sort(key=lambda rm: -(rm[1]["coverage"] if rm[1] else 0))
    return render_template("job_match.html", job=job, results=results,
                           verdict_fn=verdict)


@jobs_bp.route("/<int:job_id>/match/<int:resume_id>")
@login_required
def match_detail(job_id, resume_id):
    job = get_own_job(job_id)
    resume = db.session.get(Resume, resume_id)
    if resume is None or resume.user_id != current_user.id:
        abort(404)
    analysis = analyze_resume_text(resume.raw_text)
    analysis["full_text"] = resume.raw_text
    m = match_resume_to_job(analysis, job)
    health = health_checklist(analysis, resume.raw_text)

    # STAR: semantic similarity with quoted evidence (keyword matching above)
    sem = semantic_match(job.source_text, resume.raw_text)

    # STAR: bullet rewrite suggestions for missing/weak skills (required first,
    # then preferred gaps — anything the JD asks for that's thin in the resume)
    missing = [r["name"] for r in m["required"] if not r["matched"]][:2]
    missing_pref = [r["name"] for r in m["preferred"] if not r["matched"]][:2]
    weak = [r["name"] for r in m["required"] + m["preferred"]
            if r["matched"] and r["count"] == 1][:2]
    rewrites = []
    for name in (missing + missing_pref + weak)[:4]:
        for s in suggest_bullets(name, skill_category(name), resume.raw_text, 1):
            rewrites.append({"skill": name, **s})

    return render_template("match_detail.html", job=job, resume=resume, m=m,
                           verdict=verdict(m["coverage"]), health=health,
                           sem=sem, rewrites=rewrites)


@jobs_bp.route("/<int:job_id>/export_keywords")
@login_required
def export_keywords(job_id):
    job = get_own_job(job_id)
    keywords = json.loads(job.keywords_json or "{}")
    lines = [f"KEYWORD PROFILE — {job.company} / {job.role}", "=" * 50, ""]
    lines.append("TECHNICAL KEYWORDS")
    for k in keywords.get("technical", []):
        lines.append(f"{k['word']:<30} {k['count']}")
    lines.append("")
    lines.append("SOFT SKILLS")
    for k in keywords.get("soft", []):
        lines.append(f"{k['word']:<30} {k['count']}")
    return Response("\n".join(lines), mimetype="text/plain",
                    headers={"Content-Disposition": f"attachment; filename=keywords_{job.id}.txt"})
