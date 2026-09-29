"""
Response-time prediction — statistics learned from the user's OWN data.

For each company (and overall), compute how long applications stayed in
'Applied' before first moving on (Screening/Assessment/Interview/Rejected...).
Report median days and sample size; small samples are flagged as low
confidence. Simple, transparent regression-free statistics.
"""

from datetime import timezone
from sqlalchemy import func
from ..models import Application, StatusHistory, Job


def _aware(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _median(values):
    if not values:
        return None
    vs = sorted(values)
    n = len(vs)
    mid = n // 2
    return vs[mid] if n % 2 else (vs[mid - 1] + vs[mid]) / 2


def _response_days(app):
    """
    Days between 'Applied' and the first status after it. None if never applied
    or still waiting.
    """
    hist = sorted(app.history, key=lambda h: h.changed_at)
    applied_at = None
    for h in hist:
        if applied_at is None and h.to_status == "Applied":
            applied_at = _aware(h.changed_at)
        elif applied_at is not None and h.to_status != "Applied":
            delta = (_aware(h.changed_at) - applied_at).days
            return max(delta, 0)
    # fallback: applied_on date vs first movement
    if applied_at is None and app.applied_on:
        if app.status not in ("Applied", "Saved"):
            return None  # can't compute without history timestamps
    return None


def response_stats(user_id):
    """
    Returns {
      overall: {median_days, samples, waiting},
      by_company: [ {company, median_days, samples} ... ] (sorted, top 8)
      waiting: [ {company, role, days_waiting} ... ]  # applied, no reply yet
    }
    """
    apps = (Application.query.join(Job, Application.job_id == Job.id)
            .filter(Application.user_id == user_id).all())

    per_company = {}
    all_days = []
    waiting = []

    for a in apps:
        company = a.job.company or "Unknown"
        days = _response_days(a)
        if days is not None:
            all_days.append(days)
            per_company.setdefault(company, []).append(days)
        elif a.status == "Applied" and a.applied_on:
            waiting_days = (func.now() is not None)  # placeholder, computed below
            from datetime import datetime
            waiting_days = (datetime.now(timezone.utc).date() - a.applied_on).days
            waiting.append({"company": company, "role": a.job.role or "Untitled role",
                            "days": waiting_days})

    waiting.sort(key=lambda w: -w["days"])

    overall = {
        "median_days": _median(all_days),
        "samples": len(all_days),
    }

    by_company = [{"company": c, "median_days": _median(ds), "samples": len(ds)}
                  for c, ds in per_company.items()]
    by_company.sort(key=lambda r: (r["median_days"] is None, r["median_days"] or 0))

    return {"overall": overall, "by_company": by_company[:8], "waiting": waiting[:6]}


def waiting_note(stats):
    """A human sentence, with honest confidence labelling."""
    o = stats["overall"]
    if not o["samples"]:
        if stats["waiting"]:
            return ("Not enough history yet to predict response times — "
                    f"but {len(stats['waiting'])} application(s) are currently awaiting a reply.")
        return "Once you move a few applications past 'Applied', typical response times will appear here."
    med = o["median_days"]
    conf = "high" if o["samples"] >= 8 else "reasonable" if o["samples"] >= 4 else "low"
    return (f"Across {o['samples']} application(s) with a reply, the median first response "
            f"took {med} day{'s' if med != 1 else ''} (confidence: {conf} — {o['samples']} samples).")
