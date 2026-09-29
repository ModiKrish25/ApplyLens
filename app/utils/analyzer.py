"""
Resume Health Analyzer — a TRANSPARENT checklist/heuristic score.

This is NOT an objective measure of resume quality (no such thing exists).
Every point is tied to a visible, rule-based check so users can see exactly
where the score comes from and ignore anything they disagree with.
"""

import re


def health_checklist(analysis, text):
    """
    analysis: output of parser.analyze_resume_text
    text:     raw resume text
    Returns {category: [ {label, passed, points, max, note} ]}, total, max.
    """
    checks = []

    def add(category, label, passed, points, note=""):
        checks.append({"category": category, "label": label, "passed": bool(passed),
                       "points": points if passed else 0, "max": points, "note": note})

    sections = analysis.get("sections", {})
    skills = analysis.get("skills", [])
    contact = analysis.get("contact", {})

    # --- Contact & basics (20)
    add("Contact & Basics", "Email address found", "email" in contact, 8)
    add("Contact & Basics", "Phone number found", "phone" in contact, 6)
    add("Contact & Basics", "LinkedIn or GitHub profile found",
        bool(contact.get("linkedin") or contact.get("github")), 6)

    # --- Structure (30)
    for name, pts in [("experience", 10), ("education", 8), ("skills", 8)]:
        add("Structure", f"Has a clear '{name.title()}' section", name in sections, pts)
    add("Structure", "Resume length 200-900 words (1-2 pages)",
        200 <= analysis.get("word_count", 0) <= 900, 4,
        note=f"{analysis.get('word_count', 0)} words detected")

    # --- Skills evidence (20)
    add("Skills", "At least 8 distinct technical skills detected", len(skills) >= 8, 8,
        note=f"{len(skills)} detected")
    strong = [s for s in skills if s["count"] >= 2]
    add("Skills", "At least 5 skills appear more than once (reinforced)", len(strong) >= 5, 6)
    add("Skills", "Skills backed by Experience or Projects sections",
        any(s["in_section"] for s in skills), 6)

    # --- Content quality (30)
    bullets = re.findall(r"^\s*[•\-\*]\s+\S", text, flags=re.MULTILINE)
    add("Content", "Uses bullet points (10 or more)", len(bullets) >= 10, 8,
        note=f"{len(bullets)} bullets found")
    numbers = re.findall(r"\d+%|\b\d{2,}\+?\b|\$\s?\d|\b\d+x\b", text)
    add("Content", "Quantified impact (numbers/percentages present)",
        len(numbers) >= 3, 12, note=f"{len(numbers)} numeric mentions")
    action_words = r"\b(built|developed|designed|implemented|led|created|improved|reduced|increased|automated|migrated|optimized|launched|delivered|architected)\b"
    actions = re.findall(action_words, text, flags=re.IGNORECASE)
    add("Content", "Strong action verbs (5 or more)", len(actions) >= 5, 10,
        note=f"{len(actions)} action verbs found")

    total = sum(c["points"] for c in checks)
    max_total = sum(c["max"] for c in checks)
    return {"checks": checks, "total": total, "max": max_total,
            "score": round(100 * total / max_total) if max_total else 0}


def score_band(score):
    if score >= 85:
        return "strong", "Strong resume — covers the fundamentals well."
    if score >= 70:
        return "good", "Decent foundation with a few fixable gaps."
    if score >= 50:
        return "fair", "Several important items missing — worth a pass."
    return "weak", "Many basics are missing — start with failed checks below."
