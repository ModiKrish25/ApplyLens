"""Rule-based resume section detection, contact extraction, and JD parsing."""
import re
import json
from collections import Counter
from .skills import SKILL_DICT, SOFT_SKILL_KEYWORDS, SECTION_ALIASES, CONTACT_PATTERNS, canon_skill

STOPWORDS = set("""a an and are as at be by for from has have how in is it its of on or that the
to was were what when where which who will with you your our their they this these those we us
i me my mine please apply role job work working team teams company companies years year experience
experience ensure etc using use used ability able strong excellent good great across about into
within must should can could may might per plus new like more most other others all any each
well also than then them there here who's over under help helps helping looking join us you'll
we're our you're position candidate candidates requirements responsibilities qualifications
preferred required plus bonus nice-to-have""".split())


# ---------------------------------------------------------------- resume parsing

def split_sections(text):
    """
    Detect resume sections by matching known section headings on their own line.
    Returns {canonical_section_name: section_text}.
    """
    lines = text.splitlines()
    headings = []  # (line_index, canonical_name)
    for i, raw in enumerate(lines):
        line = raw.strip()
        if not line or len(line) > 60:
            continue
        clean = re.sub(r"[^A-Za-z &/']", "", line).strip().lower()
        if not clean or clean != line.lower():
            continue  # heading lines are usually just words
        for canonical, aliases in SECTION_ALIASES.items():
            for alias in aliases:
                if clean == alias:
                    headings.append((i, canonical))
                    break
    sections = {}
    for idx, (start, name) in enumerate(headings):
        end = headings[idx + 1][0] if idx + 1 < len(headings) else len(lines)
        body = "\n".join(lines[start + 1:end]).strip()
        if body:
            sections[name] = sections.get(name, "") + "\n" + body
    return {k: v.strip() for k, v in sections.items()}


def detect_skills(text):
    """Transparent keyword matching against the curated skill dictionary."""
    found = {}          # canonical -> [evidence snippets]
    lowered = text.lower()
    for alias, canonical in SKILL_DICT.items():
        # word-boundary match so "go" doesn't match "google"
        pattern = r"(?<![A-Za-z0-9+#.])" + re.escape(alias) + r"(?![A-Za-z0-9+#])"
        for m in re.finditer(pattern, lowered):
            start = max(0, m.start() - 45)
            end = min(len(text), m.end() + 45)
            snippet = " ".join(text[start:end].split())
            found.setdefault(canonical, []).append(snippet)
    return found


def extract_contact(text):
    contact = {}
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    first_lines = "\n".join(lines[:15])

    # Name heuristic: the first short, mostly-alphabetic line at the very top
    # that isn't a headline or contact link. Transparent and conservative.
    for line in lines[:2]:
        lowered = line.lower()
        if any(k in lowered for k in ("@", "http", "linkedin", "github", "resume",
                                      "curriculum", "phone", "email")):
            continue
        clean = re.sub(r"[^A-Za-z .'\-]", "", line).strip()
        words = [w for w in clean.split() if w]
        if 1 < len(words) <= 4 and all(w[0].isalpha() for w in words):
            contact["name"] = clean
            break
    email = re.search(CONTACT_PATTERNS["email"], first_lines)
    if email:
        contact["email"] = email.group(0)
    phone = re.search(CONTACT_PATTERNS["phone"], first_lines)
    if phone:
        contact["phone"] = phone.group(0).strip()
    for key in ("linkedin", "github", "portfolio"):
        m = re.search(CONTACT_PATTERNS[key], text, flags=re.IGNORECASE)
        if m:
            contact[key] = m.group(0).rstrip(".,)")
    return contact


def split_bullets(section_text):
    """Split a section into bullet-ish items."""
    items = re.split(r"\n(?=[•\-\*–▪◦]|\d+[\.\)])|\n(?=[A-Z][^\n]{3,70}:)", section_text)
    return [i.strip(" \t•-*–▪◦") for i in items if i.strip(" \t•-*–▪◦")]


def parse_education(section_text):
    degrees = r"(B\.?Tech|B\.?E\.?|B\.?Sc|B\.?Com|B\.?A\.?|M\.?Tech|M\.?E\.?|M\.?Sc|M\.?Com|M\.?B\.?A\.?|M\.?C\.?A\.?|Ph\.?D|Bachelor|Master|Diploma|High School|Class (?:X|XII|10th|12th))"
    items = []
    for line in section_text.splitlines():
        if re.search(degrees, line, flags=re.IGNORECASE):
            items.append(line.strip(" \t•-*–"))
    return items


def parse_certifications(section_text):
    items = []
    for line in section_text.splitlines():
        if line.strip():
            items.append(line.strip(" \t•-*–"))
    return items[:20]


def parse_experience(section_text):
    """Heuristic: a date range on a line marks the start of an experience entry."""
    date_pat = re.compile(
        r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*\d{4})"
        r"(\s*(?:-|–|—|to)\s*)"
        r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*\d{4}|Present|Current|Till date|Now)",
        flags=re.IGNORECASE)
    entries, current = [], None
    for line in section_text.splitlines():
        m = date_pat.search(line)
        if m:
            if current:
                entries.append(current)
            current = {"dates": m.group(0), "title": line.replace(m.group(0), "").strip(" •-*–|"), "detail": ""}
        elif current is not None:
            current["detail"] += line + "\n"
    if current:
        entries.append(current)
    return entries


def analyze_resume_text(text):
    """Full pipeline: sections, skills, contact, education, experience, projects."""
    sections = split_sections(text)
    found = detect_skills(text)
    skills = [
        {"name": name, "count": len(evs), "evidence": evs[:3],
         "in_section": _which_sections(name, sections)}
        for name, evs in found.items()
    ]
    skills.sort(key=lambda s: -s["count"])
    exp_text = sections.get("experience", "")
    proj_text = sections.get("projects", "")
    return {
        "sections": sections,
        "skills": skills,
        "contact": extract_contact(text),
        "education": parse_education(sections.get("education", "")),
        "experience": parse_experience(exp_text),
        "projects": split_bullets(proj_text)[:15],
        "certifications": parse_certifications(sections.get("certifications", "")),
        "word_count": len(text.split()),
    }


def _which_sections(canonical, sections):
    where = []
    for sname, stext in sections.items():
        if canon_skill(stext.lower().split()[0] if stext else ""):
            pass
        for alias, c in SKILL_DICT.items():
            if c == canonical and re.search(r"(?<![A-Za-z0-9+#.])" + re.escape(alias) + r"(?![A-Za-z0-9+#])", stext.lower()):
                where.append(sname.title())
                break
    return sorted(set(where))


# ---------------------------------------------------------------- JD parsing

def parse_job_description(text):
    """
    Extract structured fields from a pasted job description using labelled-line
    and section heuristics. Everything is rule-based and auditable.
    """
    lowered = text.lower()
    result = {
        "role": _grab(text, ["job title", "role", "position", "designation"]),
        "company": _grab(text, ["company", "organisation", "organization", "employer"]),
        "location": _grab(text, ["location", "job location", "office"]),
        "salary": _grab(text, ["salary", "compensation", "ctc", "pay"]),
        "experience": _grab(text, ["experience", "years of experience", "yoe"]),
        "work_type": _grab(text, ["job type", "employment type", "type"]),
    }

    # Remote flag
    result["remote"] = bool(re.search(r"\b(remote|work from home|wfh|fully distributed)\b", lowered))

    # Experience like "2+ years" / "3-5 years"
    if not result["experience"]:
        m = re.search(r"(\d+)\s*\+?\s*(?:-|–|to)?\s*(\d+)?\s*\+?\s*years?", lowered)
        if m:
            result["experience"] = m.group(0).title()

    req, pref = extract_skill_requirements(text)
    result["required_skills"] = req
    result["preferred_skills"] = pref
    result["keywords"] = keyword_profile(text)
    return result


def _grab(text, labels):
    for label in labels:
        m = re.search(
            r"^\s*" + re.escape(label) + r"\s*[:\-–]\s*(.+)$",
            text, flags=re.IGNORECASE | re.MULTILINE)
        if m:
            return m.group(1).strip()[:160]
    return ""


def extract_skill_requirements(text):
    """
    Return (required, preferred) skill lists.
    Preferred skills come from Preferred/Nice-to-have/Plus sections;
    everything else detected is Required.
    """
    preferred_section = ""
    m = re.search(r"(?im)^\s*(nice to have|nice-to-have|preferred(?: skills)?|good to have|bonus(?: points| skills)?|plus(?: points)?)\s*[:\-–]?\s*$", text)
    if m:
        rest = text[m.end():]
        stop = re.search(r"(?im)^\s*(requirements|required skills|must have|responsibilities|about|qualifications)\b", rest)
        preferred_section = rest[:stop.start()] if stop else rest[:600]

    found = detect_skills(text)
    preferred_names = set()
    if preferred_section:
        preferred_names = set(detect_skills(preferred_section).keys())

    ordered = sorted(found.keys(), key=lambda k: -len(found[k]))
    required = [s for s in ordered if s not in preferred_names]
    preferred = [s for s in ordered if s in preferred_names]
    return required, preferred


def keyword_profile(text, top_n=40):
    """Frequency profile of meaningful words + soft skills found in the JD."""
    soft = {}
    lowered = text.lower()
    for alias, canonical in SOFT_SKILL_KEYWORDS.items():
        n = len(re.findall(r"(?<![a-z])" + re.escape(alias) + r"(?![a-z])", lowered))
        if n:
            soft[canonical] = soft.get(canonical, 0) + n

    words = re.findall(r"[A-Za-z][A-Za-z0-9+#.\-]{1,}", text.lower())
    tech = Counter(w for w in words if w not in STOPWORDS and not w.isdigit())
    technical = [{"word": w, "count": c} for w, c in tech.most_common(top_n)]
    soft_list = [{"word": w, "count": c} for w, c in sorted(soft.items(), key=lambda x: -x[1])]
    return {"technical": technical, "soft": soft_list}
