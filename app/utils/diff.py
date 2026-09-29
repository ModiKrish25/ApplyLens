"""
Version comparison between two stored resume versions.
Pure-Python diff of extracted skills, sections, and checklist scores.
"""

import json
from .skills import SKILL_DICT


def _skills(resume):
    try:
        return json.loads(resume.skills_json or "[]")
    except json.JSONDecodeError:
        return []


def _sections(resume):
    try:
        return json.loads(resume.sections_json or "{}")
    except json.JSONDecodeError:
        return {}


def compare_versions(ra, rb):
    sa = {s["name"]: s["count"] for s in _skills(ra)}
    sb = {s["name"]: s["count"] for s in _skills(rb)}
    all_skills = sorted(set(sa) | set(sb), key=lambda s: (-(sa.get(s, 0) + sb.get(s, 0)), s))

    rows = []
    for name in all_skills:
        ca, cb = sa.get(name, 0), sb.get(name, 0)
        if ca and not cb:
            status = "lost"
        elif cb and not ca:
            status = "added"
        elif cb > ca:
            status = "up"
        elif cb < ca:
            status = "down"
        else:
            status = "same"
        rows.append({"name": name, "a": ca, "b": cb, "status": status})

    sec_a, sec_b = _sections(ra), _sections(rb)
    section_rows = []
    for name in ["summary", "experience", "education", "skills", "projects",
                 "certifications", "achievements"]:
        in_a, in_b = name in sec_a, name in sec_b
        section_rows.append({
            "name": name.title(),
            "a": "Yes" if in_a else "—",
            "b": "Yes" if in_b else "—",
            "status": ("same" if in_a == in_b else
                       ("added" if (in_b and not in_a) else "lost")),
        })

    stats = {
        "added": sum(1 for r in rows if r["status"] == "added"),
        "lost": sum(1 for r in rows if r["status"] == "lost"),
        "improved": sum(1 for r in rows if r["status"] == "up"),
        "weakened": sum(1 for r in rows if r["status"] == "down"),
        "score_a": ra.health_score,
        "score_b": rb.health_score,
        "words_a": ra.word_count,
        "words_b": rb.word_count,
    }
    return {"rows": rows, "sections": section_rows, "stats": stats,
            "total_a": len(sa), "total_b": len(sb)}
