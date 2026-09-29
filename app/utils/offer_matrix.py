"""
Offer Decision Matrix — transparent weighted scoring.

The user picks what matters to them (weights); the math is simple and fully
visible: every factor shows its weight, its 0-10 rating, and its contribution.
No black box — change a weight and the ranking changes deterministically.
"""

import re

# factor key -> (label, help text)
FACTORS = {
    "salary":   ("Salary", "Parsed salary from the posting, normalized to a 0-10 band"),
    "remote":   ("Remote friendly", "Remote-friendly roles score 10, onsite 4, unknown 6"),
    "growth":   ("Growth signal", "Seniority step-up vs your experience and learning budget hints"),
    "location": ("Location convenience", "Closer / more convenient locations score higher"),
}

DEFAULT_WEIGHTS = {"salary": 40, "remote": 25, "growth": 20, "location": 15}

_NUM = re.compile(r"([\d,]+(?:\.\d+)?)\s*[-–—to]{1,3}\s*([\d,]+(?:\.\d+)?)\s*(k|K|lpa|LPA)?")
_SINGLE = re.compile(r"([\d,]+(?:\.\d+)?)\s*(k|K|lpa|LPA)?\s*(?:per year|/yr|/year|annum|pa\b)?")

LUXURY_HINTS = ("learning", "budget", "conference", "course", "certification", "upskilling")
SENIORITY_STEPS = {"intern": 0, "junior": 1, "associate": 2, "": 3,
                   "senior": 4, "lead": 5, "principal": 6, "staff": 6, "manager": 5}


def _parse_salary_band(salary_text):
    """Return (min, max) annual-ish numbers from free text, or None."""
    if not salary_text:
        return None
    m = _NUM.search(salary_text)
    if m:
        lo, hi, suffix = float(m.group(1).replace(",", "")), float(m.group(2).replace(",", "")), m.group(3) or ""
        mult = 1000 if suffix.lower() == "k" else 1
        return (lo * mult, hi * mult)
    m = _SINGLE.search(salary_text)
    if m:
        v, suffix = float(m.group(1).replace(",", "")), m.group(2) or ""
        mult = 1000 if suffix.lower() == "k" else 1
        return (v * mult, v * mult)
    return None


def _salary_score(band):
    """Transparent banding: 0-10. Ranges are arbitrary but visible and editable."""
    if not band:
        return 5  # unknown -> neutral middle, clearly flagged in the UI
    top = band[1]
    for threshold, score in [(40_000, 3), (70_000, 5), (100_000, 7),
                             (140_000, 8), (200_000, 9), (300_000, 10)]:
        if top <= threshold:
            return score
    return 10


def _seniority_rank(text):
    t = (text or "").lower()
    for kw, rank in SENIORITY_STEPS.items():
        if kw and kw in t:
            return rank
    return 3


def rate_offer(job, user_experience=""):
    """
    job: Job model (salary, remote, location, experience, source_text)
    Returns {factor: {label, help, rating, note}} — ratings 0-10.
    """
    band = _parse_salary_band(job.salary or "")

    exp_rank = _seniority_rank(user_experience)
    job_rank = _seniority_rank(job.experience or "")
    growth = min(10, max(0, 4 + (job_rank - exp_rank) * 3))
    growth_note = f"Role targets level '{job.experience or 'unspecified'}' vs your background '{user_experience or 'unspecified'}'"

    src = (job.source_text or "").lower()
    learning_budget = any(h in src for h in LUXURY_HINTS)
    if learning_budget:
        growth = min(10, growth + 1)
        growth_note += " · posting mentions learning/certification support"

    salary_score = _salary_score(band)
    remote_score = 10 if job.remote else 4
    loc_note = job.location or "Location not recorded"
    # unknown location is neutral
    location_score = 6 if not job.location else (8 if job.remote else 5)

    return {
        "salary": {"label": FACTORS["salary"][0], "help": FACTORS["salary"][1],
                   "rating": salary_score,
                   "note": f"Listed: {job.salary or 'not recorded — neutral 5/10'}"},
        "remote": {"label": FACTORS["remote"][0], "help": FACTORS["remote"][1],
                   "rating": remote_score,
                   "note": "Remote-friendly" if job.remote else (loc_note if loc_note != "Location not recorded" else "Onsite/unknown")},
        "growth": {"label": FACTORS["growth"][0], "help": FACTORS["growth"][1],
                   "rating": growth, "note": growth_note},
        "location": {"label": FACTORS["location"][0], "help": FACTORS["location"][1],
                     "rating": location_score, "note": loc_note},
    }, band


def score_offers(offers, weights, user_experience=""):
    """
    offers: list of Application rows (status == Offer) with .job loaded
    weights: dict factor -> 0-100 int
    Returns list of dicts: {app, ratings, weighted, band} sorted best-first.
    """
    total_weight = sum(weights.get(k, 0) for k in FACTORS) or 1
    rows = []
    for o in offers:
        ratings, band = rate_offer(o.job, user_experience)
        weighted = {}
        total = 0.0
        for k, r in ratings.items():
            w = weights.get(k, 0)
            contrib = round(w / total_weight * r * 10, 1)  # 0-100 scale
            weighted[k] = {"label": r["label"], "weight": w,
                           "weight_pct": round(100 * w / total_weight),
                           "rating": r["rating"], "note": r["note"],
                           "contribution": contrib}
            total += contrib
        rows.append({"app": o, "ratings": ratings, "weighted": weighted,
                     "total": round(total, 1), "band": band})
    rows.sort(key=lambda x: -x["total"])
    return rows
