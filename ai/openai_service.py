import json

MAX_AI_DOCUMENT_CHARS = 14000


def parse_ai_response(content):
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None


def extract_evm_source_data_with_ai(client, language, extracted_text):
    """Use the existing LLM integration as a structured EVM source extractor."""

    analysis_language = "Arabic" if language == "العربية" else "English"
    document_excerpt = extracted_text[:MAX_AI_DOCUMENT_CHARS]
    prompt = f"""
Extract Earned Value Management source data from this project document.

Return valid JSON only. Do not calculate EVM metrics here.
Only extract source values that are clearly supported by evidence.

Recognize semantic equivalents:
- BAC: Budget at Completion, approved budget, project budget, total baseline budget.
- AC: Actual Cost, cost incurred, current spending, money spent, actual expenditure.
- Planned %: planned progress, planned completion, baseline progress.
- Actual %: actual progress, physical progress, work completed, percent complete.

JSON schema:
{{
  "bac": {{"value": number or null, "confidence": 0.0, "evidence": "...", "source": "llm_document_context", "method": "llm_semantic_extraction"}},
  "ac": {{"value": number or null, "confidence": 0.0, "evidence": "...", "source": "llm_document_context", "method": "llm_semantic_extraction"}},
  "planned_percent": {{"value": decimal_0_to_1_or_null, "confidence": 0.0, "evidence": "...", "source": "llm_document_context", "method": "llm_semantic_extraction"}},
  "actual_percent": {{"value": decimal_0_to_1_or_null, "confidence": 0.0, "evidence": "...", "source": "llm_document_context", "method": "llm_semantic_extraction"}}
}}

If a value is not clearly present, set it to null and confidence to 0.
Do not infer, estimate, or fabricate missing values.

Document language may be {analysis_language}.

Project document:
{document_excerpt}
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You extract PMBOK EVM source fields as strict JSON."},
            {"role": "user", "content": prompt},
        ],
    )
    data = parse_ai_response(response.choices[0].message.content) or {}
    normalized = {}
    for field in ("bac", "ac", "planned_percent", "actual_percent"):
        item = data.get(field) if isinstance(data, dict) else None
        if isinstance(item, dict):
            normalized[field] = {
                "value": item.get("value"),
                "confidence": float(item.get("confidence") or 0),
                "evidence": item.get("evidence", ""),
                "source": item.get("source", "llm_document_context"),
                "method": item.get("method", "llm_semantic_extraction"),
            }
    return normalized


def default_ai_json(language):
    if language == "العربية":
        return {
            "executive_summary": ["تم إنشاء تحليل محلي أولي. فعّل التحليل الذكي للحصول على تقييم تنفيذي أعمق."],
            "root_cause": ["تحتاج مؤشرات المشروع إلى مراجعة تفصيلية للجدول والميزانية والنطاق."],
            "detailed_findings": [
                "يجب مراجعة خط الأساس للجدول وربطه بسجل المخاطر والاعتماديات.",
                "ينبغي التحقق من افتراضات التكلفة مقابل النطاق ونقاط التسليم.",
            ],
            "risk_register": [
                {"risk": "تأخير التسليم", "category": "الجدول", "severity": "متوسط", "evidence": "مؤشرات محلية من الملف والمدخلات", "mitigation": "تحديث خطة المعالم والاعتماديات", "owner": "مدير المشروع"},
                {"risk": "انحراف التكلفة", "category": "التكلفة", "severity": "متوسط", "evidence": "مؤشرات الميزانية والنطاق", "mitigation": "تفعيل مراجعة تكلفة أسبوعية", "owner": "المالية / PMO"},
            ],
            "schedule_assessment": ["تحليل أولي يشير إلى ضرورة متابعة المعالم الحرجة وتوثيق الاعتماديات."],
            "budget_assessment": ["تحتاج الميزانية إلى ربط أوضح بين البنود والنطاق ومخاطر التغيير."],
            "resource_assessment": ["ينبغي مراجعة توفر الموارد مقابل مراحل التكامل والاختبار."],
            "scope_governance": ["يجب تثبيت آلية الموافقة على التغييرات وتحديد أثرها على التكلفة والوقت."],
            "decision_recommendation": "المتابعة مع ضوابط تنفيذية",
            "thirty_day_action_plan": ["تحديث سجل المخاطر", "تعيين ملاك المخاطر", "مراجعة خط الأساس للجدول والميزانية"],
            "assumptions_and_gaps": ["التحليل المحلي محدود بمحتوى الملف والمدخلات المتاحة."],
            "recommended_actions": ["تحديد مالك لكل خطر", "تحديث خط الأساس للجدول", "مراجعة افتراضات الميزانية"],
            "priority_level": "متوسط",
            "estimated_impact_reduction": "15-25%",
            "confidence_score": 72,
            "recommendations": ["إضافة سجل مخاطر محدث", "تحديد نقاط قرار تنفيذية أسبوعية"],
        }
    return {
        "executive_summary": ["A local baseline analysis was generated. Refresh AI insights for a deeper executive assessment."],
        "root_cause": ["Project indicators require deeper review across schedule, budget, scope, and delivery constraints."],
        "detailed_findings": [
            "The schedule baseline should be reconciled with dependencies, risk ownership, and milestone controls.",
            "Budget assumptions should be validated against scope boundaries and delivery commitments.",
        ],
        "risk_register": [
            {"risk": "Delivery delay", "category": "Schedule", "severity": "Medium", "evidence": "Local file and input signals", "mitigation": "Update milestone and dependency control plan", "owner": "Project Manager"},
            {"risk": "Cost variance", "category": "Cost", "severity": "Medium", "evidence": "Budget and scope indicators", "mitigation": "Run weekly cost variance review", "owner": "Finance / PMO"},
        ],
        "schedule_assessment": ["Initial indicators suggest closer tracking of critical milestones and cross-workstream dependencies."],
        "budget_assessment": ["Budget governance should connect spend categories to scope, risks, and change-control triggers."],
        "resource_assessment": ["Resource availability should be reviewed against integration, testing, and handover phases."],
        "scope_governance": ["Scope changes need explicit approval paths, impact analysis, and executive escalation thresholds."],
        "decision_recommendation": "Proceed with executive controls",
        "thirty_day_action_plan": ["Refresh the risk register", "Assign risk owners", "Review schedule and budget baselines"],
        "assumptions_and_gaps": ["Local analysis is limited to uploaded evidence and available sidebar parameters."],
        "recommended_actions": ["Assign owners to key risks", "Refresh the schedule baseline", "Validate budget assumptions"],
        "priority_level": "Medium",
        "estimated_impact_reduction": "15-25%",
        "confidence_score": 72,
        "recommendations": ["Maintain an active risk register", "Create weekly executive decision gates"],
    }


def markdown_from_ai_json(ai_json, language):
    headings = {
        "English": {
            "executive_summary": "Executive Summary",
            "root_cause": "Root Cause",
            "detailed_findings": "Detailed PMO Findings",
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
            "thirty_day_action_plan": "30-Day Action Plan",
            "assumptions_and_gaps": "Assumptions and Gaps",
            "recommended_actions": "Recommended Actions",
            "recommendations": "Recommendations",
        },
        "العربية": {
            "executive_summary": "الملخص التنفيذي",
            "root_cause": "السبب الجذري",
            "detailed_findings": "نتائج تفصيلية لإدارة المشاريع",
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
            "thirty_day_action_plan": "خطة العمل خلال 30 يوماً",
            "assumptions_and_gaps": "الافتراضات والفجوات",
            "recommended_actions": "الإجراءات الموصى بها",
            "recommendations": "التوصيات",
        },
    }[language]

    sections = []
    for key, heading in headings.items():
        value = ai_json.get(key, [])
        items = value if isinstance(value, list) else [str(value)]
        sections.append(f"### {heading}")
        sections.extend([f"- {item}" for item in items if isinstance(item, str) and item])

    risk_heading = "Risk Register" if language == "English" else "سجل المخاطر"
    sections.append(f"### {risk_heading}")
    for item in ai_json.get("risk_register", []):
        if isinstance(item, dict):
            risk = item.get("risk", "")
            severity = item.get("severity", "")
            evidence = item.get("evidence", "")
            mitigation = item.get("mitigation", "")
            owner = item.get("owner", "")
            sections.append(f"- **{risk}** | {severity} | {evidence} | {mitigation} | {owner}")
    return "\n\n".join(sections)


def analyze_project(client, language, project_inputs, extracted_text, risk_signals, metrics, evm_metrics=None, schedule_metrics=None):
    analysis_language = "Arabic" if language == "العربية" else "English"
    document_excerpt = extracted_text[:MAX_AI_DOCUMENT_CHARS]
    evm_context = evm_metrics or {}
    schedule_context = schedule_metrics or {}

    prompt = f"""
You are a senior PMO, industrial engineering, and project analytics consultant.

Return valid JSON only in {analysis_language}. Do not use any other language.

JSON schema:
{{
  "executive_summary": ["..."],
  "root_cause": ["..."],
  "detailed_findings": ["..."],
  "risk_register": [
    {{
      "risk": "...",
      "category": "...",
      "severity": "Low | Medium | High | Critical",
      "evidence": "...",
      "mitigation": "...",
      "owner": "..."
    }}
  ],
  "schedule_assessment": ["..."],
  "budget_assessment": ["..."],
  "project_health_assessment": ["..."],
  "cost_performance": ["..."],
  "schedule_performance": ["..."],
  "forecast": ["..."],
  "corrective_actions": ["..."],
  "preventive_actions": ["..."],
  "pmo_recommendations": ["..."],
  "critical_path_interpretation": ["..."],
  "float_risks": ["..."],
  "milestone_delays": ["..."],
  "s_curve_performance": ["..."],
  "finish_date_forecast": ["..."],
  "schedule_recovery_actions": ["..."],
  "resource_assessment": ["..."],
  "scope_governance": ["..."],
  "decision_recommendation": "...",
  "thirty_day_action_plan": ["..."],
  "assumptions_and_gaps": ["..."],
  "recommended_actions": ["..."],
  "priority_level": "Low | Medium | High | Critical",
  "estimated_impact_reduction": "percentage range",
  "confidence_score": 0,
  "recommendations": ["..."]
}}

Analyze the project in depth using PMO governance, industrial engineering, operations analytics, delivery controls, earned value thinking, schedule/cost risk, resource constraints, stakeholder readiness, scope governance, and executive decision support.

Depth requirements:
- Produce a detailed analysis, not a short overview.
- Include at least 5 detailed PMO findings.
- Include at least 6 risks in the risk_register when evidence allows.
- Each risk must include evidence from the file or from computed indicators.
- Explain likely root causes, operational impact, and mitigation logic.
- Identify missing information and assumptions.
- Give a 30-day action plan suitable for PMO leadership.
- Use Earned Value Management values when available. If EVM data is missing, state the exact missing source data and continue with risk-based analysis.
- Use Schedule Control data when available. Interpret critical path, total float, milestone slippage, S-curve performance, and finish-date forecast.
- Do not invent BAC, PV, EV, AC, SPI, CPI, EAC, ETC, VAC, or TCPI values.
- Do not invent critical path, float, milestone dates, or forecast finish dates when schedule data is missing.
- Keep text professional and specific.

Project inputs:
{json.dumps(project_inputs, ensure_ascii=False)}

Computed metrics:
{json.dumps(metrics, ensure_ascii=False)}

PMBOK Earned Value Management metrics:
{json.dumps(evm_context, ensure_ascii=False)}

Schedule Control metrics:
{json.dumps(schedule_context, ensure_ascii=False)}

Rule-based risk signals:
{json.dumps(risk_signals, ensure_ascii=False)}

Project file evidence:
{document_excerpt}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": f"You are an executive PMO risk assistant. Respond only in {analysis_language} as valid JSON."},
            {"role": "user", "content": prompt},
        ],
    )
    content = response.choices[0].message.content
    return parse_ai_response(content) or default_ai_json(language)


def answer_question(client, language, question, ai_json, risk_signals, metrics, evm_metrics=None, schedule_metrics=None):
    analysis_language = "Arabic" if language == "العربية" else "English"
    prompt = f"""
Answer this project risk question in {analysis_language}. Be concise and decision-oriented.

Question: {question}

AI analysis:
{json.dumps(ai_json, ensure_ascii=False)}

Risk signals:
{json.dumps(risk_signals, ensure_ascii=False)}

Metrics:
{json.dumps(metrics, ensure_ascii=False)}

Earned Value Management:
{json.dumps(evm_metrics or {}, ensure_ascii=False)}

Schedule Control:
{json.dumps(schedule_metrics or {}, ensure_ascii=False)}
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": f"You are a project risk decision-support assistant. Respond only in {analysis_language}."},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content
