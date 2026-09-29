from datetime import timedelta
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from sqlalchemy import func
from ..extensions import db
from ..models import Resume, Job, Application, Interview, StatusHistory
from ..models import APPLICATION_STATUSES, STATUS_CLASS

dash_bp = Blueprint("dashboard", __name__)

FOLLOWUP_AFTER_DAYS = 7   # applied this long ago with no movement → nudge due
STALE_AFTER_DAYS = 14     # existing staleness rule


@dash_bp.route("/")
@login_required
def index():
    resumes = Resume.query.filter_by(user_id=current_user.id, is_archived=False).all()
    jobs = Job.query.filter_by(user_id=current_user.id).all()
    apps = Application.query.filter_by(user_id=current_user.id).all()

    counts = {}
    for s in APPLICATION_STATUSES:
        counts[s] = sum(1 for a in apps if a.status == s)

    upcoming = (
        Interview.query
        .filter(Interview.user_id == current_user.id,
                Interview.outcome == "Pending",
                Interview.scheduled_at >= func.now())
        .order_by(Interview.scheduled_at.asc())
        .limit(5).all()
    )

    active = [a for a in apps if a.status not in ("Rejected", "Withdrawn")]
    offers = counts.get("Offer", 0)
    stale = sorted([a for a in active if a.is_stale],
                   key=lambda a: -a.days_in_status)[:5]

    # ---- STAR: follow-ups-due feed -----------------------------------------
    # Open applications where the last movement is 7+ days old and the
    # application is past 'Saved' (a saved job isn't worth nudging yet).
    # A follow-up already logged today suppresses the reminder.
    now = func.now()
    due = []
    for a in active:
        if a.status == "Saved":
            continue
        days = a.days_in_status
        if days < FOLLOWUP_AFTER_DAYS and not a.is_stale:
            continue
        last_followup = (StatusHistory.query
                         .filter(StatusHistory.application_id == a.id,
                                 StatusHistory.note == "Follow-up sent")
                         .order_by(StatusHistory.changed_at.desc())
                         .first())
        followed_recently = bool(last_followup and
                                 (func.now() - last_followup.changed_at).days < 3)
        if followed_recently:
            continue
        due.append({
            "app": a, "days": days,
            "kind": "stale" if a.is_stale else "due",
        })
    due.sort(key=lambda d: -d["days"])

    return render_template(
        "dashboard.html",
        counts=counts,
        total_apps=len(apps),
        active_apps=len(active),
        interviews_count=sum(1 for a in apps if "Interview" in a.status),
        offers=offers,
        resume_count=len(resumes),
        job_count=len(jobs),
        upcoming=upcoming,
        stale_apps=stale,
        followups_due=due,
        recent_apps=sorted(apps, key=lambda a: a.updated_at, reverse=True)[:5],
        statuses=APPLICATION_STATUSES,
        STATUS_CLASS=STATUS_CLASS,
    )
