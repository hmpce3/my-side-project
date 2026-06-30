import html

import streamlit as st


# ------------------------------------------------------------
# 보고서 결과 저장소 (session_state 기반)
# ------------------------------------------------------------
# 페이지가 runpy로 매번 재실행돼도 session_state는 유지되므로,
# 사용자가 여러 페이지에서 담은 항목이 안전하게 누적됩니다.
#
# 항목 구조:
#   {
#       "id": int,                              # 고유 번호
#       "kind": "chart" | "table" | "stat",     # 항목 종류
#       "title": str,                           # 항목 제목
#       "source": str,                          # 출처 페이지
#       "payload": <plotly fig | DataFrame | dict>,
#       "caption": str,                         # 보조 설명(선택)
#   }
#
# payload 규약:
#   - chart : plotly Figure
#   - table : pandas DataFrame
#   - stat  : {"table": DataFrame | None, "text": str}
# ------------------------------------------------------------

_STORE_KEY = "report_items"
_COUNTER_KEY = "report_counter"


def _ensure_store():
    if _STORE_KEY not in st.session_state:
        st.session_state[_STORE_KEY] = []
    if _COUNTER_KEY not in st.session_state:
        st.session_state[_COUNTER_KEY] = 0


def get_items():
    """보고서에 담긴 항목 리스트를 반환합니다."""
    _ensure_store()
    return st.session_state[_STORE_KEY]


def add_item(kind, title, source, payload, caption="", note=""):
    """보고서에 항목을 추가하고 부여된 id를 반환합니다.

    caption : 자동 생성 인사이트(시각화 요약 등)
    note    : 사용자가 직접 적는 코멘트(보고서 페이지에서 편집)
    """
    _ensure_store()
    st.session_state[_COUNTER_KEY] += 1
    item_id = st.session_state[_COUNTER_KEY]
    st.session_state[_STORE_KEY].append({
        "id": item_id,
        "kind": kind,
        "title": title,
        "source": source,
        "payload": payload,
        "caption": caption,
        "note": note,
    })
    return item_id


def remove_item(item_id):
    """id로 항목을 삭제합니다."""
    _ensure_store()
    st.session_state[_STORE_KEY] = [
        item for item in st.session_state[_STORE_KEY]
        if item["id"] != item_id
    ]


def move_item(item_id, direction):
    """항목 순서를 위(-1)/아래(+1)로 한 칸 이동합니다."""
    _ensure_store()
    items = st.session_state[_STORE_KEY]
    index = next((i for i, it in enumerate(items) if it["id"] == item_id), None)
    if index is None:
        return
    new_index = index + direction
    if 0 <= new_index < len(items):
        items[index], items[new_index] = items[new_index], items[index]


def clear_items():
    """담긴 항목을 모두 비웁니다."""
    _ensure_store()
    st.session_state[_STORE_KEY] = []


def count():
    """담긴 항목 개수를 반환합니다."""
    return len(get_items())


# ------------------------------------------------------------
# 각 페이지에서 쓰는 '리포트에 담기' 버튼
# ------------------------------------------------------------
# st.button은 클릭된 그 rerun에서만 True이므로 중복 추가가 발생하지 않습니다.
# key는 페이지 안에서 유일해야 합니다.
# ------------------------------------------------------------
def report_button(kind, title, source, payload, key, caption="", label="📌 리포트에 담기"):
    if st.button(label, key=key):
        add_item(kind, title, source, payload, caption=caption)
        st.toast(f"리포트에 담았습니다: {title}")
        return True
    return False


def chart_title(fig, default="그래프"):
    """plotly figure의 제목 텍스트를 추출합니다(없으면 default)."""
    try:
        text = fig.layout.title.text
        if text:
            return str(text)
    except Exception:
        pass
    return default


def _chart_for_report(fig):
    """HTML 보고서에서도 Plotly 그래프 색상이 유지되도록 기본 색을 보강합니다."""
    try:
        import plotly.graph_objects as go
        report_fig = go.Figure(fig)
    except Exception:
        return fig

    palette = [
        "#0068c9",
        "#83c9ff",
        "#ff7f0e",
        "#2ca02c",
        "#d62728",
        "#9467bd",
        "#8c564b",
        "#e377c2",
    ]

    for index, trace in enumerate(report_fig.data):
        color = palette[index % len(palette)]
        trace_type = getattr(trace, "type", "")

        if trace_type == "bar":
            marker = getattr(trace, "marker", None)
            current_color = getattr(marker, "color", None) if marker is not None else None
            if current_color is None:
                trace.update(marker=dict(color=color))

        elif trace_type in ("scatter", "scattergl"):
            mode = getattr(trace, "mode", "") or ""
            line = getattr(trace, "line", None)
            marker = getattr(trace, "marker", None)
            line_color = getattr(line, "color", None) if line is not None else None
            marker_color = getattr(marker, "color", None) if marker is not None else None

            if "lines" in mode and line_color is None:
                trace.update(line=dict(color=color, width=2.5))
            if "markers" in mode and marker_color is None:
                trace.update(marker=dict(color=color, size=6))

    report_fig.update_layout(
        template="plotly_white",
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, system-ui, sans-serif"),
    )
    return report_fig


# ------------------------------------------------------------
# HTML 보고서 생성
# ------------------------------------------------------------
_CSS = """<style>
  body { font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', system-ui, sans-serif;
         color: #222; background: #fff; margin: 0; }
  .wrap { max-width: 960px; margin: 0 auto; padding: 40px 24px 80px; }
  h1 { font-size: 28px; border-bottom: 3px solid #4c78a8; padding-bottom: 12px; }
  h2 { font-size: 20px; margin-top: 36px; color: #2c3e50; }
  .meta { color: #666; font-size: 14px; margin-top: 4px; }
  .overview { background: #f6f8fa; padding: 16px 20px; border-radius: 8px; line-height: 1.6; }
  .item { margin: 28px 0; padding-bottom: 16px; border-bottom: 1px solid #eee; }
  .item-title { border-left: 4px solid #4c78a8; padding-left: 10px; }
  .source { color: #8a8a8a; font-size: 12px; margin: 2px 0 14px; }
  .interpret { background: #eef6ff; padding: 14px 16px; border-radius: 8px; line-height: 1.7; }
  .caption { color: #666; font-size: 13px; }
  table { border-collapse: collapse; width: 100%; font-size: 13px; margin: 8px 0; }
  th, td { border: 1px solid #ddd; padding: 6px 10px; text-align: right; }
  th { background: #f0f4f8; }
  .insight { color: #1a5276; font-size: 14px; background: #f4f9ff;
             padding: 10px 14px; border-radius: 6px; margin-top: 10px; line-height: 1.6; }
  .note { background: #fff8e1; border-left: 4px solid #f0c040;
          padding: 12px 14px; border-radius: 6px; margin-top: 10px; line-height: 1.6; }
  .note-label { font-weight: 700; color: #8a6d1a; font-size: 13px; }
  .empty { color: #999; }
  .footer { margin-top: 48px; color: #aaa; font-size: 12px; text-align: center; }
</style>"""


def _nl2br(text):
    return html.escape(str(text)).replace("\n", "<br>")


def render_report_html(meta):
    """담긴 항목들로 자체 완결형 HTML 보고서 문자열을 생성합니다.

    meta 키: title, author, date, overview, data_summary_html
    """
    items = get_items()

    title = meta.get("title") or "데이터 분석 보고서"
    author = meta.get("author") or ""
    date = meta.get("date") or ""
    overview = meta.get("overview") or ""
    data_summary_html = meta.get("data_summary_html") or ""

    parts = [
        "<!DOCTYPE html>",
        "<html lang='ko'><head><meta charset='utf-8'>",
        f"<title>{html.escape(title)}</title>",
        _CSS,
        "</head><body><div class='wrap'>",
        f"<h1>{html.escape(title)}</h1>",
    ]

    meta_bits = []
    if author:
        meta_bits.append(f"작성자: {html.escape(author)}")
    if date:
        meta_bits.append(f"작성일: {html.escape(date)}")
    if meta_bits:
        parts.append(f"<p class='meta'>{' &nbsp;|&nbsp; '.join(meta_bits)}</p>")

    if overview:
        parts.append("<h2>분석 개요</h2>")
        parts.append(f"<div class='overview'>{_nl2br(overview)}</div>")

    if data_summary_html:
        parts.append("<h2>데이터 요약</h2>")
        parts.append(data_summary_html)

    if items:
        parts.append("<h2>분석 항목</h2>")

    first_chart = True
    for item in items:
        parts.append("<div class='item'>")
        parts.append(f"<h3 class='item-title'>{html.escape(str(item['title']))}</h3>")
        if item.get("source"):
            parts.append(f"<p class='source'>출처: {html.escape(str(item['source']))}</p>")

        kind = item["kind"]
        payload = item["payload"]

        if kind == "chart":
            include = "cdn" if first_chart else False
            chart_payload = _chart_for_report(payload)
            parts.append(chart_payload.to_html(full_html=False, include_plotlyjs=include))
            first_chart = False
        elif kind == "table":
            parts.append(payload.to_html(border=0, index=False))
        elif kind == "stat":
            table = payload.get("table")
            text = payload.get("text")
            if table is not None:
                parts.append(table.to_html(border=0, index=False))
            if text:
                parts.append(f"<div class='interpret'>{_nl2br(text)}</div>")

        if item.get("caption"):
            parts.append(f"<p class='insight'>💡 {html.escape(str(item['caption']))}</p>")
        if item.get("note"):
            parts.append(
                "<div class='note'><span class='note-label'>📝 코멘트</span><br>"
                f"{_nl2br(item['note'])}</div>"
            )
        parts.append("</div>")

    if not items:
        parts.append("<p class='empty'>담긴 분석 항목이 없습니다.</p>")

    parts.append("<p class='footer'>자동 데이터 분석 대시보드에서 생성된 보고서</p>")
    parts.append("</div></body></html>")
    return "\n".join(parts)
