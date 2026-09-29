"""
Resume <-> Job matching engine.

No mysterious "AI score": every matched/missing skill is shown with the exact
evidence (where in the resume it appears) so users can judge for themselves.
"""

import re
from .skills import SKILL_DICT, skill_category


def _alias_pattern(alias):
    return re.compile(r"(?<![A-Za-z0-9+#.])" + re.escape(alias) + r"(?![A-Za-z0-9+#])", re.IGNORECASE)


def match_resume_to_job(resume_analysis, job):
    """
    resume_analysis: dict from parser.analyze_resume_text (or rebuilt from a Resume row)
    job: Job model with required_skills / preferred_skills
    Returns a dict with per-skill coverage, evidence, and summary stats.
    """
    text = resume_analysis.get("full_text", "")
    sections = resume_analysis.get("sections", {})

    required = job.required_skills
    preferred = job.preferred_skills

    def skill_status(skill):
        """Return dict with matched bool, evidence, section hits, mention count."""
        evidence, sections_hit, count = [], [], 0
        for alias, canonical in SKILL_DICT.items():
            if canonical != skill:
                continue
            for m in _alias_pattern(alias).finditer(text):
                count += 1
                if len(evidence) < 3:
                    start = max(0, m.start() - 60)
                    end = min(len(text), m.end() + 60)
                    evidence.append(" ".join(text[start:end].split()))
            for sname, stext in sections.items():
                if _alias_pattern(alias).search(stext) and sname.title() not in sections_hit:
                    sections_hit.append(sname.title())
        return {"name": skill, "matched": count > 0, "count": count,
                "evidence": evidence, "sections": sections_hit}

    req_rows = [skill_status(s) for s in required]
    pref_rows = [skill_status(s) for s in preferred]

    req_matched = sum(1 for r in req_rows if r["matched"])
    pref_matched = sum(1 for r in pref_rows if r["matched"])

    # Transparent weighted coverage: required = weight 3, preferred = weight 1
    req_pct = 100.0 * req_matched / len(req_rows) if req_rows else None
    pref_pct = 100.0 * pref_matched / len(pref_rows) if pref_rows else None
    if req_rows and pref_rows:
        coverage = round((3 * req_pct + pref_pct) / 4)
    elif req_rows:
        coverage = round(req_pct)
    elif pref_rows:
        coverage = round(pref_pct)
    else:
        coverage = 0

    weak = [r for r in req_rows + pref_rows if r["matched"] and r["count"] == 1]
    missing = [r for r in req_rows if not r["matched"]]

    # Group missing required skills by category for the gap analyzer
    gaps = {"have": [], "strengthen": [], "not_detected": []}
    for r in req_rows + pref_rows:
        entry = {"name": r["name"], "category": skill_category(r["name"]),
                 "count": r["count"], "level_hint": "preferred" if r in pref_rows else "required"}
        if not r["matched"]:
            gaps["not_detected"].append(entry)
        elif r["count"] == 1:
            gaps["strengthen"].append(entry)
        else:
            gaps["have"].append(entry)

    return {
        "coverage": coverage,
        "required_pct": round(req_pct) if req_pct is not None else None,
        "preferred_pct": round(pref_pct) if pref_pct is not None else None,
        "required": req_rows,
        "preferred": pref_rows,
        "req_matched": req_matched,
        "req_total": len(req_rows),
        "pref_matched": pref_matched,
        "pref_total": len(pref_rows),
        "weak": weak,
        "missing": missing,
        "gaps": gaps,
    }


def verdict(coverage):
    if coverage >= 75:
        return "strong", "Strong match — your resume covers most of what this job asks for."
    if coverage >= 50:
        return "moderate", "Moderate match — several required skills are not evident."
    return "weak", "Weak match — most required skills were not detected in this resume."
