import html
import os
import re
from io import BytesIO

from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.graphics.charts.barcharts import HorizontalBarChart
from reportlab.graphics.shapes import Drawing, String


def strip_symbols(text):
    for symbol in ["🔴", "🟠", "🟡", "🟢", "🚀", "📥", "💡"]:
        text = text.replace(symbol, "")
    return re.sub(r"\s+", " ", str(text)).strip()


def prepare_pdf_text(text, language):
    text = strip_symbols(text)
    if language != "العربية":
        return text
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        return get_display(arabic_reshaper.reshape(text))
    except ImportError:
        return text


def register_fonts(language):
    regular_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        r"C:\Windows\Fonts\arial.ttf",
    ]
    bold_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
    ]
    regular = next((path for path in regular_candidates if os.path.exists(path)), None)
    bold = next((path for path in bold_candidates if os.path.exists(path)), regular)
    font_name = "ArabicFont" if language == "العربية" else "ReportFont"
    bold_name = f"{font_name}-Bold"

    if not regular:
        return "Helvetica", "Helvetica-Bold"

    if font_name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(font_name, regular))
    if bold_name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(bold_name, bold))
    return font_name, bold_name


def paragraph(text, style, language, bold=False):
    safe = html.escape(prepare_pdf_text(text, language))
    return Paragraph(f"<b>{safe}</b>" if bold else safe, style)


def build_pdf(language, labels, metrics, risk_df, ai_json):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=42, leftMargin=42, topMargin=42, bottomMargin=42)
    font_name, bold_name = register_fonts(language)
    alignment = TA_RIGHT if language == "العربية" else TA_LEFT

    styles = getSampleStyleSheet()
    styles["Title"].fontName = bold_name
    styles["Title"].alignment = alignment
    styles["BodyText"].fontName = font_name
    styles["BodyText"].fontSize = 10
    styles["BodyText"].leading = 15
    styles["BodyText"].alignment = alignment
    styles.add(ParagraphStyle("Section", parent=styles["BodyText"], fontName=bold_name, fontSize=13, leading=18, spaceBefore=12))

    story = [
        paragraph(labels["app_title"], styles["Title"], language, bold=True),
        Spacer(1, 14),
        paragraph(labels["executive_summary"], styles["Section"], language, bold=True),
        Spacer(1, 6),
    ]

    summary_items = ai_json.get("executive_summary", [])
    for item in summary_items:
        story.append(paragraph(f"• {item}", styles["BodyText"], language))

    story.extend([Spacer(1, 12), paragraph("KPI Dashboard" if language == "English" else "مؤشرات الأداء", styles["Section"], language, bold=True)])
    kpi_rows = [
        [labels["overall_risk"], f"{metrics['risk_score']}/100"],
        [labels["budget_health"], f"{metrics['budget_health']}%"],
        [labels["schedule_health"], f"{metrics['schedule_health']}%"],
        [labels["predicted_delay"], f"{metrics['predicted_delay']} days"],
        [labels["ai_confidence"], f"{metrics['ai_confidence']}%"],
    ]
    table_data = [[paragraph(a, styles["BodyText"], language, bold=True), paragraph(b, styles["BodyText"], language)] for a, b in kpi_rows]
    table = Table(table_data, colWidths=[220, 220])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ede9fe")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(table)

    story.extend([Spacer(1, 14), paragraph(labels["risk_breakdown"], styles["Section"], language, bold=True)])
    risk_rows = [[paragraph(labels["category"], styles["BodyText"], language, bold=True), paragraph(labels["score"], styles["BodyText"], language, bold=True)]]
    for _, row in risk_df.iterrows():
        risk_rows.append([paragraph(row["category"], styles["BodyText"], language), paragraph(str(row["score"]), styles["BodyText"], language)])
    risk_table = Table(risk_rows, colWidths=[260, 120])
    risk_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ddd6fe")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
        ("PADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(risk_table)

    drawing = Drawing(440, 150)
    chart = HorizontalBarChart()
    chart.x = 130
    chart.y = 20
    chart.height = 105
    chart.width = 260
    chart.data = [[float(value) for value in risk_df["score"].tolist()]]
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = 100
    chart.valueAxis.valueStep = 25
    chart.categoryAxis.categoryNames = [
        prepare_pdf_text(value, language)
        for value in risk_df["category"].tolist()
    ]
    chart.bars[0].fillColor = colors.HexColor("#8b5cf6")
    chart.barSpacing = 4
    drawing.add(String(0, 132, prepare_pdf_text(labels["risk_heatmap"], language), fontName=bold_name, fontSize=10))
    drawing.add(chart)
    story.extend([Spacer(1, 10), drawing])

    story.extend([Spacer(1, 14), paragraph(labels["recommendations"], styles["Section"], language, bold=True)])
    for item in ai_json.get("recommendations", []) + ai_json.get("recommended_actions", []):
        story.append(paragraph(f"• {item}", styles["BodyText"], language))

    section_titles = {
        "English": {
            "root_cause": "Root Cause Analysis",
            "detailed_findings": "Detailed PMO Findings",
            "risk_register": "Detailed Risk Register",
            "schedule_assessment": "Schedule Assessment",
            "budget_assessment": "Budget Assessment",
            "resource_assessment": "Resource Assessment",
            "scope_governance": "Scope Governance",
            "decision_recommendation": "Decision Recommendation",
            "thirty_day_action_plan": "30-Day PMO Action Plan",
            "assumptions_and_gaps": "Assumptions and Information Gaps",
        },
        "العربية": {
            "root_cause": "تحليل السبب الجذري",
            "detailed_findings": "نتائج تفصيلية لإدارة المشاريع",
            "risk_register": "سجل المخاطر التفصيلي",
            "schedule_assessment": "تقييم الجدول الزمني",
            "budget_assessment": "تقييم الميزانية",
            "resource_assessment": "تقييم الموارد",
            "scope_governance": "حوكمة النطاق",
            "decision_recommendation": "توصية القرار",
            "thirty_day_action_plan": "خطة عمل PMO خلال 30 يوماً",
            "assumptions_and_gaps": "الافتراضات وفجوات المعلومات",
        },
    }[language]

    for key in [
        "root_cause",
        "detailed_findings",
        "schedule_assessment",
        "budget_assessment",
        "resource_assessment",
        "scope_governance",
        "decision_recommendation",
        "thirty_day_action_plan",
        "assumptions_and_gaps",
    ]:
        value = ai_json.get(key, [])
        items = value if isinstance(value, list) else [value]
        if not items:
            continue
        story.extend([Spacer(1, 12), paragraph(section_titles[key], styles["Section"], language, bold=True)])
        for item in items:
            story.append(paragraph(f"• {item}", styles["BodyText"], language))

    risk_register = ai_json.get("risk_register", [])
    if risk_register:
        story.extend([Spacer(1, 12), paragraph(section_titles["risk_register"], styles["Section"], language, bold=True)])
        for risk in risk_register:
            if isinstance(risk, dict):
                line = (
                    f"{risk.get('risk', '')} | {risk.get('category', '')} | "
                    f"{risk.get('severity', '')} | {risk.get('evidence', '')} | "
                    f"{risk.get('mitigation', '')} | {risk.get('owner', '')}"
                )
                story.append(paragraph(f"• {line}", styles["BodyText"], language))

    doc.build(story)
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data
