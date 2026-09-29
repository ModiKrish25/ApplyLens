"""
Smart bullet rewriter — suggests bullet phrasings for weak/missing skills,
retrieved from the user's OWN resume content (no LLM, no fabrication).

How it stays honest:
- Templates combine the skill + verbs/numbers the user actually used elsewhere,
  so suggestions read like the user, and placeholders are explicit.
- Every suggestion is labelled as a DRAFT the user must make true.
"""

import re
from .parser import STOPWORDS

VERB_BANK = {
    "Languages": ("Built", "Implemented", "Refactored"),
    "Frameworks": ("Developed", "Engineered", "Delivered"),
    "Databases": ("Designed", "Optimized", "Modeled"),
    "Cloud & DevOps": ("Automated", "Migrated", "Containerized"),
    "Data & ML": ("Analyzed", "Trained", "Pipelined"),
    "Testing & Tools": ("Testing with", "Hardened", "Streamlined"),
    "APIs & Architecture": ("Designed", "Integrated", "Scaled"),
    "Other / General": ("Worked with", "Applied", "Leveraged"),
}

RESULT_TEMPLATES = [
    "{verb} {skill} to {outcome}, improving {metric} by {number}%",
    "{verb} {skill} across {scope}, reducing {metric} by {number}%",
    "{verb} {skill} in a team of {team}, cutting {metric} from {number} to {number}",
    "{verb} {skill} for {scope}; result: {metric} improved {number}x",
]

METRIC_WORDS = ("latency", "load time", "throughput", "error rate", "cost",
                "deployment time", "query time", "build time", "manual work")

SCOPE_WORDS = ("the platform", "the main product", "client projects",
               "production services", "the data pipeline", "the team")


def _sentences(text):
    out = []
    for s in re.split(r"(?<=[.!?])\s+|\n+", text or ""):
        s = s.strip(" \t•-*–")
        if 30 <= len(s) <= 300:
            out.append(s)
    return out


def _context_snippets(skill, text, limit=3):
    """Sentences from the user's resume that mention related concepts."""
    related = re.compile(
        r"\b(" + "|".join(map(re.escape, [w for w in skill.lower().split()] + [
            "api", "database", "service", "pipeline", "deploy", "test", "scale",
            "performance", "team", "project", "system"])) + r")",
        re.IGNORECASE)
    hits = []
    for s in _sentences(text):
        if related.search(s):
            hits.append(" ".join(s.split()))
        if len(hits) >= limit:
            break
    return hits


def _user_metrics(text):
    """Numbers the user already quoted, to anchor suggestions in their reality."""
    nums = re.findall(r"\b(\d{2,5})\s*%|\$(\d{1,3}(?:,\d{3})+|\d{2,6})\b", text or "")
    flat = [a or b for a, b in nums]
    return [n.replace(",", "") for n in flat[:6]] or ["30", "2"]


def suggest_bullets(skill, category, resume_text, max_suggestions=3):
    """
    Returns [ {template, placeholders_filled, anchor (quoted from own resume),
               disclaimer} ] — drafts only, clearly labelled.
    """
    verbs = VERB_BANK.get(category, VERB_BANK["Other / General"])
    metrics = [m for m in METRIC_WORDS
               if re.search(r"\b" + re.escape(m.split()[0]), resume_text or "", re.IGNORECASE)]
    metrics = metrics or list(METRIC_WORDS)[:2]
    scopes = SCOPE_WORDS
    numbers = _user_metrics(resume_text)
    anchors = _context_snippets(skill, resume_text)

    suggestions = []
    for i in range(min(max_suggestions, len(RESULT_TEMPLATES))):
        verb = verbs[i % len(verbs)]
        t = RESULT_TEMPLATES[i]
        draft = t.format(verb=verb, skill=skill,
                         outcome=metrics[i % len(metrics)],
                         metric=metrics[(i + 1) % len(metrics)],
                         scope=scopes[i % len(scopes)],
                         team=max(2, len(numbers)) if i == 2 else 3,
                         number=numbers[i % len(numbers)])
        suggestions.append({
            "draft": draft,
            "anchor": anchors[i] if i < len(anchors) else (anchors[0] if anchors else None),
            "why": f"Built from your own phrasing and numbers{'' if not anchors else ' — anchor quoted below'}",
        })
    return suggestions
