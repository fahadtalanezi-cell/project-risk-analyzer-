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


def pdf_currency(value):
    if value is None:
        return "Not available"
    return f"{value:,.0f}"


def pdf_index(value):
    if value is None:
        return "Not available"
    return f"{value:.2f}"


def pdf_percent(value):
    if value is None:
        return "Not available"
    return f"{value * 100:.1f}%"


def build_pdf(language, labels, metrics, risk_df, ai_json, evm_metrics=None, schedule_metrics=None):
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

    if evm_metrics:
        evm_values = evm_metrics.get("values", {})
        traffic = evm_metrics.get("traffic_lights", {})
        interpretation = evm_metrics.get("interpretation", {})
        story.extend([
            Spacer(1, 14),
            paragraph("Earned Value Management Dashboard" if language == "English" else "لوحة إدارة القيمة المكتسبة", styles["Section"], language, bold=True),
        ])
        evm_rows = [
            ["BAC", pdf_currency(evm_values.get("bac")), "Budget at Completion"],
            ["PV", pdf_currency(evm_values.get("pv")), "PV = BAC x Planned %"],
            ["EV", pdf_currency(evm_values.get("ev")), "EV = BAC x Actual %"],
            ["AC", pdf_currency(evm_values.get("ac")), "Actual Cost"],
            ["SV", pdf_currency(evm_values.get("sv")), "SV = EV - PV"],
            ["CV", pdf_currency(evm_values.get("cv")), "CV = EV - AC"],
            ["SPI", pdf_index(evm_values.get("spi")), "SPI = EV / PV"],
            ["CPI", pdf_index(evm_values.get("cpi")), "CPI = EV / AC"],
            ["EAC", pdf_currency(evm_values.get("eac")), evm_metrics.get("formulas", {}).get("eac") or "Not available"],
            ["ETC", pdf_currency(evm_values.get("etc")), "ETC = EAC - AC"],
            ["VAC", pdf_currency(evm_values.get("vac")), "VAC = BAC - EAC"],
            ["TCPI", pdf_index(evm_values.get("tcpi")), evm_metrics.get("formulas", {}).get("tcpi") or "Not available"],
            ["Percent Complete", pdf_percent(evm_values.get("percent_complete")), "Actual % or EV / BAC"],
        ]
        evm_table_data = [[
            paragraph(row[0], styles["BodyText"], language, bold=True),
            paragraph(row[1], styles["BodyText"], language),
            paragraph(row[2], styles["BodyText"], language),
        ] for row in evm_rows]
        evm_table = Table(evm_table_data, colWidths=[90, 125, 245])
        evm_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ede9fe")),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(evm_table)

        traffic_lines = [
            f"Schedule: {traffic.get('schedule', 'gray')} - {interpretation.get('schedule', '')}",
            f"Cost: {traffic.get('cost', 'gray')} - {interpretation.get('cost', '')}",
            f"Forecast: {traffic.get('forecast', 'gray')} - {interpretation.get('forecast', '')}",
            f"TCPI: {traffic.get('tcpi', 'gray')} - {interpretation.get('tcpi', '')}",
        ]
        story.extend([Spacer(1, 8), paragraph("Traffic-Light Management Interpretation" if language == "English" else "تفسير مؤشرات الحالة", styles["Section"], language, bold=True)])
        for line in traffic_lines:
            story.append(paragraph(f"• {line}", styles["BodyText"], language))

        missing = evm_metrics.get("missing_sources", [])
        assumptions = evm_metrics.get("assumptions", [])
        if missing or assumptions:
            story.extend([Spacer(1, 8), paragraph("EVM Assumptions and Data Gaps" if language == "English" else "افتراضات وفجوات القيمة المكتسبة", styles["Section"], language, bold=True)])
            if missing:
                story.append(paragraph(f"• Missing source data: {', '.join(missing)}", styles["BodyText"], language))
            for item in assumptions:
                story.append(paragraph(f"• {item}", styles["BodyText"], language))

    if schedule_metrics:
        story.extend([
            Spacer(1, 14),
            paragraph("Schedule Control Dashboard" if language == "English" else "لوحة ضبط الجدول الزمني", styles["Section"], language, bold=True),
        ])
        forecast = schedule_metrics.get("forecast", {})
        schedule_rows = [
            ["Schedule Health", str(schedule_metrics.get("traffic_light", "gray")).upper()],
            ["Baseline Finish", str(forecast.get("baseline_finish") or "Not enough schedule data")[:10]],
            ["Forecast Finish", str(forecast.get("forecast_finish") or "Not enough schedule data")[:10]],
            ["Forecast Delay Days", str(forecast.get("forecast_delay_days") if forecast.get("forecast_delay_days") is not None else "Not enough schedule data")],
            ["Forecast Method", str(forecast.get("method", "Not enough schedule data"))],
        ]
        schedule_table = Table([
            [paragraph(a, styles["BodyText"], language, bold=True), paragraph(b, styles["BodyText"], language)]
            for a, b in schedule_rows
        ], colWidths=[180, 280])
        schedule_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ede9fe")),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(schedule_table)

        critical_path = schedule_metrics.get("critical_path", [])
        story.extend([Spacer(1, 8), paragraph("Critical Path" if language == "English" else "المسار الحرج", styles["Section"], language, bold=True)])
        if critical_path:
            for activity in critical_path[:12]:
                story.append(paragraph(f"• {activity}", styles["BodyText"], language))
        else:
            story.append(paragraph("• Not enough schedule data to calculate the critical path.", styles["BodyText"], language))

        float_table = schedule_metrics.get("float_table")
        if float_table is not None and not float_table.empty:
            story.extend([Spacer(1, 8), paragraph("Float Summary" if language == "English" else "ملخص السماحية الزمنية", styles["Section"], language, bold=True)])
            for _, row in float_table.head(10).iterrows():
                story.append(paragraph(f"• {row.get('activity')} | Total Float: {row.get('total_float')} | Critical: {row.get('is_critical')}", styles["BodyText"], language))

        milestones = schedule_metrics.get("milestones")
        story.extend([Spacer(1, 8), paragraph("Milestone Slippage" if language == "English" else "انزلاق المعالم", styles["Section"], language, bold=True)])
        if milestones is not None and not milestones.empty:
            for _, row in milestones.head(10).iterrows():
                line = f"{row.get('milestone')} | Planned: {row.get('planned_date')} | Actual/Forecast: {row.get('actual_or_forecast_date')} | Slippage: {row.get('slippage_days')} days | {row.get('status')}"
                story.append(paragraph(f"• {line}", styles["BodyText"], language))
        else:
            story.append(paragraph("• Not enough schedule data to calculate milestone slippage.", styles["BodyText"], language))

        s_curve = schedule_metrics.get("s_curve")
        story.extend([Spacer(1, 8), paragraph("S-Curve Summary" if language == "English" else "ملخص منحنى S", styles["Section"], language, bold=True)])
        if s_curve is not None and not s_curve.empty:
            latest = s_curve.tail(1).iloc[0]
            story.append(paragraph(f"• Latest cumulative PV: {pdf_currency(latest.get('PV'))}, EV: {pdf_currency(latest.get('EV'))}, AC: {pdf_currency(latest.get('AC'))}.", styles["BodyText"], language))
        else:
            story.append(paragraph("• Not enough schedule data to build an S-curve.", styles["BodyText"], language))

        assumptions = schedule_metrics.get("assumptions", [])
        missing = schedule_metrics.get("missing_data", [])
        if assumptions or missing:
            story.extend([Spacer(1, 8), paragraph("Schedule Assumptions and Data Gaps" if language == "English" else "افتراضات وفجوات الجدول الزمني", styles["Section"], language, bold=True)])
            if missing:
                story.append(paragraph(f"• Missing source data: {', '.join(missing)}", styles["BodyText"], language))
            for item in assumptions:
                story.append(paragraph(f"• {item}", styles["BodyText"], language))

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
            "project_health_assessment": "Project Health Assessment",
            "cost_performance": "Cost Performance",
            "schedule_performance": "Schedule Performance",
            "forecast": "Forecast",
            "corrective_actions": "Corrective Actions",
            "preventive_actions": "Preventive Actions",
            "pmo_recommendations": "PMO Recommendations",
            "critical_path_interpretation": "Critical Path Interpretation",
            "float_risks": "Float Risks",
            "milestone_delays": "Milestone Delays",
            "s_curve_performance": "S-Curve Performance",
            "finish_date_forecast": "Finish Date Forecast",
            "schedule_recovery_actions": "Schedule Recovery Actions",
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
            "project_health_assessment": "تقييم صحة المشروع",
            "cost_performance": "أداء التكلفة",
            "schedule_performance": "أداء الجدول",
            "forecast": "التوقعات",
            "corrective_actions": "الإجراءات التصحيحية",
            "preventive_actions": "الإجراءات الوقائية",
            "pmo_recommendations": "توصيات مكتب إدارة المشاريع",
            "critical_path_interpretation": "تفسير المسار الحرج",
            "float_risks": "مخاطر السماحية الزمنية",
            "milestone_delays": "تأخيرات المعالم",
            "s_curve_performance": "أداء منحنى S",
            "finish_date_forecast": "توقع تاريخ الانتهاء",
            "schedule_recovery_actions": "إجراءات استعادة الجدول",
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
        "project_health_assessment",
        "cost_performance",
        "schedule_performance",
        "forecast",
        "corrective_actions",
        "preventive_actions",
        "pmo_recommendations",
        "critical_path_interpretation",
        "float_risks",
        "milestone_delays",
        "s_curve_performance",
        "finish_date_forecast",
        "schedule_recovery_actions",
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
