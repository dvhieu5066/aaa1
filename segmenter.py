
import re
from difflib import SequenceMatcher

HEADING_SYNONYMS = {
    "education": ["education", "educational background", "academic background", "qualification"],
    "experience": ["experience", "work experience", "professional experience", "employment history",
                   "organizational & volunteer experience", "organizational and volunteer experience"],
    "skills": ["skills", "technical skills", "soft skills", "core competencies", "expertise"],
    "projects": ["projects", "personal projects", "key projects"],
}

OTHER_HEADINGS = [
    "summary", "objective", "profile", "about me",
    "certifications", "certificates", "awards", "achievements",
    "languages", "activities", "publications", "references",
    "contact", "interests", "hobbies",
]

ALL_CANDIDATES = [(block, syn) for block, syns in HEADING_SYNONYMS.items() for syn in syns]
ALL_CANDIDATES += [("other", h) for h in OTHER_HEADINGS]


def merge_wrapped_lines(text):
    raw_lines = text.split("\n")
    merged = []
    for line in raw_lines:
        line = line.strip()
        if merged and merged[-1].rstrip().endswith(","):
            merged[-1] = merged[-1].rstrip() + " " + line
        else:
            merged.append(line)
    return "\n".join(merged)


def _clean_heading_candidate(text):
    text = text.strip().lower()
    text = re.sub(r'^[\divxIVX]+[\.\):]\s*', '', text)
    text = re.sub(r'[_\-=.]{2,}\s*$', '', text)
    return text.rstrip(':').strip()


def _starts_with_uppercase(line):
    stripped = line.strip()
    return bool(stripped) and stripped[0].isupper()


def _match_compound(cleaned):

    parts = [p.strip() for p in re.split(r'\s*(?:&|and|/)\s*', cleaned) if p.strip()]
    if len(parts) < 2:
        return None
    for part in parts:
        for block, syn in ALL_CANDIDATES:
            if part == syn:
                return block
    return None


def _match_full_line(cleaned):
    if not cleaned:
        return None

    for block, syn in ALL_CANDIDATES:
        if cleaned == syn:
            return block

    compound = _match_compound(cleaned)
    if compound:
        return compound

    if len(cleaned.split()) <= 4:
        best_block, best_score = None, 0.0
        for block, syn in ALL_CANDIDATES:
            score = SequenceMatcher(None, cleaned, syn).ratio()
            if score > best_score:
                best_score, best_block = score, block
        if best_score >= 0.85:
            return best_block

    return None


def _match_prefix_label(cleaned):
    if ":" not in cleaned:
        return None, None
    head, _, rest = cleaned.partition(":")
    head, rest = head.strip(), rest.strip()
    for block, syn in ALL_CANDIDATES:
        if head == syn and not rest:
            return block, ""
    return None, None


def _split_heading_and_content(line):
    if not _starts_with_uppercase(line):
        return None, None

    cleaned = _clean_heading_candidate(line)

    block = _match_full_line(cleaned)
    if block:
        return block, ""

    block, rest = _match_prefix_label(cleaned)
    if block:
        return block, rest

    return None, None


def segment_cv(text):
    text = merge_wrapped_lines(text)
    blocks = {"personal": [], "education": [], "experience": [], "skills": [], "projects": [], "other": []}
    current_block = "personal"

    for line in text.split("\n"):
        block, rest = _split_heading_and_content(line)
        if block:
            current_block = block
            if rest:
                blocks[current_block].append(rest)
            continue
        blocks[current_block].append(line)

    return {k: "\n".join(v) for k, v in blocks.items()}