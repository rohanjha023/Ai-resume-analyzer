"""Streamlit frontend for the AI Resume Analyzer."""
import html
import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import api_client as api

st.set_page_config(
    page_title="AI Resume Analyzer",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
#MainMenu, footer {visibility: hidden;}
.block-container {padding-top: 2rem; max-width: 1200px;}
.hero {background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 55%, #db2777 100%);
  padding: 2.2rem 2.4rem; border-radius: 20px; color: #fff; margin-bottom: 1.6rem;
  box-shadow: 0 10px 30px rgba(79,70,229,.25);}
.hero h1 {margin: 0; font-size: 2.1rem; font-weight: 800; color: #fff; padding: 0;}
.hero p {margin: .5rem 0 0; font-size: 1.05rem; opacity: .92; color: #fff;}
.card {background: #fff; border: 1px solid #e2e8f0; border-radius: 16px; padding: 1.1rem 1.3rem;
  margin-bottom: 1rem; box-shadow: 0 1px 3px rgba(15,23,42,.06);}
.card h4 {margin: 0 0 .7rem; font-size: 1rem; font-weight: 700; color: #0f172a;}
.card p, .card li {color: #334155; font-size: .95rem; line-height: 1.55;}
.card ul, .card ol {margin: 0; padding-left: 1.2rem;}
.chip {display: inline-block; padding: .28rem .75rem; margin: .18rem .3rem .18rem 0;
  border-radius: 999px; font-size: .82rem; font-weight: 600;}
.chip-ok {background: #dcfce7; color: #166534;}
.chip-miss {background: #fee2e2; color: #991b1b;}
.chip-kw {background: #e0e7ff; color: #3730a3;}
.verdict {display: inline-block; padding: .4rem 1.1rem; border-radius: 999px; color: #fff;
  font-weight: 700; font-size: .95rem;}
.muted {color: #94a3b8; font-size: .9rem;}
div[data-testid="stTabs"] button {font-weight: 600;}
</style>
""",
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------------------- helpers
def esc(value) -> str:
    return html.escape(str(value))


def score_color(score: int) -> str:
    return "#16a34a" if score >= 75 else "#f59e0b" if score >= 50 else "#dc2626"


def chips(items: list[str], css: str) -> str:
    if not items:
        return "<span class='muted'>Nothing identified</span>"
    return "".join(f"<span class='chip {css}'>{esc(i)}</span>" for i in items)


def listing(items: list[str], tag: str = "ul") -> str:
    if not items:
        return "<span class='muted'>Nothing identified</span>"
    return f"<{tag}>" + "".join(f"<li>{esc(i)}</li>" for i in items) + f"</{tag}>"


def card(title: str, body: str) -> None:
    st.markdown(f"<div class='card'><h4>{title}</h4>{body}</div>", unsafe_allow_html=True)


def gauge(score: int) -> go.Figure:
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"suffix": "%", "font": {"size": 46, "color": score_color(score)}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#94a3b8"},
                "bar": {"color": score_color(score), "thickness": 0.28},
                "bgcolor": "#f1f5f9",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 50], "color": "#fee2e2"},
                    {"range": [50, 75], "color": "#fef3c7"},
                    {"range": [75, 100], "color": "#dcfce7"},
                ],
            },
        )
    )
    fig.update_layout(height=250, margin=dict(l=25, r=25, t=25, b=0), paper_bgcolor="rgba(0,0,0,0)")
    return fig


def section_chart(scores: dict) -> go.Figure:
    labels = ["Skills", "Experience", "Education", "Keywords"]
    values = [scores.get(k, 0) for k in ("skills", "experience", "education", "keywords")]
    fig = go.Figure(
        go.Bar(
            x=values[::-1],
            y=labels[::-1],
            orientation="h",
            marker_color=[score_color(v) for v in values[::-1]],
            text=[f"{v}%" for v in values[::-1]],
            textposition="outside",
            cliponaxis=False,
        )
    )
    fig.update_layout(
        height=210,
        margin=dict(l=0, r=40, t=5, b=0),
        xaxis=dict(range=[0, 100], visible=False),
        yaxis=dict(tickfont=dict(size=13)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def build_report(data: dict) -> str:
    r = data["result"]

    def section(title, items):
        return f"\n## {title}\n" + ("\n".join(f"- {i}" for i in items) or "- None") + "\n"

    return (
        f"# Resume Analysis Report\n\n"
        f"- **File:** {data['filename']}\n"
        f"- **Target role:** {data['job_title'] or 'N/A'}\n"
        f"- **Match score:** {r['match_score']}/100 ({r['verdict']})\n\n"
        f"## Summary\n{r['summary']}\n"
        + section("Matched skills", r["matched_skills"])
        + section("Missing skills", r["missing_skills"])
        + section("Strengths", r["strengths"])
        + section("Weaknesses", r["weaknesses"])
        + section("Suggestions", r["suggestions"])
        + section("ATS keywords to add", r["ats_keywords"])
    )


def render_result(data: dict, prefix: str) -> None:
    r = data["result"]
    score = r["match_score"]

    left, right = st.columns([1, 1.6], gap="large")
    with left:
        st.plotly_chart(gauge(score), key=f"{prefix}-gauge", config={"displayModeBar": False})
        st.markdown(
            f"<div style='text-align:center'><span class='verdict' style='background:{score_color(score)}'>"
            f"{esc(r['verdict'] or 'Analysis complete')}</span></div>",
            unsafe_allow_html=True,
        )
    with right:
        card("Summary", f"<p>{esc(r['summary'])}</p>")
        st.plotly_chart(
            section_chart(r["section_scores"]), key=f"{prefix}-sections", config={"displayModeBar": False}
        )

    st.write("")
    a, b = st.columns(2, gap="medium")
    with a:
        card(" Matched skills", chips(r["matched_skills"], "chip-ok"))
    with b:
        card("⚠️ Missing skills", chips(r["missing_skills"], "chip-miss"))

    c, d = st.columns(2, gap="medium")
    with c:
        card(" Strengths", listing(r["strengths"]))
    with d:
        card(" Weaknesses", listing(r["weaknesses"]))

    e, f = st.columns([1.4, 1], gap="medium")
    with e:
        card("💡 Suggestions to improve", listing(r["suggestions"], "ol"))
    with f:
        card(" ATS keywords to add", chips(r["ats_keywords"], "chip-kw"))

    d1, d2, _ = st.columns([1, 1, 3])
    d1.download_button(
        "⬇ Report (.md)", build_report(data), f"resume-analysis-{data['id']}.md", key=f"{prefix}-md"
    )
    d2.download_button(
        "⬇ Data (.json)",
        json.dumps(data, indent=2),
        f"resume-analysis-{data['id']}.json",
        key=f"{prefix}-json",
    )


# ----------------------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown("### 📄 Resume Analyzer")
    status = api.health()
    if status is None:
        st.error("API unreachable")
        st.caption(f"Expected at `{api.API_URL}`")
    else:
        st.success("API online")
        if not status.get("llm_configured"):
            st.warning("The server has no Gemini API key configured.")
    st.markdown("---")
    st.markdown("**Tips for better results**")
    st.caption(
        "• Paste the complete job description\n\n"
        "• Use a text-based PDF or DOCX, not a scan\n\n"
        "• Mirror the job's keywords honestly in your resume\n\n"
        "• Re-run after every edit and compare scores in History"
    )

# ----------------------------------------------------------------------------- header
st.markdown(
    "<div class='hero'><h1>AI Resume Analyzer</h1>"
    "<p>Upload your resume, paste a job description, and get an instant match score, "
    "skill-gap analysis and ATS-ready suggestions.</p></div>",
    unsafe_allow_html=True,
)

tab_analyze, tab_history, tab_about = st.tabs(["🔍 Analyze", "🕘 History", "ℹ️ About"])

# ----------------------------------------------------------------------------- analyze
with tab_analyze:
    col1, col2 = st.columns([1, 1.4], gap="large")
    with col1:
        st.markdown("##### 1 · Upload your resume")
        resume = st.file_uploader(
            "Resume", type=["pdf", "docx", "txt"], label_visibility="collapsed", help="PDF, DOCX or TXT · max 5 MB"
        )
        job_title = st.text_input("Target role (optional)", placeholder="e.g. AI Engineer")
    with col2:
        st.markdown("##### 2 · Paste the job description")
        jd = st.text_area(
            "Job description",
            height=225,
            label_visibility="collapsed",
            placeholder="Paste the responsibilities and requirements here...",
        )

    run = st.button("Analyze match", type="primary", width="stretch")

    if run:
        if resume is None:
            st.warning("Please upload your resume first.")
        elif len(jd.strip()) < 50:
            st.warning("Please paste a complete job description (at least 50 characters).")
        else:
            with st.spinner("Analyzing your resume. This usually takes 10-20 seconds..."):
                try:
                    st.session_state["current"] = api.analyze(resume.name, resume.getvalue(), jd, job_title)
                except api.ApiError as exc:
                    st.session_state.pop("current", None)
                    st.error(str(exc))

    if "current" in st.session_state:
        st.divider()
        render_result(st.session_state["current"], "current")

# ----------------------------------------------------------------------------- history
with tab_history:
    try:
        items = api.history()
    except api.ApiError as exc:
        st.error(str(exc))
        items = []

    if not items:
        st.info("No analyses yet. Run your first analysis in the Analyze tab.")
    else:
        df = pd.DataFrame(items)
        df["created_at"] = df["created_at"].str[:16].str.replace("T", " ") + " UTC"
        df = df.rename(
            columns={
                "id": "ID",
                "created_at": "Date",
                "filename": "Resume",
                "job_title": "Role",
                "match_score": "Match",
            }
        )[["ID", "Date", "Resume", "Role", "Match"]]
        st.dataframe(
            df,
            width="stretch",
            hide_index=True,
            column_config={"Match": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d%%")},
        )

        labels = {i["id"]: f"#{i['id']} · {i['filename']} · {i['match_score']}%" for i in items}
        selected = st.selectbox("Open an analysis", options=list(labels), format_func=labels.get)
        if st.button("🗑 Delete this analysis", key="delete-btn"):
            try:
                api.delete_analysis(selected)
                st.session_state.pop("current", None)
                st.rerun()
            except api.ApiError as exc:
                st.error(str(exc))
        try:
            st.divider()
            render_result(api.get_analysis(selected), f"history-{selected}")
        except api.ApiError as exc:
            st.error(str(exc))

# ----------------------------------------------------------------------------- about
with tab_about:
    st.markdown(
        """
### How it works
1. Your resume is converted to plain text (PDF, DOCX and TXT are supported).
2. The text and the job description are sent to Google Gemini with a structured evaluation prompt.
3. The response is validated, scored and stored in the database so you can track improvements over time.

### Scoring guide
| Score | Meaning |
|---|---|
| 90 - 100 | Exceptional match |
| 70 - 89 | Strong match |
| 50 - 69 | Partial match, close the listed gaps |
| Below 50 | Weak match for this role |

### Stack
FastAPI · Streamlit · Google Gemini · SQLAlchemy (MySQL / PostgreSQL / SQLite) · Docker

### Privacy
Resume text is sent to the Gemini API for analysis. Only the analysis result is stored, never the uploaded file.
"""
    )
