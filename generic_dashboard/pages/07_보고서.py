import streamlit as st
import pandas as pd
from datetime import datetime

from helpers import my_report


st.title("보고서")

st.write(
    "분석 과정에서 여러 페이지에서 담은 그래프와 통계 결과를 한곳에 모아 "
    "하나의 HTML 보고서로 내보냅니다."
)

items = my_report.get_items()


# ------------------------------------------------------------
# 1. 보고서 기본 정보
# ------------------------------------------------------------
st.subheader("보고서 정보")

info_col1, info_col2 = st.columns(2)

with info_col1:
    report_title = st.text_input("보고서 제목", value="데이터 분석 보고서")

with info_col2:
    report_author = st.text_input("작성자", value="")

report_overview = st.text_area(
    "분석 개요 (선택)",
    placeholder="이 분석의 목적과 핵심 내용을 간단히 적어주세요.",
)

report_date = datetime.now().strftime("%Y-%m-%d")
st.caption(f"작성일: {report_date}")


# ------------------------------------------------------------
# 2. 데이터 요약 (자동)
# ------------------------------------------------------------
st.subheader("데이터 요약")

data_summary_html = ""

if "data" in st.session_state:
    if "cleaned_data" in st.session_state:
        base_data = st.session_state["cleaned_data"]
        using_label = "정제 데이터"
    else:
        base_data = st.session_state["data"]
        using_label = "원본 데이터"

    rows, cols = base_data.shape
    missing = int(base_data.isnull().sum().sum())

    summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)
    summary_col1.metric("사용 데이터", using_label)
    summary_col2.metric("행 개수", f"{rows:,}")
    summary_col3.metric("열 개수", f"{cols:,}")
    summary_col4.metric("전체 결측치", f"{missing:,}")

    summary_df = pd.DataFrame({
        "항목": ["사용 데이터", "행 개수", "열 개수", "전체 결측치"],
        "값": [using_label, f"{rows:,}", f"{cols:,}", f"{missing:,}"],
    })
    data_summary_html = summary_df.to_html(border=0, index=False)
else:
    st.info(
        "아직 업로드된 데이터가 없습니다. 데이터 요약 없이 담은 항목만 보고서에 포함됩니다."
    )


# ------------------------------------------------------------
# 3. 담은 분석 항목
# ------------------------------------------------------------
st.subheader(f"담은 분석 항목 ({len(items)}개)")

if not items:
    st.info(
        "아직 담은 항목이 없습니다. 시각화 / 통계 분석 페이지에서 "
        "'📌 리포트에 담기' 버튼을 눌러 추가하세요."
    )
else:
    if st.button("전체 비우기"):
        my_report.clear_items()
        st.rerun()

    for index, item in enumerate(items):
        with st.expander(
            f"{index + 1}. [{item['source']}] {item['title']}",
            expanded=False,
        ):
            kind = item["kind"]

            # 미리보기 (항목 하나가 깨져도 보고서 전체가 멈추지 않도록 방어)
            try:
                if kind == "chart":
                    st.plotly_chart(
                        item["payload"],
                        use_container_width=True,
                        key=f"preview_{item['id']}",
                    )
                elif kind == "table":
                    st.dataframe(item["payload"], use_container_width=True)
                elif kind == "stat":
                    table = item["payload"].get("table")
                    text = item["payload"].get("text")
                    if table is not None:
                        st.dataframe(table, use_container_width=True)
                    if text:
                        st.info(text)
            except Exception as error:
                st.error(f"이 항목을 표시할 수 없습니다: {error}")

            if item.get("caption"):
                st.markdown(f"💡 **자동 인사이트**: {item['caption']}")

            # 사용자가 직접 적는 코멘트 (보고서에 함께 출력됩니다)
            item["note"] = st.text_area(
                "📝 내 코멘트 / 결과",
                value=item.get("note", ""),
                key=f"note_{item['id']}",
                placeholder="이 분석에 대한 해석이나 결론을 적어주세요. 보고서에 함께 출력됩니다.",
            )

            # 순서 이동 / 삭제 컨트롤
            ctrl_up, ctrl_down, ctrl_del, _ = st.columns([1, 1, 1, 5])

            with ctrl_up:
                if st.button("⬆️", key=f"up_{item['id']}", disabled=(index == 0)):
                    my_report.move_item(item["id"], -1)
                    st.rerun()

            with ctrl_down:
                if st.button(
                    "⬇️",
                    key=f"down_{item['id']}",
                    disabled=(index == len(items) - 1),
                ):
                    my_report.move_item(item["id"], 1)
                    st.rerun()

            with ctrl_del:
                if st.button("🗑️", key=f"del_{item['id']}"):
                    my_report.remove_item(item["id"])
                    st.rerun()


# ------------------------------------------------------------
# 4. HTML 보고서 내보내기
# ------------------------------------------------------------
st.subheader("보고서 내보내기")

if not items:
    st.caption("담은 항목이 있어야 보고서를 생성할 수 있습니다.")
else:
    meta = {
        "title": report_title,
        "author": report_author,
        "date": report_date,
        "overview": report_overview,
        "data_summary_html": data_summary_html,
    }

    html_report = my_report.render_report_html(meta)

    st.download_button(
        label="📥 HTML 보고서 다운로드",
        data=html_report.encode("utf-8"),
        file_name=f"report_{report_date}.html",
        mime="text/html",
        type="primary",
    )

    st.caption(
        "다운로드한 HTML 파일을 더블클릭하면 브라우저에서 열리며, "
        "그래프는 확대·마우스오버 등 인터랙티브 기능이 그대로 유지됩니다."
    )
