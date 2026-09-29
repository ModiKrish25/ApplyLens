"""
Interview Prep Kit — rule-based question & checklist generation.

No LLM, no mystery: every question is derived from an actual gap or claim
in the user's resume vs the job description, so the user always knows WHY
they should prepare an answer.
"""

import re
from .matcher import _alias_pattern

ROUND_FOCUS = {
    "phone": "Recruiter phone screen — motivation, logistics, salary expectations.",
    "video": "Video technical screen — live problem solving, past project walkthrough.",
    "onsite": "Onsite loop — deep dives, whiteboarding, system or team fit.",
    "task": "Take-home / task review — they will probe how you made decisions.",
}

BEHAVIOURAL_QUESTIONS = [
    ("Ownership", "Tell me about a project you owned end-to-end. What broke, and what did you do?"),
    ("Conflict", "Describe a disagreement with a teammate about a technical choice. How did it end?"),
    ("Deadline", "A deadline was slipping and scope had to change — walk me through your call."),
    ("Learning", "Tell me about the hardest new technology you had to learn fast. What did you do?"),
    ("Failure", "Describe something you shipped that failed or had to be rolled back."),
]


def generate_prep_kit(analysis, job):
    """
    analysis: dict from parser.analyze_resume_text (with full_text)
    job:      Job model
    Returns a dict of rule-derived prep items, each with a 'why'.
    """
    text = analysis.get("full_text", "")
    sections = analysis.get("sections", {})
    required = job.required_skills
    preferred = job.preferred_skills

    deep_dives, gaps, sharpen = [], [], []

    def find_evidence(skill):
        """Evidence snippets + section names + mention count for one skill."""
        evidence, sections_hit, count = [], [], 0
        for alias, canonical in _skill_aliases(skill):
            for m in _alias_pattern(alias).finditer(text):
                count += 1
                if len(evidence) < 2:
                    start, end = max(0, m.start() - 70), min(len(text), m.end() + 70)
                    evidence.append(" ".join(text[start:end].split()))
            for sname, stext in sections.items():
                if _alias_pattern(alias).search(stext) and sname.title() not in sections_hit:
                    sections_hit.append(sname.title())
        return evidence, sections_hit, count

    for skill in required:
        evidence, secs, count = find_evidence(skill)
        if count == 0:
            gaps.append({
                "name": skill, "kind": "not_detected",
                "q": f"{skill} is required but not found in your resume. If asked, what's your honest current level — and your plan to close the gap?",
                "why": "Required by the job, absent from your resume",
            })
        elif count == 1:
            gaps.append({
                "name": skill, "kind": "single_mention",
                "q": f"You mention {skill} exactly once. Pick that one project and rehearse explaining it in depth — expect a follow-up question.",
                "why": "Single mention — likely to be probed",
            })
        else:
            deep_dives.append({
                "name": skill, "mentions": count,
                "evidence": evidence[0] if evidence else "",
                "q": f"Expect a deep dive on {skill}: be ready to whiteboard how you used it and defend one technical decision.",
                "why": f"Strengthened by {count} mentions — interviewers go deep on strengths",
            })

    for skill in preferred:
        evidence, secs, count = find_evidence(skill)
        if count > 0:
            sharpen.append({
                "name": skill, "mentions": count,
                "q": f"{skill} is a preferred skill you do show — prepare one crisp example that links it to a real result.",
                "why": "Preferred skill present — cheap win to polish",
            })

    # Projects: rank by how many required skills the project text touches
    # parser returns projects as plain strings
    projects = analysis.get("projects", [])
    ranked = []
    for p in projects:
        ptext = p if isinstance(p, str) else (p.get("name") or "") + " " + (p.get("description") or "")
        label = p if isinstance(p, str) else (p.get("name") or "Untitled project")
        hits = 0
        for s in required:
            for alias, _c in _skill_aliases(s):
                if _alias_pattern(alias).search(ptext):
                    hits += 1
                    break
        ranked.append((hits, label, ptext.strip()))
    ranked.sort(key=lambda x: -x[0])
    top_projects = [{"name": label, "text": ptext, "hits": hits}
                    for hits, label, ptext in ranked[:2] if label]

    # Quantified claims: the numbers they will ask about
    sentences = re.split(r"(?<=[.!?])\s+", text)
    number_claims = []
    for s in sentences:
        if re.search(r"\b\d+(?:\.\d+)?%|\b\d{2,}\+?\b|\$\s?\d+", s):
            clean = " ".join(s.split())
            if len(clean) > 20:
                number_claims.append(clean)
        if len(number_claims) >= 3:
            break

    # Experience: most recent entries (parser usually returns reverse-chron)
    experience = analysis.get("experience", [])[:2]

    kit = {
        "job": job,
        "round_focus": ROUND_FOCUS.get((job.work_type or "").lower()),
        "deep_dives": deep_dives,
        "gaps": gaps,
        "sharpen": sharpen,
        "top_projects": top_projects,
        "number_claims": number_claims,
        "experience": experience,
        "behavioural": BEHAVIOURAL_QUESTIONS,
    }
    kit["total_items"] = (len(deep_dives) + len(gaps) + len(sharpen) +
                          len(top_projects) + len(number_claims) + len(experience) +
                          len(BEHAVIOURAL_QUESTIONS))
    return kit


def _skill_aliases(skill):
    """Yield (alias, canonical) pairs whose canonical name == skill."""
    from .skills import SKILL_DICT  # lazy import keeps module load cheap
    return [(a, c) for a, c in SKILL_DICT.items() if c == skill]
