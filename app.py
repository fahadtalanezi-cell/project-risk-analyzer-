import hashlib
import os

import pandas as pd
import streamlit as st

try:
    from openai import OpenAI
except ModuleNotFoundError:
    OpenAI = None

from ai.openai_service import (
    analyze_project,
    answer_question,
    default_ai_json,
    extract_evm_source_data_with_ai,
    markdown_from_ai_json,
)
from charts.figures import (
    budget_waterfall,
    category_bar,
    critical_task_ranking,
    evm_forecast_chart,
    evm_indices_chart,
    evm_value_chart,
    evm_variance_chart,
    finish_forecast_chart,
    forecast_chart,
    float_analysis_chart,
    milestone_slippage_chart,
    milestone_tracking,
    resource_donut,
    resource_load_chart,
    risk_gauge,
    risk_heatmap,
    risk_radar,
    s_curve_chart,
    spi_cpi_trend,
    timeline_chart,
)
from components.ui import floating_assistant, hero, inject_css, insight_card, kpi_cards, soft_panel
from localization.strings import LANGUAGES, TRANSLATIONS, direction, t
from reports.pdf_report import build_pdf
from services.evm_engine import (
    calculate_evm_metrics,
    evm_to_ai_context,
    extract_evm_source_data,
    format_currency,
    format_index,
    format_percent,
    merge_source_data,
)
from services.forecasting import build_forecast, performance_indicators
from services.risk_engine import (
    build_heatmap_data,
    build_risk_table,
    build_timeline,
    calculate_risk,
    estimate_ai_confidence,
    project_status,
)
from services.schedule_engine import analyze_schedule_control, schedule_to_ai_context
from utils.file_processing import SUPPORTED_TYPES, extract_file_text


APP_NAME = "Project Risk Analyzer"
DEMO_TEXT = """
The project portfolio includes moderate schedule pressure, procurement coordination needs,
resource allocation constraints, controlled scope exposure, and budget variance monitoring.
Key milestones are concentrated around procurement, systems integration, testing, and executive handover.
For the demonstration EVM scenario, the project budget is 1,000,000 SAR, actual cost incurred
is 450,000 SAR, planned progress is 50 percent, and actual progress is 40 percent.
"""


# =====================================================
# APPLICATION CONFIGURATION
# =====================================================
st.set_page_config(page_title=APP_NAME, layout="wide", initial_sidebar_state="expanded")


def get_openai_api_key():
    """Load the API key from Streamlit Secrets in production, with env fallback for local runs."""
    try:
        return st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    except Exception:
        return os.getenv("OPENAI_API_KEY")


api_key = get_openai_api_key()
client = OpenAI(api_key=api_key) if api_key and OpenAI else None

if "analysis_cache" not in st.session_state:
    st.session_state.analysis_cache = {}
if "evm_cache" not in st.session_state:
    st.session_state.evm_cache = {}
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "uploaded_project_file" not in st.session_state:
    st.session_state.uploaded_project_file = None


# =====================================================
# SIDEBAR ENTERPRISE CONTROL PANEL
# =====================================================
language = st.sidebar.selectbox(
    "Language / اللغة",
    LANGUAGES,
    index=LANGUAGES.index(st.session_state.get("language", "English")),
    key="language",
)
labels = TRANSLATIONS[language]
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True
dark_mode = st.session_state.dark_mode
inject_css(dark_mode, direction(language))

st.sidebar.markdown(f"### {APP_NAME}")
st.sidebar.caption(t(language, "brand_caption"))
st.sidebar.divider()

if language == "العربية":
    defaults = {
        "duration": ["اختر أفق التسليم", "0-6 أشهر", "6-12 شهر", "1-2 سنة", "2-5 سنوات"],
        "budget": ["اختر فئة الاستثمار", "أقل من 500 ألف ريال", "500 ألف - 1 مليون", "1 مليون - 5 مليون", "أكثر من 5 مليون"],
        "team": ["اختر حجم الفريق", "1-10", "10-50", "50-100", "100+"],
        "level": ["اختر مستوى التحكم", "منخفض", "متوسط", "مرتفع"],
    }
else:
    defaults = {
        "duration": ["Select delivery horizon", "0-6 Months", "6-12 Months", "1-2 Years", "2-5 Years"],
        "budget": ["Select investment tier", "< 500K SAR", "500K - 1M SAR", "1M - 5M SAR", "> 5M SAR"],
        "team": ["Select delivery team scale", "1-10", "10-50", "50-100", "100+"],
        "level": ["Select control level", "Low", "Medium", "High"],
    }

with st.sidebar.expander(t(language, "project_information"), expanded=False):
    duration = st.selectbox(t(language, "duration"), defaults["duration"])
    budget = st.selectbox(t(language, "budget"), defaults["budget"])
    team_size = st.selectbox(t(language, "team_size"), defaults["team"])

with st.sidebar.expander(t(language, "risk_parameters"), expanded=False):
    complexity = st.selectbox(t(language, "complexity"), defaults["level"], index=2)
    stakeholder_engagement = st.selectbox(t(language, "stakeholder_engagement"), defaults["level"], index=2)
    schedule_pressure = st.selectbox(t(language, "schedule_pressure"), defaults["level"], index=2)
    scope_clarity = st.selectbox(t(language, "scope_clarity"), defaults["level"], index=2)

with st.sidebar.expander(t(language, "resource_settings"), expanded=False):
    resource_availability = st.selectbox(t(language, "resource_availability"), defaults["level"], index=2)

with st.sidebar.expander(t(language, "forecast_controls"), expanded=False):
    forecast_horizon = st.slider("Forecast horizon" if language == "English" else "أفق التنبؤ", 4, 12, 8)
    confidence_bias = st.slider("Executive confidence adjustment" if language == "English" else "تعديل الثقة التنفيذية", -10, 10, 0)

project_inputs = {
    "duration": duration,
    "budget": budget,
    "team_size": team_size,
    "complexity": complexity,
    "stakeholder_engagement": stakeholder_engagement,
    "schedule_pressure": schedule_pressure,
    "resource_availability": resource_availability,
    "scope_clarity": scope_clarity,
}
selected_values = list(project_inputs.values())


# =====================================================
# HERO AND INTELLIGENCE INTAKE
# =====================================================
hero(t(language, "app_title"), t(language, "app_subtitle"))

intake_col, signal_col = st.columns([1.45, .95])
with intake_col:
    st.markdown(f"### {t(language, 'upload_title')}")
    uploaded_file = st.file_uploader(
        t(language, "upload_help"),
        type=SUPPORTED_TYPES,
        accept_multiple_files=False,
    )

if uploaded_file is not None:
    st.session_state.uploaded_project_file = {
        "name": uploaded_file.name,
        "bytes": uploaded_file.getvalue(),
    }

active_file = st.session_state.uploaded_project_file

with signal_col:
    if active_file is None:
        st.markdown(
            f"<div class='empty-state'><h4>{t(language, 'empty_title')}</h4><p>{t(language, 'empty_body')}</p></div>",
            unsafe_allow_html=True,
        )
    else:
        st.caption(f"{t(language, 'uploaded')}: {active_file['name']}")
        if st.button(t(language, "clear_file")):
            st.session_state.uploaded_project_file = None
            st.rerun()


# =====================================================
# FILE OR DEMO DATA PROCESSING
# =====================================================
if active_file:
    file_bytes = active_file["bytes"]
    file_hash = hashlib.sha256(file_bytes + language.encode("utf-8") + str(project_inputs).encode("utf-8")).hexdigest()
    with st.status(t(language, "processing"), expanded=False) as status:
        processed_file = extract_file_text(active_file["name"], file_bytes)
        extracted_text = processed_file["text"]
        st.write(f"{t(language, 'uploaded')}: {processed_file['name']} ({processed_file['size_kb']} KB)")
        is_demo = False
else:
    file_hash = hashlib.sha256((DEMO_TEXT + language + str(project_inputs)).encode("utf-8")).hexdigest()
    processed_file = {"name": "Synthetic PMO Portfolio Scenario", "preview_df": None, "size_kb": 0}
    extracted_text = DEMO_TEXT
    is_demo = True

risk_score, category_scores, risk_signals = calculate_risk(project_inputs, extracted_text)
evm_source_data = extract_evm_source_data(extracted_text, processed_file.get("preview_df"))
missing_evm_sources = [
    field
    for field, item in evm_source_data.items()
    if item.get("value") is None
]
evm_cache_key = hashlib.sha256((file_hash + "evm").encode("utf-8")).hexdigest()
if missing_evm_sources and client and not is_demo:
    if evm_cache_key not in st.session_state.evm_cache:
        try:
            st.session_state.evm_cache[evm_cache_key] = extract_evm_source_data_with_ai(client, language, extracted_text)
        except Exception:
            st.session_state.evm_cache[evm_cache_key] = {}
    evm_source_data = merge_source_data(evm_source_data, st.session_state.evm_cache[evm_cache_key])
evm_metrics = calculate_evm_metrics(evm_source_data)
evm_ai_context = evm_to_ai_context(evm_metrics)
schedule_metrics = analyze_schedule_control(extracted_text, processed_file.get("preview_df"), evm_metrics)
schedule_ai_context = schedule_to_ai_context(schedule_metrics)
risk_df = build_risk_table(category_scores, language)
heatmap_df = build_heatmap_data(category_scores, language)
timeline_df = build_timeline(category_scores, language)
forecast_df = build_forecast(risk_score, category_scores).head(forecast_horizon)
perf = performance_indicators(risk_score, category_scores)
ai_confidence = max(50, min(99, estimate_ai_confidence(extracted_text, selected_values) + confidence_bias))

metrics = {
    "risk_score": risk_score,
    "health_score": max(100 - risk_score, 0),
    "budget_health": perf["budget_health"],
    "schedule_health": perf["schedule_health"],
    "critical_tasks": perf["critical_tasks"],
    "predicted_delay": perf["predicted_delay"],
    "budget_variance": perf["budget_variance"],
    "spi": perf["spi"],
    "cpi": perf["cpi"],
    "ai_confidence": ai_confidence,
    "project_status": project_status(risk_score, labels),
}

if file_hash not in st.session_state.analysis_cache:
    if client and not is_demo:
        try:
            ai_json = analyze_project(client, language, project_inputs, extracted_text, risk_signals, metrics, evm_ai_context, schedule_ai_context)
        except Exception as exc:
            st.warning(f"AI analysis service error: {exc}")
            ai_json = default_ai_json(language)
    else:
        ai_json = default_ai_json(language)
    st.session_state.analysis_cache[file_hash] = ai_json

ai_json = st.session_state.analysis_cache[file_hash]
if uploaded_file:
    status.update(state="complete", label="Analysis ready" if language == "English" else "التحليل جاهز")

if st.sidebar.button(t(language, "refresh_ai"), disabled=client is None or is_demo, width="stretch"):
    with st.spinner(t(language, "processing")):
        st.session_state.analysis_cache[file_hash] = analyze_project(client, language, project_inputs, extracted_text, risk_signals, metrics, evm_ai_context, schedule_ai_context)
        st.rerun()

st.sidebar.markdown("<div class='sidebar-bottom-control'>", unsafe_allow_html=True)
st.sidebar.toggle(t(language, "theme"), key="dark_mode")
st.sidebar.markdown("</div>", unsafe_allow_html=True)


# =====================================================
# STICKY EXECUTIVE KPI CARDS
# =====================================================
kpi_cards([
    {"label": t(language, "overall_risk"), "value": f"{metrics['risk_score']}/100", "note": f"{metrics['project_status']}  •  trend +3%"},
    {"label": t(language, "budget_health"), "value": f"{metrics['budget_health']}%", "note": f"{t(language, 'cpi')}: {metrics['cpi']}  ↗"},
    {"label": t(language, "schedule_health"), "value": f"{metrics['schedule_health']}%", "note": f"{t(language, 'spi')}: {metrics['spi']}  ↘"},
    {"label": t(language, "predicted_delay"), "value": f"{metrics['predicted_delay']}d", "note": f"{metrics['budget_variance']}% {t(language, 'budget_variance')}"},
    {"label": t(language, "critical_tasks"), "value": metrics["critical_tasks"], "note": "Critical path ranked" if language == "English" else "ترتيب المسار الحرج"},
    {"label": t(language, "ai_confidence"), "value": f"{metrics['ai_confidence']}%", "note": "Evidence weighted" if language == "English" else "مرجح بالأدلة"},
])


# =====================================================
# ENTERPRISE TABBED COCKPIT
# =====================================================
tabs = st.tabs([
    t(language, "executive_overview"),
    t(language, "risk_analysis"),
    t(language, "forecasting"),
    t(language, "schedule_control"),
    t(language, "evm"),
    t(language, "resource_analytics"),
    t(language, "ai_insights"),
    t(language, "reports"),
])

with tabs[0]:
    top_left, top_mid, top_right = st.columns([.8, 1.15, 1.05])
    with top_left:
        st.plotly_chart(risk_gauge(metrics["risk_score"], t(language, "overall_risk"), dark_mode), width="stretch", key="overview_risk_gauge")
    with top_mid:
        st.plotly_chart(category_bar(risk_df, t(language, "risk_breakdown"), dark_mode), width="stretch", key="overview_category_bar")
    with top_right:
        st.plotly_chart(resource_donut(timeline_df, t(language, "resource_load"), dark_mode), width="stretch", key="overview_resource_donut")

    low_left, low_right = st.columns([1.2, 1])
    with low_left:
        st.plotly_chart(spi_cpi_trend(forecast_df, "SPI/CPI Trend", dark_mode), width="stretch", key="overview_spi_cpi")
    with low_right:
        st.plotly_chart(milestone_tracking(timeline_df, t(language, "milestones"), dark_mode), width="stretch", key="overview_milestones")

with tabs[1]:
    filter_threshold = st.slider("Severity filter" if language == "English" else "مرشح شدة المخاطر", 0, 100, 0)
    filtered_heatmap = heatmap_df[heatmap_df["score"] >= filter_threshold]
    st.plotly_chart(risk_heatmap(filtered_heatmap, t(language, "risk_heatmap"), labels, dark_mode), width="stretch", key="risk_heatmap")
    left, right = st.columns([1, 1])
    with left:
        st.plotly_chart(risk_radar(risk_df, t(language, "risk_radar"), dark_mode), width="stretch", key="risk_radar")
    with right:
        st.plotly_chart(critical_task_ranking(timeline_df, t(language, "critical_ranking"), dark_mode), width="stretch", key="critical_ranking")

with tabs[2]:
    c1, c2, c3 = st.columns(3)
    c1.metric(t(language, "spi"), metrics["spi"])
    c2.metric(t(language, "cpi"), metrics["cpi"])
    c3.metric(t(language, "budget_variance"), f"{metrics['budget_variance']}%")
    left, right = st.columns([1.15, .85])
    with left:
        st.plotly_chart(forecast_chart(forecast_df, t(language, "forecast"), dark_mode), width="stretch", key="forecast_chart")
    with right:
        st.plotly_chart(budget_waterfall(metrics, t(language, "budget_waterfall"), dark_mode), width="stretch", key="budget_waterfall")
    st.plotly_chart(timeline_chart(timeline_df, t(language, "timeline"), dark_mode), width="stretch", key="timeline_chart")

with tabs[3]:
    schedule_forecast = schedule_metrics["forecast"]
    status_cols = st.columns(4)
    status_cols[0].metric(t(language, "schedule_traffic"), schedule_metrics["traffic_light"].upper())
    status_cols[1].metric(t(language, "baseline_finish"), str(schedule_forecast.get("baseline_finish") or t(language, "not_enough_schedule_data"))[:10])
    status_cols[2].metric(t(language, "forecast_finish"), str(schedule_forecast.get("forecast_finish") or t(language, "not_enough_schedule_data"))[:10])
    status_cols[3].metric(t(language, "forecast_delay_days"), schedule_forecast.get("forecast_delay_days") if schedule_forecast.get("forecast_delay_days") is not None else t(language, "not_enough_schedule_data"))

    schedule_left, schedule_right = st.columns([1.15, .85])
    with schedule_left:
        st.plotly_chart(s_curve_chart(schedule_metrics["s_curve"], t(language, "s_curve"), dark_mode), width="stretch", key="schedule_s_curve")
    with schedule_right:
        st.plotly_chart(finish_forecast_chart(schedule_metrics, t(language, "schedule_forecast"), dark_mode), width="stretch", key="schedule_finish_forecast")

    float_left, float_right = st.columns([1, 1])
    with float_left:
        st.plotly_chart(float_analysis_chart(schedule_metrics["float_table"], t(language, "float_analysis"), dark_mode), width="stretch", key="schedule_float_analysis")
    with float_right:
        st.plotly_chart(milestone_slippage_chart(schedule_metrics["milestones"], t(language, "milestone_slippage"), dark_mode), width="stretch", key="schedule_milestone_slippage")

    cp_cols = st.columns([1.05, .95])
    with cp_cols[0]:
        st.markdown(f"### {t(language, 'critical_path')}")
        if schedule_metrics["critical_path"]:
            for activity in schedule_metrics["critical_path"]:
                st.write(f"- {activity}")
        else:
            st.info(t(language, "not_enough_schedule_data"))
    with cp_cols[1]:
        st.markdown(f"### {t(language, 'schedule_assumptions')}")
        if schedule_metrics["missing_data"]:
            st.warning(f"{t(language, 'not_enough_schedule_data')}: {', '.join(schedule_metrics['missing_data'])}")
        for item in schedule_metrics["assumptions"]:
            st.write(f"- {item}")

    with st.expander(t(language, "float_analysis"), expanded=not schedule_metrics["float_table"].empty):
        if schedule_metrics["float_table"].empty:
            st.info(t(language, "not_enough_schedule_data"))
        else:
            st.dataframe(schedule_metrics["float_table"], width="stretch", hide_index=True)
    with st.expander(t(language, "milestone_slippage"), expanded=not schedule_metrics["milestones"].empty):
        if schedule_metrics["milestones"].empty:
            st.info(t(language, "not_enough_schedule_data"))
        else:
            st.dataframe(schedule_metrics["milestones"], width="stretch", hide_index=True)

with tabs[4]:
    evm_values = evm_metrics["values"]
    kpi_cards([
        {"label": "BAC", "value": format_currency(evm_values.get("bac")), "note": t(language, "bac")},
        {"label": "PV", "value": format_currency(evm_values.get("pv")), "note": t(language, "pv")},
        {"label": "EV", "value": format_currency(evm_values.get("ev")), "note": t(language, "ev")},
        {"label": "AC", "value": format_currency(evm_values.get("ac")), "note": t(language, "ac")},
        {"label": "SV", "value": format_currency(evm_values.get("sv")), "note": evm_metrics["interpretation"]["schedule"]},
        {"label": "CV", "value": format_currency(evm_values.get("cv")), "note": evm_metrics["interpretation"]["cost"]},
        {"label": "SPI", "value": format_index(evm_values.get("spi")), "note": evm_metrics["traffic_lights"]["schedule"].upper()},
        {"label": "CPI", "value": format_index(evm_values.get("cpi")), "note": evm_metrics["traffic_lights"]["cost"].upper()},
        {"label": "EAC", "value": format_currency(evm_values.get("eac")), "note": t(language, "eac")},
        {"label": "ETC", "value": format_currency(evm_values.get("etc")), "note": t(language, "etc")},
        {"label": "VAC", "value": format_currency(evm_values.get("vac")), "note": evm_metrics["interpretation"]["forecast"]},
        {"label": "TCPI", "value": format_index(evm_values.get("tcpi")), "note": evm_metrics["interpretation"]["tcpi"]},
    ])

    status_cols = st.columns(4)
    status_cols[0].metric(t(language, "percent_complete"), format_percent(evm_values.get("percent_complete")))
    status_cols[1].metric(t(language, "spi"), format_index(evm_values.get("spi")))
    status_cols[2].metric(t(language, "cpi"), format_index(evm_values.get("cpi")))
    status_cols[3].metric(t(language, "tcpi"), format_index(evm_values.get("tcpi")))

    evm_top_left, evm_top_right = st.columns([1, 1])
    with evm_top_left:
        st.plotly_chart(evm_value_chart(evm_metrics, t(language, "evm_values"), dark_mode), width="stretch", key="evm_value_chart")
    with evm_top_right:
        st.plotly_chart(evm_indices_chart(evm_metrics, t(language, "evm_indices"), dark_mode), width="stretch", key="evm_indices_chart")

    evm_low_left, evm_low_right = st.columns([1, 1])
    with evm_low_left:
        st.plotly_chart(evm_variance_chart(evm_metrics, t(language, "evm_variances"), dark_mode), width="stretch", key="evm_variance_chart")
    with evm_low_right:
        st.plotly_chart(evm_forecast_chart(evm_metrics, t(language, "evm_forecast"), dark_mode), width="stretch", key="evm_forecast_chart")

    source_rows = []
    for field, item in evm_metrics["source_data"].items():
        source_rows.append({
            "Field": field.upper().replace("_PERCENT", " %"),
            "Value": format_percent(item.get("value")) if field.endswith("percent") else format_currency(item.get("value")),
            "Confidence": f"{float(item.get('confidence') or 0) * 100:.0f}%",
            "Method": item.get("method", "not_found"),
            "Evidence": item.get("evidence", ""),
        })
    with st.expander(t(language, "evm_source_data"), expanded=True):
        st.dataframe(pd.DataFrame(source_rows), width="stretch", hide_index=True)

    if evm_metrics["missing_sources"]:
        st.warning(f"{t(language, 'missing_evm_data')}: {', '.join(evm_metrics['missing_sources'])}")
    with st.expander(t(language, "evm_assumptions"), expanded=bool(evm_metrics["missing_sources"])):
        for item in evm_metrics["assumptions"]:
            st.write(f"- {item}")

with tabs[5]:
    left, right = st.columns([1, 1])
    with left:
        st.plotly_chart(resource_load_chart(timeline_df, t(language, "resource_load"), dark_mode), width="stretch", key="resource_load_chart")
    with right:
        st.plotly_chart(resource_donut(timeline_df, t(language, "resource_load"), dark_mode), width="stretch", key="resource_donut")
    with st.expander(t(language, "portfolio_signal"), expanded=True):
        st.dataframe(timeline_df, width="stretch", hide_index=True)

with tabs[6]:
    insight_cols = st.columns(3)
    with insight_cols[0]:
        insight_card("Key Risk" if language == "English" else "الخطر الرئيسي", "<br>".join(ai_json.get("executive_summary", [])[:2]), metrics["project_status"])
    with insight_cols[1]:
        insight_card(t(language, "root_cause"), "<br>".join(ai_json.get("root_cause", [])), ai_json.get("priority_level", "Medium"))
    with insight_cols[2]:
        insight_card(t(language, "impact_reduction"), ai_json.get("estimated_impact_reduction", "15-25%"), f"{t(language, 'confidence_score')}: {ai_json.get('confidence_score', metrics['ai_confidence'])}%")

    st.markdown(markdown_from_ai_json(ai_json, language))

    if ai_json.get("risk_register"):
        st.markdown("### Detailed Risk Register" if language == "English" else "### سجل المخاطر التفصيلي")
        st.dataframe(pd.DataFrame(ai_json["risk_register"]), width="stretch", hide_index=True)

    with st.expander(t(language, "chat_title"), expanded=False):
        question = st.text_input(t(language, "chat_placeholder"))
        if st.button(t(language, "chat_button"), disabled=not question or client is None or is_demo):
            try:
                answer = answer_question(client, language, question, ai_json, risk_signals, metrics, evm_ai_context, schedule_ai_context)
            except Exception as exc:
                answer = f"AI analysis service error: {exc}"
            st.session_state.chat_history.append({"question": question, "answer": answer})
        for item in reversed(st.session_state.chat_history[-5:]):
            st.markdown(f"**Q:** {item['question']}")
            st.markdown(item["answer"])
    floating_assistant(t(language, "assistant_label"))

with tabs[7]:
    left, right = st.columns([1.1, .9])
    with left:
        soft_panel(f"<h3>{t(language, 'executive_summary')}</h3><p>{' '.join(ai_json.get('executive_summary', []))}</p>")
        for item in ai_json.get("recommendations", []) + ai_json.get("recommended_actions", []):
            st.write(f"- {item}")
    with right:
        st.plotly_chart(risk_radar(risk_df, t(language, "risk_radar"), dark_mode), width="stretch", key="report_radar")
        try:
            pdf_data = build_pdf(language, labels, metrics, risk_df, ai_json, evm_metrics, schedule_metrics)
            st.download_button(
                label=t(language, "download_pdf"),
                data=pdf_data,
                file_name="Project_Risk_Analyzer_Executive_Report.pdf",
                mime="application/pdf",
                width="stretch",
            )
        except Exception as exc:
            st.warning(f"Report export is temporarily unavailable: {exc}")
