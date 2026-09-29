from datetime import datetime, timedelta, timezone
from flask import Blueprint, render_template, request, url_for, redirect, flash, abort
from flask_login import login_required, current_user
from sqlalchemy import func
from ..extensions import db
from ..models import (Resume, Job, Application, Interview, UserSkill, LearningGoal,
                      APPLICATION_STATUSES, SKILL_LEVELS)
from ..utils.skills import skill_category
from ..utils.response_time import response_stats, waiting_note

LEVEL_SCORE = {"Not Started": 0, "Learning": 1, "Practicing": 2,
               "Comfortable": 3, "Expert": 4}
LEVEL_NAME = {v: k for k, v in LEVEL_SCORE.items()}

analytics_bp = Blueprint("analytics", __name__, url_prefix="/analytics")


@analytics_bp.route("/")
@login_required
def index():
    now = datetime.now(timezone.utc)
    apps = Application.query.filter_by(user_id=current_user.id).all()
    jobs = Job.query.filter_by(user_id=current_user.id).all()
    resumes = Resume.query.filter_by(user_id=current_user.id).all()
    skills = UserSkill.query.filter_by(user_id=current_user.id).all()

    total = len(apps)
    counts = {s: sum(1 for a in apps if a.status == s) for s in APPLICATION_STATUSES}
    interviews = Interview.query.filter_by(user_id=current_user.id).count()
    offers = counts.get("Offer", 0)
    rejected = counts.get("Rejected", 0)
    responded = total - counts.get("Saved", 0) - counts.get("Applied", 0)

    def pct(n, d):
        return round(100 * n / d) if d else 0

    funnel = [
        ("Saved", counts.get("Saved", 0)),
        ("Applied", counts.get("Applied", 0)),
        ("Screening / Assessment", counts.get("Screening", 0) + counts.get("Assessment", 0)),
        ("Interviewing", counts.get("Interview", 0) + counts.get("Final Interview", 0)),
        ("Offer", offers),
    ]
    funnel_max = max([n for _, n in funnel], default=1) or 1

    weeks = []
    for i in range(7, -1, -1):
        start = (now - timedelta(weeks=i + 1)).date()
        end = (now - timedelta(weeks=i)).date()
        applied_w = sum(1 for a in apps if a.applied_on and start <= a.applied_on < end)
        rej_w = sum(1 for a in apps if a.status == "Rejected" and start <= a.updated_at.date() < end)
        weeks.append({"label": f"W-{i}", "applied": applied_w, "rejected": rej_w})
    week_max = max([max(w["applied"], w["rejected"]) for w in weeks], default=1) or 1

    by_company = {}
    for a in apps:
        name = a.job.company or "Unknown"
        by_company.setdefault(name, {"count": 0, "best": 99})
        by_company[name]["count"] += 1
        rank = APPLICATION_STATUSES.index(a.status) if a.status in APPLICATION_STATUSES else 0
        by_company[name]["best"] = min(by_company[name]["best"], rank)
    top_companies = sorted(by_company.items(), key=lambda kv: (-kv[1]["count"], kv[0]))[:8]

    demand = {}
    for j in jobs:
        for s in j.required_skills + j.preferred_skills:
            demand.setdefault(s, {"count": 0, "category": skill_category(s)})
            demand[s]["count"] += 1
    top_demand = sorted(demand.items(), key=lambda kv: -kv[1]["count"])[:12]

    # ---- STAR: market demand vs self-assessed skill levels ----------------
    skill_map = {s.name.lower(): s for s in skills}
    demand_vs_skill = []
    for name, info in top_demand:
        tracked = skill_map.get(name.lower())
        score = LEVEL_SCORE.get(tracked.level, -1) if tracked else -1
        demand_vs_skill.append({
            "name": name, "count": info["count"], "category": info["category"],
            "level": tracked.level if tracked else None, "score": score,
        })
    demand_vs_skill.sort(key=lambda d: (-d["count"], -(d["score"] + 1)))

    # ---- STAR: funnel conversion + avg days in stage -----------------------
    OPEN_STAGES = ["Saved", "Applied", "Screening / Assessment",
                   "Interviewing", "Offer"]
    open_counts = {
        "Saved": counts.get("Saved", 0),
        "Applied": counts.get("Applied", 0),
        "Screening / Assessment": counts.get("Screening", 0) + counts.get("Assessment", 0),
        "Interviewing": counts.get("Interview", 0) + counts.get("Final Interview", 0),
        "Offer": counts.get("Offer", 0),
    }
    conversions = []
    for i in range(1, len(OPEN_STAGES)):
        prev, cur = OPEN_STAGES[i - 1], OPEN_STAGES[i]
        reached_cur = sum(open_counts[s] for s in OPEN_STAGES[i:])
        conversions.append({
            "from": prev, "to": cur,
            "rate": pct(reached_cur, open_counts[prev]) if open_counts[prev] else None,
        })

    # avg days in current stage, only for open applications, from StatusHistory
    stage_days = {}
    for stage, key in [("Applied", "Applied"), ("Screening / Assessment", "Screening"),
                       ("Interviewing", "Interview")]:
        members = [a for a in apps if a.status.startswith(key) or
                   (key == "Screening" and a.status == "Assessment") or
                   (key == "Interview" and a.status == "Final Interview")]
        if members:
            avg = sum(a.days_in_status for a in members) / len(members)
            stage_days[stage] = round(avg)

    resume_usage = [{"resume": r, "uses": Application.query.filter_by(resume_id=r.id).count()}
                    for r in resumes]
    resume_usage.sort(key=lambda x: -x["uses"])

    stats = {
        "Total applications": total,
        "Active applications": sum(1 for a in apps if a.status not in ("Rejected", "Withdrawn")),
        "Response rate": f"{pct(responded, total)}%",
        "Interview rate": f"{pct(interviews, total)}%",
        "Offer rate": f"{pct(offers, total)}%",
        "Rejections": rejected,
        "Resumes stored": len(resumes),
        "Jobs saved": len(jobs),
        "Interviews recorded": interviews,
        "Skills self-tracked": len(skills),
    }

    level_counts = {lv: sum(1 for s in skills if s.level == lv) for lv in SKILL_LEVELS}

    # STAR: response-time stats learned from the user's own history
    rt = response_stats(current_user.id)

    return render_template("analytics.html", stats=stats, funnel=funnel,
                           funnel_max=funnel_max, weeks=weeks, week_max=week_max,
                           top_companies=top_companies, top_demand=top_demand,
                           demand_vs_skill=demand_vs_skill,
                           conversions=conversions, stage_days=stage_days,
                           rt=rt, rt_note=waiting_note(rt),
                           resume_usage=resume_usage, level_counts=level_counts,
                           statuses=APPLICATION_STATUSES)


# ------------------------------------------------------------------
# STAR: skill-gap learning plan
# ------------------------------------------------------------------

@analytics_bp.route("/plan")
@login_required
def learning_plan():
    """Tracked learning goals, fed by job-match gaps."""
    goals = LearningGoal.query.filter_by(user_id=current_user.id)\
        .order_by(LearningGoal.done.asc(), LearningGoal.priority.asc(),
                  LearningGoal.created_at.desc()).all()
    open_goals = [g for g in goals if not g.done]
    done_goals = [g for g in goals if g.done]
    avg_progress = (sum(g.progress for g in open_goals) // len(open_goals)) if open_goals else 0

    # same suggestions as My Skills: demanded in saved jobs, not already planned
    planned = {g.name for g in goals}
    suggested = {}
    for j in Job.query.filter_by(user_id=current_user.id).all():
        for s in j.required_skills + j.preferred_skills:
            suggested[s] = suggested.get(s, 0) + 1
    suggestions = sorted(((s, c) for s, c in suggested.items() if s.lower() not in planned),
                         key=lambda x: -x[1])[:12]

    return render_template("learning_plan.html", open_goals=open_goals,
                           done_goals=done_goals, avg_progress=avg_progress,
                           suggestions=suggestions, statuses=APPLICATION_STATUSES)


@analytics_bp.route("/plan/add", methods=["POST"])
@login_required
def plan_add():
    name = (request.form.get("name") or "").strip()
    if not name:
        flash("Give the goal a skill name.", "error")
        return redirect(request.referrer or url_for("analytics.learning_plan"))
    job_id = request.form.get("job_id", type=int)
    job = db.session.get(Job, job_id) if job_id else None
    if job is not None and job.user_id != current_user.id:
        abort(404)
    priority = request.form.get("priority", type=int) or 2
    if priority not in (1, 2, 3):
        priority = 2
    existing = LearningGoal.query.filter_by(user_id=current_user.id,
                                            name=name.lower()).first()
    if existing:
        existing.done = False
        existing.priority = priority
        flash(f"'{name}' is already in your plan — reopened/updated it.", "success")
    else:
        db.session.add(LearningGoal(
            user_id=current_user.id, name=name.lower(),
            category=skill_category(name) if name[0].isupper() else "Other / General",
            source_job_id=job.id if job else None,
            source_company=(job.company if job else "") or "",
            priority=priority))
        flash(f"'{name}' added to your learning plan.", "success")
    db.session.commit()
    return redirect(request.referrer or url_for("analytics.learning_plan"))


@analytics_bp.route("/plan/<int:goal_id>/update", methods=["POST"])
@login_required
def plan_update(goal_id):
    goal = db.session.get(LearningGoal, goal_id)
    if goal is None or goal.user_id != current_user.id:
        abort(404)
    if "progress" in request.form:
        p = request.form.get("progress", type=int) or 0
        goal.progress = max(0, min(100, p))
        goal.done = goal.progress >= 100
    if "priority" in request.form:
        pr = request.form.get("priority", type=int) or 2
        if pr in (1, 2, 3):
            goal.priority = pr
    if "toggle_done" in request.form:
        goal.done = not goal.done
        goal.progress = 100 if goal.done else min(goal.progress, 90)
    db.session.commit()
    return redirect(request.referrer or url_for("analytics.learning_plan"))


@analytics_bp.route("/plan/<int:goal_id>/delete", methods=["POST"])
@login_required
def plan_delete(goal_id):
    goal = db.session.get(LearningGoal, goal_id)
    if goal is None or goal.user_id != current_user.id:
        abort(404)
    db.session.delete(goal)
    db.session.commit()
    flash("Goal removed.", "success")
    return redirect(url_for("analytics.learning_plan"))


@analytics_bp.route("/skills", methods=["GET", "POST"])
@login_required
def my_skills():
    """Skill Gap self-tracking: mark skills as Not Started → Expert."""
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        level = request.form.get("level", "Not Started")
        if level not in SKILL_LEVELS:
            level = "Not Started"
        if name:
            existing = UserSkill.query.filter_by(user_id=current_user.id,
                                                 name=name.lower()).first()
            if existing:
                existing.level = level
            else:
                db.session.add(UserSkill(user_id=current_user.id,
                                         name=name.lower(), level=level))
            db.session.commit()
        return redirect(url_for("analytics.my_skills"))

    skills = UserSkill.query.filter_by(user_id=current_user.id)\
        .order_by(UserSkill.name.asc()).all()

    suggested = {}
    for j in Job.query.filter_by(user_id=current_user.id).all():
        for s in j.required_skills + j.preferred_skills:
            suggested[s] = suggested.get(s, 0) + 1
    tracked = {s.name for s in skills}
    suggestions = sorted(((s, c) for s, c in suggested.items() if s.lower() not in tracked),
                         key=lambda x: -x[1])[:15]

    return render_template("my_skills.html", skills=skills, levels=SKILL_LEVELS,
                           suggestions=suggestions)
