import streamlit as st


def inject_css(dark_mode, direction):
    bg = "#060b18" if dark_mode else "#f6f4ff"
    panel = "#0d1428" if dark_mode else "#ffffff"
    text = "#f8fafc" if dark_mode else "#111827"
    muted = "#a7a3c8" if dark_mode else "#6b668a"
    border = "rgba(167,139,250,.22)" if dark_mode else "rgba(109,40,217,.14)"
    align = "right" if direction == "rtl" else "left"
    st.markdown(
        f"""
        <style>
        .stApp {{
            background:
                radial-gradient(circle at 12% 6%, rgba(124,58,237,.28), transparent 28%),
                radial-gradient(circle at 86% 16%, rgba(91,33,182,.22), transparent 30%),
                linear-gradient(180deg, {bg}, #050816 75%);
            color: {text};
            direction: ltr;
        }}
        section[data-testid="stSidebar"] {{
            background: linear-gradient(180deg, rgba(13,20,40,.98), rgba(8,13,29,.98));
            border-right: 1px solid {border};
            direction: ltr;
            text-align: {align};
        }}
        .block-container {{
            padding-top: .85rem;
            max-width: 1480px;
            direction: ltr;
            text-align: {align};
        }}
        .stMarkdown, .stMarkdown p, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4,
        label, div[data-testid="stWidgetLabel"], div[data-testid="stMetricLabel"], div[data-testid="stMetricValue"] {{
            direction: {direction};
            text-align: {align};
        }}
        div[data-testid="stHorizontalBlock"] {{
            direction: ltr;
        }}
        div[data-testid="stTabs"] [role="tablist"] {{
            direction: ltr;
            justify-content: flex-start;
        }}
        div[data-testid="stTabs"] button {{
            direction: ltr;
        }}
        div[data-testid="stTabs"] button p {{
            direction: {direction};
            text-align: {align};
        }}
        input, textarea, div[data-baseweb="select"] {{
            direction: {direction};
            text-align: {align};
        }}
        div[data-baseweb="select"] input {{
            caret-color: transparent;
            cursor: default;
        }}
        .hero {{
            border: 1px solid {border};
            background:
                linear-gradient(135deg, rgba(12,18,38,.96), rgba(54,23,108,.92)),
                radial-gradient(circle at 82% 10%, rgba(167,139,250,.38), transparent 26%);
            color: white;
            padding: 24px 28px;
            border-radius: 22px;
            margin-bottom: 12px;
            box-shadow: 0 24px 80px rgba(31,14,78,.32);
            text-align: {align};
            direction: {direction};
            position: relative;
            overflow: hidden;
            animation: fadeUp .45s ease both;
        }}
        .hero h1 {{
            font-size: 36px;
            line-height: 1.15;
            margin: 0 0 8px 0;
            letter-spacing: 0;
        }}
        .hero p {{
            color: #ddd6fe;
            font-size: 16px;
            margin: 0;
        }}
        .hero-meta {{
            display: inline-flex;
            gap: 8px;
            align-items: center;
            border: 1px solid rgba(221,214,254,.22);
            background: rgba(255,255,255,.08);
            border-radius: 999px;
            padding: 6px 10px;
            margin-bottom: 10px;
            color: #ede9fe;
            font-size: 12px;
            backdrop-filter: blur(14px);
        }}
        .soft-panel {{
            border: 1px solid {border};
            background: rgba(13,20,40,.72);
            border-radius: 18px;
            padding: 16px;
            box-shadow: 0 16px 50px rgba(2,6,23,.2);
            backdrop-filter: blur(18px);
            margin-bottom: 12px;
        }}
        .status-pill {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            color: #ddd6fe;
            border: 1px solid rgba(167,139,250,.26);
            background: rgba(91,33,182,.16);
            border-radius: 999px;
            padding: 7px 11px;
            font-size: 12px;
        }}
        .kpi-grid {{
            position: sticky;
            top: 0;
            z-index: 999;
            padding: 8px 0 14px 0;
            backdrop-filter: blur(10px);
        }}
        .kpi-card {{
            background: linear-gradient(180deg, rgba(15,23,42,.86), rgba(17,24,39,.64));
            border: 1px solid {border};
            border-radius: 16px;
            padding: 13px 13px 11px 13px;
            min-height: 96px;
            box-shadow: 0 12px 38px rgba(31,14,78,.2);
            transition: transform .18s ease, border-color .18s ease;
            direction: {direction};
            text-align: {align};
            margin-bottom: 10px;
        }}
        .kpi-card:hover {{
            transform: translateY(-3px);
            border-color: rgba(196,181,253,.65);
            box-shadow: 0 18px 55px rgba(91,33,182,.34);
        }}
        .kpi-label {{
            color: {muted};
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: .04em;
        }}
        .kpi-value {{
            color: {text};
            font-size: 24px;
            font-weight: 750;
            margin-top: 10px;
        }}
        .kpi-note {{
            color: {muted};
            font-size: 12px;
            margin-top: 6px;
        }}
        .insight-card {{
            background: linear-gradient(180deg, rgba(15,23,42,.82), rgba(30,27,75,.45));
            border: 1px solid {border};
            border-radius: 14px;
            padding: 16px;
            min-height: 160px;
            direction: {direction};
            text-align: {align};
        }}
        .empty-state {{
            background: linear-gradient(180deg, rgba(15,23,42,.74), rgba(49,46,129,.28));
            border: 1px dashed rgba(139,92,246,.55);
            border-radius: 16px;
            padding: 26px;
            color: {text};
            direction: {direction};
            text-align: {align};
        }}
        .floating-assistant {{
            position: fixed;
            right: 24px;
            bottom: 22px;
            z-index: 1000;
            padding: 12px 16px;
            border-radius: 999px;
            color: #f5f3ff;
            background: linear-gradient(135deg, rgba(91,33,182,.96), rgba(49,46,129,.96));
            border: 1px solid rgba(221,214,254,.28);
            box-shadow: 0 18px 55px rgba(49,46,129,.42);
            font-weight: 700;
        }}
        .sidebar-bottom-control {{
            margin-top: 36vh;
            padding-top: 14px;
            border-top: 1px solid {border};
        }}
        @keyframes fadeUp {{
            from {{ opacity: 0; transform: translateY(8px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        div[data-testid="stTabs"] button p {{
            font-weight: 700;
        }}
        @media (max-width: 1100px) {{
            .kpi-grid {{ position: relative; }}
            .hero h1 {{ font-size: 26px; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero(title, subtitle):
    st.markdown(
        f"<div class='hero'><div class='hero-meta'>PMO Intelligence Platform</div><h1>{title}</h1><p>{subtitle}</p></div>",
        unsafe_allow_html=True,
    )


def kpi_cards(cards):
    columns = st.columns(len(cards))

    for column, card in zip(columns, cards):
        with column:
            st.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-label">{card['label']}</div>
                    <div class="kpi-value">{card['value']}</div>
                    <div class="kpi-note">{card.get('note', '')}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def insight_card(title, body, footer=""):
    st.markdown(
        f"""
        <div class='insight-card'>
            <h4>{title}</h4>
            <p>{body}</p>
            <small>{footer}</small>
        </div>
        """,
        unsafe_allow_html=True,
    )


def soft_panel(content):
    st.markdown(f"<div class='soft-panel'>{content}</div>", unsafe_allow_html=True)


def status_pill(text):
    st.markdown(f"<span class='status-pill'>{text}</span>", unsafe_allow_html=True)


def floating_assistant(label):
    st.markdown(f"<div class='floating-assistant'>{label}</div>", unsafe_allow_html=True)
