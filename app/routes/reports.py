import io
import os
import tempfile
from flask import Blueprint, render_template, send_file, abort, current_app
from flask_login import login_required, current_user
from ..extensions import db
from ..models import Job, Resume, Application, Interview
from ..utils.parser import analyze_resume_text, parse_job_description
from ..utils.analyzer import health_checklist
from ..utils.proofread import proofread
from ..utils.matcher import match_resume_to_job, verdict
from ..utils import pdf_reports

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


@reports_bp.route("/")
@login_required
def index():
    resumes = Resume.query.filter_by(user_id=current_user.id).all()
    jobs = Job.query.filter_by(user_id=current_user.id).all()
    apps = Application.query.join(Job).filter(Application.user_id == current_user.id).all()
    return render_template("reports.html", resumes=resumes, jobs=jobs, apps=apps)


def _generate(filename, builder, *args, **kwargs):
    """Build a PDF into a temp file, then send it from memory.

    Reports are produced and downloaded within a single request, so nothing
    needs to persist — important because local disk does not survive a
    redeploy on a PaaS.
    """
    fd, path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    try:
        builder(path, *args, **kwargs)
        with open(path, "rb") as f:
            buf = io.BytesIO(f.read())
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name=filename,
                     mimetype="application/pdf")


@reports_bp.route("/resume/<int:resume_id>")
@login_required
def resume_report(resume_id):
    resume = db.session.get(Resume, resume_id)
    if resume is None or resume.user_id != current_user.id:
        abort(404)
    analysis = analyze_resume_text(resume.raw_text)
    health = health_checklist(analysis, resume.raw_text)
    proof = proofread(resume.raw_text)
    return _generate(f"resume_report_{resume_id}.pdf",
                     pdf_reports.generate_resume_report, resume, analysis, health,
                     proof)


@reports_bp.route("/resume/<int:resume_id>/document")
@login_required
def resume_document(resume_id):
    """Clean resume PDF rebuilt from the parsed data (fixed layout)."""
    resume = db.session.get(Resume, resume_id)
    if resume is None or resume.user_id != current_user.id:
        abort(404)
    analysis = analyze_resume_text(resume.raw_text)
    return _generate(f"resume_document_{resume_id}.pdf",
                     pdf_reports.generate_resume_document, resume, analysis)


@reports_bp.route("/job/<int:job_id>/<int:resume_id>")
@login_required
def job_report(job_id, resume_id):
    job = db.session.get(Job, job_id)
    resume = db.session.get(Resume, resume_id)
    if not job or not resume or job.user_id != current_user.id or resume.user_id != current_user.id:
        abort(404)
    analysis = analyze_resume_text(resume.raw_text)
    analysis["full_text"] = resume.raw_text
    m = match_resume_to_job(analysis, job)
    v = verdict(m["coverage"])
    return _generate(f"job_match_{job_id}_{resume_id}.pdf",
                     pdf_reports.generate_job_match_report, job, resume, m, v[1])


@reports_bp.route("/application/<int:app_id>")
@login_required
def application_report(app_id):
    app_ = db.session.get(Application, app_id)
    if app_ is None or app_.user_id != current_user.id:
        abort(404)
    interviews = Interview.query.filter_by(application_id=app_.id)\
        .order_by(Interview.scheduled_at.asc()).all()
    return _generate(f"application_{app_id}.pdf",
                     pdf_reports.generate_application_summary,
                     app_, app_.job, app_.resume, interviews)


@reports_bp.route("/analytics")
@login_required
def analytics_report():
    apps = Application.query.filter_by(user_id=current_user.id).all()
    total = len(apps)
    counts = {s: sum(1 for a in apps if a.status == s) for s in
              ["Saved", "Applied", "Screening", "Assessment", "Interview",
               "Final Interview", "Offer", "Rejected", "Withdrawn"]}
    interviews = Interview.query.filter_by(user_id=current_user.id).count()
    stats = {
        "Total applications": total,
        "Offers": counts.get("Offer", 0),
        "Rejections": counts.get("Rejected", 0),
        "In interview stages": counts.get("Interview", 0) + counts.get("Final Interview", 0),
        "Interviews recorded": interviews,
        "Resumes stored": Resume.query.filter_by(user_id=current_user.id).count(),
        "Jobs saved": Job.query.filter_by(user_id=current_user.id).count(),
    }
    return _generate("career_analytics.pdf",
                     pdf_reports.generate_analytics_report, current_user, stats)
