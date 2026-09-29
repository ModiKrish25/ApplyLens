import csv
import io
from datetime import datetime, timezone
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, abort, Response, session)
from flask_login import login_required, current_user
from sqlalchemy import or_, func
from ..extensions import db
from ..models import (Job, Resume, Application, Interview, StatusHistory,
                      APPLICATION_STATUSES, STATUS_CLASS)
from ..utils.parser import analyze_resume_text
from ..utils.prep import generate_prep_kit
from ..utils.offer_matrix import score_offers, DEFAULT_WEIGHTS

apps_bp = Blueprint("applications", __name__, url_prefix="/applications")

OPEN_STATUSES = ("Saved", "Applied", "Screening", "Assessment", "Interview", "Final Interview")
SORTS = {
    "updated": Application.updated_at.desc(),
    "company": func.lower(Job.company).asc(),
    "role": func.lower(Job.role).asc(),
    "status": Application.status.asc(),
    "applied": Application.applied_on.desc().nullslast(),
}


def get_own_app(app_id):
    app_ = db.session.get(Application, app_id)
    if app_ is None or app_.user_id != current_user.id:
        abort(404)
    return app_


@apps_bp.route("/")
@login_required
def index():
    q = (request.args.get("q") or "").strip()
    status = request.args.get("status") or ""
    company = request.args.get("company") or ""
    tech = request.args.get("tech") or ""
    remote = request.args.get("remote") or ""
    sort = request.args.get("sort", "updated")

    query = Application.query.join(Job, Application.job_id == Job.id)\
        .filter(Application.user_id == current_user.id)

    if q:
        like = f"%{q}%"
        query = query.filter(or_(
            Job.company.ilike(like), Job.role.ilike(like),
            Job.location.ilike(like), Job.source_text.ilike(like),
            Application.notes.ilike(like)))
    if status:
        query = query.filter(Application.status == status)
    if company:
        query = query.filter(func.lower(Job.company) == company.lower())
    if tech:
        like = f"%{tech.lower()}%"
        query = query.filter(or_(Job.required_skills_json.ilike(like),
                                 Job.source_text.ilike(like)))
    if remote == "1":
        query = query.filter(Job.remote.is_(True))

    order = SORTS.get(sort, SORTS["updated"])
    apps = query.order_by(order).all()

    companies = [c for (c,) in db.session.query(func.lower(Job.company))
                 .filter(Job.user_id == current_user.id, Job.company != "")
                 .distinct().order_by(func.lower(Job.company)).all()]

    return render_template("applications.html", apps=apps, q=q, status=status,
                           company=company, tech=tech, remote=remote,
                           sort=sort, statuses=APPLICATION_STATUSES,
                           companies=companies,
                           STATUS_CLASS=STATUS_CLASS)


@apps_bp.route("/board")
@login_required
def board():
    apps = Application.query.join(Job).filter(Application.user_id == current_user.id).all()
    return render_template("board.html", apps=apps, statuses=APPLICATION_STATUSES,
                           STATUS_CLASS=STATUS_CLASS)


@apps_bp.route("/<int:app_id>/status", methods=["POST"])
@login_required
def set_status(app_id):
    """API endpoint for kanban drag-and-drop: JSON in, JSON out."""
    app_ = get_own_app(app_id)
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if status not in APPLICATION_STATUSES:
        return {"ok": False, "error": "Invalid status"}, 400
    if status != app_.status:
        db.session.add(StatusHistory(application_id=app_.id, from_status=app_.status,
                                     to_status=status, note="Moved on board"))
        app_.status = status
        db.session.commit()
    return {"ok": True, "status": status, "history_recorded": True}


@apps_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    jobs = Job.query.filter_by(user_id=current_user.id).order_by(Job.created_at.desc()).all()
    resumes = Resume.query.filter_by(user_id=current_user.id, is_archived=False).all()
    if request.method == "POST":
        job_id = request.form.get("job_id", type=int)
        job = db.session.get(Job, job_id) if job_id else None
        if job is None or job.user_id != current_user.id:
            flash("Pick a saved job to track.", "error")
            return render_template("application_new.html", jobs=jobs, resumes=resumes,
                                   statuses=APPLICATION_STATUSES)
        if job.application:
            flash("This job is already being tracked.", "error")
            return redirect(url_for("applications.detail", app_id=job.application.id))
        resume_id = request.form.get("resume_id", type=int)
        status = request.form.get("status", "Saved")
        if status not in APPLICATION_STATUSES:
            status = "Saved"
        applied_raw = request.form.get("applied_on") or ""
        applied = datetime.strptime(applied_raw, "%Y-%m-%d").date() if applied_raw else None
        if status != "Saved" and not applied:
            applied = datetime.now(timezone.utc).date()
        app_ = Application(user_id=current_user.id, job_id=job.id,
                           resume_id=resume_id if resume_id else None,
                           status=status, applied_on=applied,
                           notes=request.form.get("notes", "").strip())
        db.session.add(app_)
        db.session.flush()
        db.session.add(StatusHistory(application_id=app_.id, from_status="",
                                     to_status=status, note="Application created"))
        db.session.commit()
        flash("Application tracking started.", "success")
        return redirect(url_for("applications.detail", app_id=app_.id))
    return render_template("application_new.html", jobs=jobs, resumes=resumes,
                           statuses=APPLICATION_STATUSES)


@apps_bp.route("/<int:app_id>")
@login_required
def detail(app_id):
    app_ = get_own_app(app_id)
    interviews = Interview.query.filter_by(application_id=app_.id)\
        .order_by(Interview.scheduled_at.desc()).all()
    resumes = Resume.query.filter_by(user_id=current_user.id, is_archived=False).all()
    return render_template("application_detail.html", app=app_,
                           interviews=interviews, resumes=resumes,
                           statuses=APPLICATION_STATUSES,
                           STATUS_CLASS=STATUS_CLASS)


@apps_bp.route("/<int:app_id>/update", methods=["POST"])
@login_required
def update(app_id):
    app_ = get_own_app(app_id)
    status = request.form.get("status")
    resume_id = request.form.get("resume_id", type=int)
    applied_raw = request.form.get("applied_on") or ""
    if status in APPLICATION_STATUSES and status != app_.status:
        db.session.add(StatusHistory(application_id=app_.id, from_status=app_.status,
                                     to_status=status,
                                     note=request.form.get("status_note", "").strip()))
        app_.status = status
    if resume_id:
        resume = db.session.get(Resume, resume_id)
        if resume and resume.user_id == current_user.id:
            app_.resume_id = resume.id
    else:
        app_.resume_id = None
    app_.applied_on = datetime.strptime(applied_raw, "%Y-%m-%d").date() if applied_raw else None
    app_.notes = request.form.get("notes", "").strip()
    db.session.commit()
    flash("Application updated.", "success")
    return redirect(url_for("applications.detail", app_id=app_.id))


@apps_bp.route("/<int:app_id>/delete", methods=["POST"])
@login_required
def delete(app_id):
    app_ = get_own_app(app_id)
    db.session.delete(app_)
    db.session.commit()
    flash("Application removed.", "success")
    return redirect(url_for("applications.index"))


@apps_bp.route("/offers")
@login_required
def offers():
    """Side-by-side comparison of all offers."""
    offers = (Application.query.join(Job, Application.job_id == Job.id)
              .filter(Application.user_id == current_user.id,
                      Application.status == "Offer")
              .order_by(Application.updated_at.desc()).all())
    for o in offers:
        o.interview_count = Interview.query.filter_by(application_id=o.id).count()
    return render_template("offers.html", offers=offers, STATUS_CLASS=STATUS_CLASS)


@apps_bp.route("/export")
@login_required
def export_csv():
    apps = (Application.query.join(Job, Application.job_id == Job.id)
            .filter(Application.user_id == current_user.id)
            .order_by(Application.updated_at.desc()).all())
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Company", "Role", "Status", "Applied On", "Resume",
                     "Location", "Remote", "Notes", "Last Updated"])
    for a in apps:
        writer.writerow([
            a.job.company, a.job.role, a.status,
            a.applied_on.isoformat() if a.applied_on else "",
            a.resume.title if a.resume else "",
            a.job.location, "Yes" if a.job.remote else "No",
            (a.notes or "").replace("\n", " "), a.updated_at.strftime("%Y-%m-%d %H:%M"),
        ])
    buf.seek(0)
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=applications.csv"})


# ---------------------------------------------------------------- interviews

# ------------------------------------------------------------------
# STAR: interview prep kit
# ------------------------------------------------------------------

@apps_bp.route("/<int:app_id>/prep")
@login_required
def prep(app_id):
    """Rule-generated interview prep for this application's next round."""
    app_ = get_own_app(app_id)
    if not app_.resume:
        flash("Attach a resume to this application first — the prep kit derives everything from it.", "error")
        return redirect(url_for("applications.detail", app_id=app_.id))
    analysis = analyze_resume_text(app_.resume.raw_text)
    analysis["full_text"] = app_.resume.raw_text
    kit = generate_prep_kit(analysis, app_.job)
    upcoming = Interview.query.filter_by(application_id=app_.id, outcome="Pending")\
        .order_by(Interview.scheduled_at.asc()).first()
    return render_template("interview_prep.html", app=app_, kit=kit,
                           upcoming=upcoming, STATUS_CLASS=STATUS_CLASS)


# ------------------------------------------------------------------
# STAR: offer decision matrix
# ------------------------------------------------------------------

@apps_bp.route("/offers/matrix", methods=["GET", "POST"])
@login_required
def offer_matrix():
    """Weighted, fully transparent comparison of all offers."""
    offers = (Application.query.join(Job, Application.job_id == Job.id)
              .filter(Application.user_id == current_user.id,
                      Application.status == "Offer")
              .order_by(Application.updated_at.desc()).all())
    for o in offers:
        o.interview_count = Interview.query.filter_by(application_id=o.id).count()

    weights = dict(DEFAULT_WEIGHTS)
    if request.method == "POST":
        for k in DEFAULT_WEIGHTS:
            w = request.form.get(f"w_{k}", type=int)
            if w is not None and 0 <= w <= 100:
                weights[k] = w
        session["offer_weights"] = weights
    else:
        weights = session.get("offer_weights", weights)

    rows = score_offers(offers, weights)
    total_w = sum(weights.values()) or 1
    return render_template("offer_matrix.html", rows=rows, weights=weights,
                           total_w=total_w, has_offers=bool(offers))


@apps_bp.route("/<int:app_id>/followup", methods=["POST"])
@login_required
def followup(app_id):
    """Bump an application: clears staleness by recording a nudge in history."""
    app_ = get_own_app(app_id)
    db.session.add(StatusHistory(application_id=app_.id, from_status=app_.status,
                                 to_status=app_.status,
                                 note="Follow-up sent"))
    app_.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    flash("Follow-up logged — staleness timer reset.", "success")
    return redirect(url_for("applications.detail", app_id=app_.id))


@apps_bp.route("/<int:app_id>/interviews/new", methods=["POST"])
@login_required
def add_interview(app_id):
    app_ = get_own_app(app_id)
    when_raw = request.form.get("scheduled_at", "")
    try:
        when = datetime.strptime(when_raw, "%Y-%m-%dT%H:%M")
    except ValueError:
        flash("Pick a valid interview date and time.", "error")
        return redirect(url_for("applications.detail", app_id=app_.id))
    iv = Interview(
        user_id=current_user.id, job_id=app_.job_id, application_id=app_.id,
        round_name=request.form.get("round_name", "Interview").strip() or "Interview",
        scheduled_at=when, mode=request.form.get("mode", "").strip(),
        location=request.form.get("location", "").strip(),
        outcome=request.form.get("outcome", "Pending"),
        notes=request.form.get("notes", "").strip())
    db.session.add(iv)
    db.session.commit()
    flash("Interview added.", "success")
    return redirect(url_for("applications.detail", app_id=app_.id))


@apps_bp.route("/interviews")
@login_required
def interviews():
    upcoming = Interview.query.filter(
        Interview.user_id == current_user.id,
        Interview.scheduled_at >= func.now(),
        Interview.outcome == "Pending").order_by(Interview.scheduled_at.asc()).all()
    past = Interview.query.filter(
        Interview.user_id == current_user.id,
        or_(Interview.scheduled_at < func.now(), Interview.outcome != "Pending"))\
        .order_by(Interview.scheduled_at.desc()).all()
    return render_template("interviews.html", upcoming=upcoming, past=past)


@apps_bp.route("/interviews/<int:iv_id>/outcome", methods=["POST"])
@login_required
def interview_outcome(iv_id):
    iv = db.session.get(Interview, iv_id)
    if iv is None or iv.user_id != current_user.id:
        abort(404)
    outcome = request.form.get("outcome", "Pending")
    if outcome in ("Pending", "Passed", "Failed"):
        iv.outcome = outcome
        db.session.commit()
    return redirect(request.referrer or url_for("applications.interviews"))
