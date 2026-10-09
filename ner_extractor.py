import re
import spacy
from segmenter import segment_cv

nlp = spacy.load("en_core_web_sm")

VN_PROVINCES = [
    "ho chi minh city", "hcmc", "hanoi", "ha noi", "da nang", "can tho",
    "hai phong", "thu duc", "binh thanh", "bien hoa", "vung tau",
    "nha trang", "hue", "quy nhon", "buon ma thuot", "long xuyen",
    "rach gia", "thai nguyen", "nam dinh", "vinh", "hai duong",
    "thanh hoa", "phan thiet",
]

JOB_TITLE_MARKERS = {
    "developer", "engineer", "designer", "architect", "analyst",
    "scientist", "backend", "frontend", "full-stack", "fullstack",
    "programmer", "technician", "devops",
    "manager", "specialist", "consultant", "coordinator", "assistant",
    "director", "executive", "representative", "associate", "supervisor",
    "officer", "administrator", "lead", "head", "chief", "intern",
    "trainee", "student", "senior", "junior",
    "salesperson", "marketer", "accountant", "auditor", "recruiter", "hr", "banker",
    "teacher", "tutor", "lecturer",
}

ENTITY_CONNECTORS = {",", "-", "–", "—", "&", "and"}

DEGREE_START_PATTERN = re.compile(
    r'^(bachelor|master|higher diploma|diploma|associate|certificate|'
    r'ph\.?d|doctorate)\b',
    re.IGNORECASE
)
INSTITUTION_HINTS = ("university", "college", "institute", "academy", "school", "polytechnic")

ADDRESS_LABEL_PATTERN = re.compile(r'^(address|location)\s*:\s*(.+)$', re.IGNORECASE)
CONTACT_LABEL_PATTERN = re.compile(
    r'^(phone|tel|mobile|email|e-mail|address|location|github|linkedin|'
    r'website|portfolio|skype|whatsapp|zalo)\s*:',
    re.IGNORECASE
)

DATE_RANGE_PATTERN = re.compile(
    r'\b(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*\d{4}'
    r'|\d{1,2}/\d{4}|\d{4})'
    r'\s*[-–—]\s*'
    r'(?:Present|Now'
    r'|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*\d{4}'
    r'|\d{1,2}/\d{4}|\d{4})',
    re.IGNORECASE
)


def strip_bullet(line):
    return re.sub(r'^[•\-*\u2022\u25CF\u25AA]+\s*', '', line).strip()


def strip_trailing_dates(line):
    return DATE_RANGE_PATTERN.sub('', line).strip()


def strip_midline_noise(line):
    line = re.sub(r'\bGPA\s*\(?[^)]*\)?\s*:\s*[\d./]+', '', line, flags=re.IGNORECASE)
    line = re.sub(r'\bCGPA\s*:\s*[\d./]+', '', line, flags=re.IGNORECASE)
    line = re.sub(r'\bIELTS\s*:\s*[\d.]+', '', line, flags=re.IGNORECASE)
    line = re.sub(r'\bTOEIC\s*:\s*[\d/]+', '', line, flags=re.IGNORECASE)
    line = re.sub(r'\bSpecialization\s*:\s*\S+', '', line, flags=re.IGNORECASE)
    line = re.sub(r'\bMajor\s*:\s*[^|]+', '', line, flags=re.IGNORECASE)
    line = re.sub(r'\bMajor\s+in\s+.+$', '', line, flags=re.IGNORECASE)
    line = re.sub(r'\(Expected\s*\d{4}\)', '', line, flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', line).strip()


def strip_degree_line(line):
    stripped = line.strip()
    if not DEGREE_START_PATTERN.match(stripped):
        return line

    matches = list(re.finditer(r'\b(of|in)\b', stripped, flags=re.IGNORECASE))
    if matches:
        tail = stripped[matches[-1].end():].strip()
        if any(hint in tail.lower() for hint in INSTITUTION_HINTS):
            return tail

    return ""


def normalize_casing(line):
    tokens = line.split(' ')
    result = []
    i = 0
    while i < len(tokens):
        j = i
        run = []
        while j < len(tokens) and (
            tokens[j] == '&' or (tokens[j].isupper() and any(c.isalpha() for c in tokens[j]))
        ):
            run.append(tokens[j])
            j += 1
        if len(run) >= 2:
            result.append(' '.join(t.title() if t != '&' else t for t in run))
            i = j
        else:
            result.append(tokens[i])
            i += 1
    return ' '.join(result)


def is_contact_line(line):
    return bool(CONTACT_LABEL_PATTERN.match(line.strip()))


def is_list_line(line):
    segments = [s.strip() for s in line.split(",") if s.strip()]
    if len(segments) < 3:
        return False
    avg_words = sum(len(s.split()) for s in segments) / len(segments)
    return avg_words <= 5

def is_long_sentence(line, max_words=12):
    line = line.strip()
    if line.endswith((".", "!", "?")):
        return True
    return len(line.split()) > max_words

def is_stat_line(line):
    line = line.strip()
    if re.match(r'^(GPA|CGPA|TOEIC|TOEFL|IELTS)\b', line, re.IGNORECASE):
        return True
    return bool(re.match(r'^[A-Za-z][A-Za-z\s]{1,30}:\s*[\d./%\-–]+\s*$', line))


def _get_lines(block_text, skip_noise=False, filter_degree=False):
    raw_lines = [strip_bullet(l) for l in block_text.split("\n") if l.strip()]

    expanded = []
    for l in raw_lines:
        expanded.extend(p.strip() for p in l.split("|") if p.strip())

    lines = [strip_trailing_dates(l) for l in expanded]
    if skip_noise:
        lines = [strip_midline_noise(l) for l in lines]
    lines = [l for l in lines if l and not is_contact_line(l) and not is_stat_line(l)]
    if skip_noise:
        lines = [l for l in lines if not is_list_line(l) and not is_long_sentence(l)]
    if filter_degree:
        lines = [strip_degree_line(l) for l in lines]
        lines = [l for l in lines if l]
    return [normalize_casing(l) for l in lines]


def extract_org_entities(doc):
    raw_ents = [e for e in doc.ents if e.label_ in ("ORG", "PERSON")]
    if not raw_ents:
        return []

    merged = [raw_ents[0]]
    for nxt in raw_ents[1:]:
        current = merged[-1]
        gap_words = [t.text.lower() for t in doc[current.end:nxt.start]]
        if gap_words and len(gap_words) <= 2 and all(w in ENTITY_CONNECTORS for w in gap_words):
            merged[-1] = doc[current.start:nxt.end]
        else:
            merged.append(nxt)

    return [span.text for span in merged if any(t.pos_ == "PROPN" for t in span)]

def extract_experience_lines(doc):
    raw_ents = [e for e in doc.ents if e.label_ in ("ORG", "PERSON")]
    has_real_org = any(any(t.pos_ == "PROPN" for t in e) for e in raw_ents)
    return [doc.text] if has_real_org else []

def extract_labeled_address(text):
    for line in text.split("\n"):
        m = ADDRESS_LABEL_PATTERN.match(line.strip())
        if m:
            return [p.strip() for p in m.group(2).split(",") if p.strip()]
    return []


def rescue_location(person_list):
    location, real_person = [], []
    for p in person_list:
        if p.lower().strip() in VN_PROVINCES:
            location.append(p)
        else:
            real_person.append(p)
    return location, real_person


def extract_name_fallback(text):
    first_line = strip_bullet(text.strip().split("\n")[0])
    name_part = re.split(r'\s{2,}|[|·•]', first_line)[0].strip()
    words = name_part.split()

    cut = len(words)
    for i, w in enumerate(words):
        if w.strip(".,").lower() in JOB_TITLE_MARKERS:
            cut = i
            break
    words = words[:cut]

    if not (2 <= len(words) <= 4):
        return None
    name = " ".join(words)
    return name.title() if name.isupper() else name


def split_skill_items(text):
    protected = []

    def _protect(m):
        protected.append(m.group(0))
        return f"__PROTECTED_{len(protected)-1}__"

    text = text.replace("\xa0", " ")
    text = re.sub(r'\([^)]*\)', _protect, text)

    all_items = []
    for line in text.split("\n"):
        line = strip_bullet(line)
        for segment in re.split(r'[·|]', line):
            segment = strip_bullet(segment.strip())
            segment = re.sub(r'^[A-Za-z][A-Za-z &/]{0,30}:\s*', '', segment)
            for item in re.split(r'[,/]', segment):
                item = item.strip()
                if item:
                    all_items.append(item)

    result = []
    for item in all_items:
        for idx, val in enumerate(protected):
            item = item.replace(f"__PROTECTED_{idx}__", val)
        if len(item.split()) <= 8:
            result.append(item)
    return list(dict.fromkeys(result))


def _dedup(items):
    return list(dict.fromkeys(items))


def extract_entities(text, table_text=""):
    blocks = segment_cv(text)

    labeled_location = extract_labeled_address(blocks["personal"])

    person, location = [], list(labeled_location)
    for doc in nlp.pipe(_get_lines(blocks["personal"], skip_noise=True)):
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                person.append(ent.text)
            elif ent.label_ in ("GPE", "LOC"):
                location.append(ent.text)

    rescued_loc, person = rescue_location(person)
    location += rescued_loc

    fallback_name = extract_name_fallback(blocks["personal"])
    if fallback_name:
        fallback_lower = fallback_name.lower()
        already_full_match = any(fallback_lower in p.lower() for p in person)
        if not already_full_match:
            person = [p for p in person if p.lower() not in fallback_lower]
            person.insert(0, fallback_name)

    education_raw = []
    for doc in nlp.pipe(_get_lines(blocks["education"], skip_noise=True, filter_degree=True)):
        education_raw.extend(extract_org_entities(doc))

    experience_org = []
    for doc in nlp.pipe(_get_lines(blocks["experience"], skip_noise=True)):
        experience_org.extend(extract_experience_lines(doc))

    skills_raw_text = blocks["skills"]
    if table_text.strip():
        skills_raw_text += "\n" + table_text

    skills = split_skill_items(blocks["skills"])
    if table_text.strip():
        skills += split_skill_items(table_text)
        skills = list(dict.fromkeys(skills))
    return {
        "PERSON": _dedup(person),
        "LOCATION": _dedup(location),
        "EDUCATION": _dedup(education_raw),
        "EXPERIENCE_ORG": _dedup(experience_org),
        "SKILLS": skills,
        "SKILLS_RAW": skills_raw_text,
    }