
import re
import numpy as np
import spacy
from sklearn.feature_extraction.text import TfidfVectorizer

CANONICAL_SKILLS = {
    "it": [
        "Python", "Java", "JavaScript", "TypeScript", "C#", "C++", "C",
        "PHP", "Go", "Rust", "Kotlin", "Swift", "Ruby", "Dart",
        "React", "React Native", "Next.js", "Vue.js", "Angular",
        "HTML", "CSS", "Tailwind CSS", "Bootstrap", "SASS", "jQuery",
        "Node.js", "Express.js", "Spring Boot", "ASP.NET Core",
        "Django", "Flask", "FastAPI", "Laravel", "NestJS",
        "MySQL", "PostgreSQL", "MongoDB", "SQL Server", "SQLite",
        "Oracle", "Redis", "Firebase", "Supabase",
        "AWS", "Azure", "Google Cloud Platform", "Docker", "Kubernetes",
        "CI/CD", "Jenkins", "GitHub Actions", "Terraform", "Ansible",
        "Git", "GitHub", "GitLab", "Postman", "Swagger", "Jira",
        "Figma", "VS Code", "Linux",
        "RESTful API", "GraphQL", "Microservices",
        "Object-Oriented Programming", "Design Patterns", "Agile", "Scrum",
        "Machine Learning", "Deep Learning", "Artificial Intelligence",
        "Data Structures and Algorithms",
        "Unit Testing", "JWT", "OAuth 2.0", "WebSocket",
        "Vite", "Expo", "ESLint", "Ethers.js", "Responsive Design",
        "Subnetting", "VLAN", "OSPF", "RIP", "NAT", "IPv4", "IPv6",
        "TCP/IP", "DNS", "DHCP", "SNMP", "SSH", "ARP",
        "pfSense", "OpenWRT", "FreePBX", "Active Directory",
        "Snort", "Wireshark", "Checkmk", "Nessus",
        "VirtualBox", "OpenStack", "Proxmox",
        "Infrastructure as Code", "VoIP", "Firewall", "VPN",
        "Cisco", "Juniper", "FortiGate",
    ],
    "business_sales": [
        "Sales Execution", "Customer Service", "Negotiation",
        "Customer Relationship Management", "Lead Generation",
        "B2B Sales", "Account Management", "Sales Strategy",
        "Business Development", "Cold Calling", "Salesforce",
        "Partner Management", "Channel Development",
    ],
    "marketing": [
        "Content Marketing", "SEO", "SEM", "Social Media Marketing",
        "Copywriting", "Email Marketing", "Google Analytics",
        "Brand Management", "Market Research", "Digital Marketing",
        "Content Creation", "Canva", "Adobe Photoshop", "Video Editing",
        "Content Planning", "Facebook Ads", "TikTok Content Creation",
        "Meta Business Suite", "Microsoft Office",
    ],
    "finance_accounting": [
        "Financial Analysis", "Bookkeeping", "Accounts Payable",
        "Accounts Receivable", "Budgeting", "Forecasting",
        "Tax Preparation", "Auditing", "QuickBooks", "Excel",
        "Financial Reporting", "Reconciliation", "Cost Accounting",
    ],
    "hr": [
        "Recruitment", "Talent Acquisition", "Onboarding",
        "Employee Relations", "Performance Management", "HRIS",
        "Payroll", "Training and Development", "Compensation and Benefits",
    ],
}


ALIASES = {
    "js": "JavaScript", "ts": "TypeScript", "ml": "Machine Learning",
    "ai": "Artificial Intelligence", "oop": "Object-Oriented Programming",
    "k8s": "Kubernetes", "nodejs": "Node.js", "node js": "Node.js",
    "reactjs": "React", "react.js": "React", "vuejs": "Vue.js",
    "postgres": "PostgreSQL", "mongo": "MongoDB",
    "rest api": "RESTful API", "restful apis": "RESTful API",
    "rest api integration": "RESTful API",
    "ci cd": "CI/CD", "gcp": "Google Cloud Platform",
    "crm": "Customer Relationship Management",
    "iac": "Infrastructure as Code",
    "infrastructure-as-code (iac)": "Infrastructure as Code",
    "tcp": "TCP/IP", "ip": "TCP/IP",
}

ALL_CANONICAL = [(domain, skill) for domain, skills in CANONICAL_SKILLS.items() for skill in skills]
CANONICAL_NAMES = [skill for _, skill in ALL_CANONICAL]


def _normalize(text):
    return re.sub(r'\s+', ' ', text.strip().lower())


def _resolve_canonical(raw_text):
    """Tra thẳng xem 1 chuỗi có khớp CHÍNH XÁC (kể cả qua bí danh) với
    tên chuẩn nào trong từ điển không -- dùng chung cho cả match_skill()
    (chuỗi đã tách sẵn) lẫn EntityRuler (chuỗi nguyên trong văn bản)."""
    normalized = _normalize(raw_text)
    if normalized in ALIASES:
        canonical = ALIASES[normalized]
        domain = next((d for d, s in ALL_CANONICAL if s == canonical), "it")
        return canonical, domain
    for domain, skill in ALL_CANONICAL:
        if _normalize(skill) == normalized:
            return skill, domain
    return None, None


_ruler_nlp = spacy.blank("en")
_ruler = _ruler_nlp.add_pipe("entity_ruler", config={"phrase_matcher_attr": "LOWER"})

_ruler_patterns = [
    {"label": "SKILL", "pattern": skill, "id": domain}
    for domain, skill in ALL_CANONICAL
]
_ruler_patterns += [
    {"label": "SKILL", "pattern": alias, "id": next((d for d, s in ALL_CANONICAL if s == canonical), "it")}
    for alias, canonical in ALIASES.items()
]
_ruler.add_patterns(_ruler_patterns)


def extract_known_skills_ner(raw_text):
    """Chạy EntityRuler trực tiếp trên văn bản gốc (CHƯA tách theo dấu
    câu) để bắt các kỹ năng đã có trong từ điển -- đúng nghĩa 1 bước
    NER thật (nhận diện theo ranh giới từ, không phân biệt hoa/thường),
    khác với split_skill_items() ở ner_extractor.py chỉ tách chuỗi
    thô. Không thay thế split_skill_items -- chỉ bổ sung thêm 1 nguồn
    tín hiệu đáng tin cậy cho các kỹ năng ĐÃ BIẾT trước."""
    if not raw_text.strip():
        return []
    doc = _ruler_nlp(raw_text)
    results = []
    for ent in doc.ents:
        canonical, domain = _resolve_canonical(ent.text)
        if canonical is None:
            canonical, domain = ent.text, ent.ent_id_ or "it"
        results.append({"raw": ent.text, "canonical": canonical, "domain": domain, "score": 1.0})
    return results


_vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4))
_canonical_matrix = _vectorizer.fit_transform(CANONICAL_NAMES).toarray()
_canonical_norms = np.linalg.norm(_canonical_matrix, axis=1)
_canonical_norms[_canonical_norms == 0] = 1e-9  # tránh chia cho 0

def _cosine_similarity_to_all(vec):
    vec_norm = np.linalg.norm(vec)
    if vec_norm == 0:
        return np.zeros(len(CANONICAL_NAMES))
    dot_products = _canonical_matrix @ vec
    return dot_products / (_canonical_norms * vec_norm)


def match_skill(raw_skill, threshold=0.55):
    """So khớp 1 kỹ năng thô với gazetteer.
    Trả về (tên chuẩn, lĩnh vực, điểm tương đồng)."""
    canonical, domain = _resolve_canonical(raw_skill)
    if canonical:
        return canonical, domain, 1.0

    query_vec = _vectorizer.transform([_normalize(raw_skill)]).toarray()[0]
    similarities = _cosine_similarity_to_all(query_vec)
    best_idx = int(np.argmax(similarities))
    best_score = float(similarities[best_idx])

    word_count = len(_normalize(raw_skill).split())
    effective_threshold = threshold if word_count >= 3 else threshold + 0.2

    if best_score >= effective_threshold:
        domain, skill = ALL_CANONICAL[best_idx]
        return skill, domain, best_score

    return raw_skill, "unmatched", best_score


def match_skills(raw_skills, raw_text=""):
    """Áp dụng match_skill cho toàn bộ danh sách SKILLS thô lấy từ
    ner_extractor.py, loại trùng theo tên chuẩn sau khi so khớp.
    Nếu có raw_text (SKILLS_RAW từ ner_extractor.py), chạy EntityRuler
    trước để lấy các kỹ năng đã biết chắc chắn (score=1.0), rồi mới bổ
    sung phần còn lại bằng cách tách chuỗi + so khớp mờ như cũ."""
    results, seen = [], set()

    if raw_text:
        for r in extract_known_skills_ner(raw_text):
            key = r["canonical"].lower()
            if key not in seen:
                seen.add(key)
                results.append(r)

    for raw in raw_skills:
        canonical, domain, score = match_skill(raw)
        key = canonical.lower()
        if key in seen:
            continue
        seen.add(key)
        results.append({
            "raw": raw,
            "canonical": canonical,
            "domain": domain,
            "score": round(score, 3),
        })
    return results


if __name__ == "__main__":
    from reader import extract_text_sections
    from ner_extractor import extract_entities

    paragraph_text, table_text = extract_text_sections("data/CV_Huynh_Tien_Loi.pdf")
    entities = extract_entities(paragraph_text, table_text)

    matched = match_skills(entities["SKILLS"], entities.get("SKILLS_RAW", ""))
    for m in matched:
        tag = "OK " if m["domain"] != "unmatched" else "?? "
        print(f"{tag}{m['raw']!r:40s} -> {m['canonical']:30s} [{m['domain']:20s}] score={m['score']}")