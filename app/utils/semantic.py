"""
Semantic similarity between a resume and a job description — WITH quoted evidence.

Two engines, chosen automatically:

1. "neural"  — sentence-transformers embeddings (all-MiniLM-L6-v2) if the
   package is installed. Cross-encodes meaning, e.g. "managed deployments"
   ≈ "DevOps experience". Runs locally, no API calls.
2. "lexical" — dependency-free fallback: TF-IDF-weighted token overlap with
   stemming and stopword removal. Works everywhere, still quoted.

Either way the UI shows, for each JD requirement sentence, the closest resume
sentence(s) — so every similarity claim has visible evidence.
"""

import math
import re
from collections import Counter

try:  # optional neural engine
    from sentence_transformers import SentenceTransformer, util as st_util
    _NEURAL_AVAILABLE = True
except Exception:  # ImportError or model load issues at import time
    _NEURAL_AVAILABLE = False

from .parser import STOPWORDS


MODEL_NAME = "all-MiniLM-L6-v2"
_model = None  # lazy singleton


def engine_name():
    return "neural" if _NEURAL_AVAILABLE else "lexical"


def _split_sentences(text):
    """Sentence-ish chunks: split on punctuation/bullets, keep meaningful length."""
    raw = re.split(r"(?<=[.!?])\s+|\n+", text)
    out = []
    for s in raw:
        s = s.strip(" \t•-*–▪◦|")
        s = re.sub(r"\s+", " ", s)
        if 25 <= len(s) <= 400 and re.search(r"[A-Za-z]{3}", s):
            out.append(s)
    return out


def _req_sentences(jd_text):
    """JD sentences that look like requirements (contain a skill/verb cue)."""
    sents = _split_sentences(jd_text)
    cue = re.compile(
        r"\b(you will|responsib|require|must|experience with|experience in|"
        r"strong |proficien|familiar|knowledge of|skilled|expertise|"
        r"\d+\+?\s*years?|ownership|build|design|develop|manage|maintain)\b",
        re.IGNORECASE)
    return [s for s in sents if cue.search(s)][:12]


_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9+#.\-]{1,}")

def _tokens(sentence):
    words = [w.lower() for w in _TOKEN_RE.findall(sentence)]
    return [w for w in words if w not in STOPWORDS and len(w) > 1]


def _stem(word):
    """Tiny Porter-ish stemmer: enough for matching plurals/gerunds."""
    for suf in ("ing", "ed", "es", "s"):
        if word.endswith(suf) and len(word) > len(suf) + 2:
            return word[: -len(suf)]
    return word


def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


# ------------------------------------------------------------- lexical engine

def _lexical_scores(jd_sents, resume_sents):
    """TF-IDF-ish cosine between every JD sentence and resume sentence."""
    jd_toks = [_tokens(s) for s in jd_sents]
    rs_toks = [_tokens(s) for s in resume_sents]

    df = Counter()
    for toks in jd_toks + rs_toks:
        df.update(set(toks))
    n_docs = len(jd_toks) + len(rs_toks) or 1

    def idf(w):
        return math.log((n_docs + 1) / (df.get(w, 0) + 1)) + 1

    def vec(toks):
        tf = Counter(_stem(t) for t in toks)
        if not tf:
            return {}
        max_tf = max(tf.values())
        return {w: (c / max_tf) * idf(w) for w, c in tf.items()}

    def dot(a, b):
        return sum(v * b.get(w, 0.0) for w, v in a.items())

    jd_vecs = [vec(t) for t in jd_toks]
    rs_vecs = [vec(t) for t in rs_toks]

    def norm(v):
        return math.sqrt(sum(x * x for x in v.values())) or 1.0

    scores = []
    for jv in jd_vecs:
        jn = norm(jv)
        row = []
        for rv in rs_vecs:
            cos = dot(jv, rv) / (jn * norm(rv)) if jv and rv else 0.0
            row.append(cos)
        scores.append(row)
    return scores


# ------------------------------------------------------------- neural engine

def _neural_scores(jd_sents, resume_sents):
    model = _get_model()
    j_emb = model.encode(jd_sents, normalize_embeddings=True)
    r_emb = model.encode(resume_sents, normalize_embeddings=True)
    sim = st_util.cos_sim(j_emb, r_emb)  # tensor (jd x resume)
    return [[float(v) for v in row] for row in sim]


# ------------------------------------------------------------------- public

def semantic_match(jd_text, resume_text, top_k=2):
    """
    Returns {
      engine: 'neural'|'lexical',
      pairs: [ {jd, jd_index, matches: [ {resume, score} ], best_score } ],
      overall: 0-100            # mean of best-pair scores
      coverage_hint: 'strong'|'moderate'|'weak'
    }
    Only pairs with a non-trivial best score are meaningful; weak ones are
    returned too so the UI can show "nothing in your resume matches this".
    """
    jd_sents = _req_sentences(jd_text or "")
    resume_sents = _split_sentences(resume_text or "")
    if not jd_sents or not resume_sents:
        return {"engine": engine_name(), "pairs": [], "overall": None,
                "coverage_hint": "unknown"}

    scores = (_neural_scores(jd_sents, resume_sents) if _NEURAL_AVAILABLE
              else _lexical_scores(jd_sents, resume_sents))

    pairs = []
    for i, row in enumerate(scores):
        ranked = sorted(range(len(row)), key=lambda j: -row[j])[:top_k]
        matches = [{"resume": resume_sents[j], "score": round(row[j] * 100)}
                   for j in ranked if row[j] > 0.05]
        best = max(row) if row else 0.0
        pairs.append({
            "jd": jd_sents[i], "jd_index": i, "matches": matches,
            "best_score": round(best * 100),
        })

    meaningful = [p["best_score"] for p in pairs] or [0]
    overall = round(sum(meaningful) / len(meaningful))

    # threshold is engine-aware: neural similarities run lower than lexical overlap
    strong, moderate = (55, 35) if _NEURAL_AVAILABLE else (40, 20)
    hint = ("strong" if overall >= strong
            else "moderate" if overall >= moderate else "weak")

    return {"engine": engine_name(), "pairs": pairs,
            "overall": overall, "coverage_hint": hint}
