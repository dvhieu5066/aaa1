import os
import tempfile

import pandas as pd
import streamlit as st

from aggregator import build_record, build_dataset, DOMAIN_LABELS
from exporter import export_to_excel

st.set_page_config(page_title="Trích xuất thông tin CV bằng NER", layout="wide")
st.title("Hệ thống trích xuất thông tin CV sử dụng kỹ thuật NER")

DISPLAY_FIELDS = [
    "Họ tên", "Số điện thoại", "Email", "LinkedIn", "GitHub",
    "Địa điểm", "Học vấn", "Kinh nghiệm (Tổ chức)",
]


def _record_to_excel_bytes(record):
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp_path = tmp.name
    export_to_excel([record], tmp_path)
    with open(tmp_path, "rb") as f:
        data = f.read()
    os.unlink(tmp_path)
    return data


def _render_record(record):
    col1, col2 = st.columns(2)
    fields_left = DISPLAY_FIELDS[:4]
    fields_right = DISPLAY_FIELDS[4:]

    with col1:
        for field in fields_left:
            st.markdown(f"**{field}:** {record.get(field) or '—'}")
    with col2:
        for field in fields_right:
            st.markdown(f"**{field}:** {record.get(field) or '—'}")

    st.subheader("Kỹ năng theo lĩnh vực")
    has_any_skill = False
    for label in DOMAIN_LABELS.values():
        if record.get(label):
            has_any_skill = True
            st.markdown(f"**{label}:** {record[label]}")
    if not has_any_skill:
        st.caption("Không nhận diện được kỹ năng nào thuộc các lĩnh vực đã biết.")

    if record.get("Kỹ năng chưa xác định"):
        with st.expander("Kỹ năng chưa xác định (chưa có trong từ điển Gazetteer)"):
            st.write(record["Kỹ năng chưa xác định"])

    if record.get("Lỗi"):
        st.error(f"Lỗi khi xử lý: {record['Lỗi']}")


tab1, tab2 = st.tabs(["Xử lý 1 CV", "Xử lý hàng loạt"])

with tab1:
    uploaded_file = st.file_uploader("Tải lên 1 file CV (PDF hoặc DOCX)", type=["pdf", "docx"])

    if uploaded_file is not None:
        suffix = os.path.splitext(uploaded_file.name)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name

        try:
            with st.spinner("Đang trích xuất thông tin..."):
                record = build_record(tmp_path)
            record["Tệp"] = uploaded_file.name

            st.success("Trích xuất thành công")
            _render_record(record)

            st.download_button(
                "Tải kết quả (Excel)",
                data=_record_to_excel_bytes(record),
                file_name=f"ket_qua_{os.path.splitext(uploaded_file.name)[0]}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except Exception as e:
            st.error(f"Không thể xử lý file này: {e}")
        finally:
            os.unlink(tmp_path)

with tab2:
    folder_path = st.text_input("Đường dẫn thư mục chứa CV", value="data")

    if st.button("Xử lý toàn bộ thư mục"):
        if not os.path.isdir(folder_path):
            st.error("Không tìm thấy thư mục này. Kiểm tra lại đường dẫn.")
        else:
            with st.spinner("Đang xử lý hàng loạt..."):
                dataset = build_dataset(folder_path)

            n_error = sum(1 for r in dataset if r.get("Lỗi"))
            st.success(f"Đã xử lý {len(dataset)} tệp ({n_error} tệp lỗi, nếu có).")

            df = pd.DataFrame(dataset)
            st.dataframe(df, use_container_width=True)

            output_path = os.path.join("output", "ket_qua_trich_xuat_cv.xlsx")
            export_to_excel(dataset, output_path)
            with open(output_path, "rb") as f:
                st.download_button(
                    "Tải báo cáo Excel đầy đủ",
                    data=f.read(),
                    file_name="ket_qua_trich_xuat_cv.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )