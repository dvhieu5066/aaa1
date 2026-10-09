import os

from aggregator import build_record
from ground_truth import GROUND_TRUTH

SKILL_COLUMNS = [
    "Kỹ năng CNTT", "Kỹ năng Kinh doanh/Bán hàng", "Kỹ năng Marketing",
    "Kỹ năng Tài chính - Kế toán", "Kỹ năng Nhân sự", "Kỹ năng chưa xác định",
]


def _split_field(value):
    if not value:
        return []
    return [item.strip() for item in value.split(";") if item.strip()]


def _get_extracted_skills(record):
    skills = []
    for col in SKILL_COLUMNS:
        skills.extend(_split_field(record.get(col, "")))
    return skills


def _normalize(text):
    return text.strip().lower()


def _relaxed_match(item, candidates):
    """So khớp nới lỏng -- coi là khớp nếu 1 trong 2 chuỗi là chuỗi con
    của chuỗi kia. Cần thiết vì hệ thống đôi khi tách 1 thực thể thành
    nhiều mảnh nhỏ hơn ground truth hoặc ngược lại."""
    item_norm = _normalize(item)
    for c in candidates:
        c_norm = _normalize(c)
        if item_norm in c_norm or c_norm in item_norm:
            return True
    return False


def compute_prf(ground_truth_list, extracted_list):
    if not ground_truth_list and not extracted_list:
        return 1.0, 1.0, 1.0, 0, 0, 0

    tp = sum(1 for gt in ground_truth_list if _relaxed_match(gt, extracted_list))
    fn = len(ground_truth_list) - tp
    fp = sum(1 for ex in extracted_list if not _relaxed_match(ex, ground_truth_list))

    precision = tp / (tp + fp) if (tp + fp) > 0 else (1.0 if not extracted_list else 0.0)
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return precision, recall, f1, tp, fp, fn


def evaluate(data_folder="data"):
    per_category_scores = {"education_org": [], "experience_org": [], "skills": []}
    name_correct, name_total = 0, 0

    print(f"{'Tệp':40s} {'Danh mục':16s} {'P':>6s} {'R':>6s} {'F1':>6s}   (TP/FP/FN)")
    print("-" * 90)

    for filename, gt in GROUND_TRUTH.items():
        file_path = os.path.join(data_folder, filename)
        if not os.path.exists(file_path):
            print(f"[BỎ QUA] Không tìm thấy file: {file_path}")
            continue

        record = build_record(file_path)

        name_total += 1
        extracted_name = record.get("Họ tên", "")
        if _normalize(gt["name"]) == _normalize(extracted_name):
            name_correct += 1
            name_result = "OK"
        else:
            name_result = f"SAI (he thong ra: {extracted_name!r})"
        print(f"{filename:40s} {'Họ tên':16s} {'':>6s} {'':>6s} {'':>6s}   {name_result}")

        extracted = {
            "education_org": _split_field(record.get("Học vấn", "")),
            "experience_org": _split_field(record.get("Kinh nghiệm (Tổ chức)", "")),
            "skills": _get_extracted_skills(record),
        }

        for category in ("education_org", "experience_org", "skills"):
            p, r, f1, tp, fp, fn = compute_prf(gt[category], extracted[category])
            per_category_scores[category].append((p, r, f1))
            print(f"{'':40s} {category:16s} {p:6.2f} {r:6.2f} {f1:6.2f}   ({tp}/{fp}/{fn})")

        print()

    print("=" * 90)
    print("TỔNG KẾT (trung bình cộng qua các CV đã đánh giá)")
    print("=" * 90)

    for category, scores in per_category_scores.items():
        if not scores:
            continue
        avg_p = sum(s[0] for s in scores) / len(scores)
        avg_r = sum(s[1] for s in scores) / len(scores)
        avg_f1 = sum(s[2] for s in scores) / len(scores)
        print(f"{category:20s}  Precision={avg_p:.3f}  Recall={avg_r:.3f}  F1={avg_f1:.3f}")

    if name_total:
        print(f"{'name_accuracy':20s}  {name_correct}/{name_total} = {name_correct/name_total:.3f}")


if __name__ == "__main__":
    evaluate("data")