import os

from reader import extract_text_sections
from ner_extractor import extract_entities
from gazetteer import match_skills, CANONICAL_SKILLS
from regex import extract_contact_info

DOMAIN_LABELS = {
    "it": "Kỹ năng CNTT",
    "business_sales": "Kỹ năng Kinh doanh/Bán hàng",
    "marketing": "Kỹ năng Marketing",
    "finance_accounting": "Kỹ năng Tài chính - Kế toán",
    "hr": "Kỹ năng Nhân sự",
}

SUPPORTED_EXT = (".pdf", ".docx")


def _pick_name(person_list):
    return person_list[0] if person_list else "Không xác định"


def _join(items, sep="; "):
    return sep.join(items) if items else ""


def group_skills_by_domain(matched_skills):
    grouped = {domain: [] for domain in CANONICAL_SKILLS}
    unmatched = []
    for item in matched_skills:
        if item["domain"] == "unmatched":
            unmatched.append(item["raw"])
        else:
            grouped[item["domain"]].append(item["canonical"])
    return grouped, unmatched


def build_record(file_path):
    paragraph_text, table_text = extract_text_sections(file_path)
    full_text = paragraph_text + "\n" + table_text

    contact = extract_contact_info(full_text)
    entities = extract_entities(paragraph_text, table_text)
    matched_skills = match_skills(entities["SKILLS"], entities.get("SKILLS_RAW", ""))
    grouped_skills, unmatched_skills = group_skills_by_domain(matched_skills)

    record = {
        "Tệp": os.path.basename(file_path),
        "Họ tên": _pick_name(entities["PERSON"]),
        "Số điện thoại": _join(contact["phones"], ", "),
        "Email": _join(contact["emails"], ", "),
        "LinkedIn": _join(contact["links"]["linkedin"], ", "),
        "GitHub": _join(contact["links"]["github"], ", "),
        "Địa điểm": _join(entities["LOCATION"], ", "),
        "Học vấn": _join(entities["EDUCATION"]),
        "Kinh nghiệm (Tổ chức)": _join(entities["EXPERIENCE_ORG"]),
    }
    for domain, label in DOMAIN_LABELS.items():
        record[label] = _join(grouped_skills[domain])
    record["Kỹ năng chưa xác định"] = _join(unmatched_skills)

    return record


def build_dataset(folder_path):
    records = []
    for name in sorted(os.listdir(folder_path)):
        if not name.lower().endswith(SUPPORTED_EXT):
            continue
        path = os.path.join(folder_path, name)
        try:
            records.append(build_record(path))
        except Exception as e:
            records.append({"Tệp": name, "Lỗi": str(e)})
    return records


if __name__ == "__main__":
    dataset = build_dataset("data")
    for r in dataset:
        print(r.get("Họ tên", r.get("Tệp")), "-", r.get("Email", r.get("Lỗi", "")))
