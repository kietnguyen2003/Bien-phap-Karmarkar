"""Vietnamese browser interface: python -m streamlit run streamlit_app.py."""
from pathlib import Path
import logging
import sys

import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, str(Path(__file__).resolve().parent / "karmarkar-project" / "src"))
from karmarkar.general_lp import GeneralSolverConfig
from karmarkar.web_service import build_problem, run_problem


def clear_report():
    st.session_state["report"] = None


def dimensions_changed():
    clear_report()
    # Remove vectors whose length depended on the previous problem dimensions.
    for key in list(st.session_state):
        if key == "objective" or key.startswith("row_") or key.startswith("var_"):
            del st.session_state[key]


def input_form(n, m):
    with st.form("problem"):
        st.subheader("1. Hàm mục tiêu")
        sense = st.selectbox("Chiều tối ưu", ["min", "max"], key="sense")
        objective = st.text_input(
            f"Hệ số mục tiêu ({n} số)",
            value=" ".join(["-1"] + ["0"] * (n - 1)), key="objective",
        )
        constant = st.text_input("Hằng số mục tiêu", "2", key="constant")
        st.caption("Nhập hệ số theo thứ tự x1, x2, …, cách nhau bằng khoảng trắng. Ví dụ: 1/3 -2 0.5")
        st.subheader("2. Ràng buộc")
        rows = []
        if not m:
            st.caption("Bài toán chỉ có các điều kiện dấu biến bên dưới.")
        for i in range(m):
            a, b, c = st.columns([3, 1, 1])
            coefficients = a.text_input(
                f"Hệ số ràng buộc {i + 1}", " ".join(["1"] * n), key=f"row_{i}_a",
            )
            sign = b.selectbox(f"Dấu {i + 1}", ["<=", ">=", "="], key=f"row_{i}_sign")
            rhs = c.text_input(f"Vế phải {i + 1}", "2", key=f"row_{i}_rhs")
            rows.append((coefficients, sign, rhs))
        st.subheader("3. Điều kiện dấu biến")
        columns = st.columns(min(n, 4))
        signs = [columns[j % len(columns)].selectbox(
            f"x{j + 1}", [">=0", "<=0", "free"], key=f"var_{j}",
            format_func=lambda value: "Tự do" if value == "free" else value,
        ) for j in range(n)]
        submitted = st.form_submit_button("Giải bài toán", type="primary", key="solve")
    return submitted, (objective, constant, rows, signs, sense)


def show_result(report):
    st.subheader("Kết quả lần giải gần nhất")
    st.caption("Kết quả ứng với dữ liệu đã gửi. Sau khi sửa form, bấm Giải bài toán để cập nhật.")
    labels = {
        "APPROX_TOL_REACHED": "Đã đạt sai số yêu cầu",
        "UNBOUNDED": "Bài toán không giới nội",
        "INFEASIBLE": "Bài toán vô nghiệm",
        "MULTIPLE_OPTIMA": "Bài toán có vô số nghiệm tối ưu",
        "KARMARKAR_PRECONDITION_FAILED": "Không thể khởi tạo phép lặp Karmarkar",
        "MAX_ITERATIONS": "Đã hết số vòng lặp, chưa đạt sai số yêu cầu",
    }
    message = labels.get(report.status, report.status)
    if report.status == "APPROX_TOL_REACHED":
        st.success(message)
    else:
        st.warning(message)
    a, b = st.columns(2)
    a.metric("Giá trị hàm mục tiêu", "—" if report.objective is None else f"{report.objective:.10g}")
    b.metric("Số vòng Karmarkar", report.iterations)
    if report.x is not None:
        st.dataframe({"Biến": [f"x{i+1}" for i in range(len(report.x))], "Giá trị": report.x}, hide_index=True)
    st.download_button("Tải lời giải HTML", report.html, file_name="Loi_giai_Karmarkar.html", mime="text/html", key="download")
    components.html(report.html, height=850, scrolling=True)


def main():
    st.set_page_config(page_title="Karmarkar · Giải quy hoạch tuyến tính", page_icon="📐", layout="wide")
    st.title("Giải quy hoạch tuyến tính bằng Karmarkar")
    st.write("Nhập bài toán, xem từng bước giải và tải báo cáo HTML.")
    st.session_state.setdefault("report", None)
    with st.sidebar:
        st.header("Kích thước bài toán")
        n = st.number_input("Số biến", 1, 20, 2, key="n", on_change=dimensions_changed)
        m = st.number_input("Số ràng buộc", 0, 40, 1, key="m", on_change=dimensions_changed)
        st.caption("Đổi kích thước sẽ đặt lại hệ số và xóa kết quả trước.")
        with st.expander("Cài đặt thuật toán"):
            alpha = st.number_input("Alpha", 0.01, 0.99, 0.25, step=0.01, on_change=clear_report)
            max_iter = st.number_input("Số vòng tối đa", 1, 2000, 300, on_change=clear_report)
            tolerance = st.selectbox("Sai số mục tiêu", [1e-6, 1e-8, 1e-10], index=1, on_change=clear_report)
            compare = st.checkbox("Đối chứng bằng HiGHS", True, on_change=clear_report)
            details = st.checkbox("Hiện ma trận từng bước", True, on_change=clear_report)
        st.caption("HiGHS hỗ trợ phân loại và chuẩn hóa; các bước lặp Karmarkar do mã nguồn dự án tính toán.")
    submitted, values = input_form(n, m)
    if submitted:
        clear_report()
        try:
            problem = build_problem(*values)
            config = GeneralSolverConfig(alpha=alpha, max_iter=max_iter, objective_tolerance=tolerance)
            with st.spinner("Đang giải và tạo báo cáo…"):
                st.session_state["report"] = run_problem(problem, config, compare=compare, details=details)
        except ValueError as error:
            st.error(str(error))
        except Exception:
            logging.exception("Không thể hoàn tất lời giải Streamlit")
            st.error("Không thể hoàn tất lời giải. Hãy kiểm tra dữ liệu hoặc xem chi tiết lỗi trong terminal.")
    if st.session_state["report"] is not None:
        show_result(st.session_state["report"])


if __name__ == "__main__":
    main()
