import math
import pandas as pd


def normalize_choice(value):
    return {
        "Low": "low",
        "Medium": "medium",
        "High": "high",
        "منخفض": "low",
        "متوسط": "medium",
        "مرتفع": "high",
    }.get(value, "unknown")


def estimate_ai_confidence(extracted_text, selected_values):
    placeholders = [
        "Select...",
        "اختر...",
        "Select delivery horizon",
        "Select investment tier",
        "Select delivery team scale",
        "Select control level",
        "اختر أفق التسليم",
        "اختر فئة الاستثمار",
        "اختر حجم الفريق",
        "اختر مستوى التحكم",
    ]
    completed_inputs = sum(value not in placeholders for value in selected_values)
    input_score = int((completed_inputs / max(len(selected_values), 1)) * 35)
    document_score = min(len(extracted_text) // 180, 45)
    return min(52 + input_score + document_score, 98)


def calculate_risk(inputs, extracted_text):
    risk_score = 0
    category_scores = {"schedule": 10, "cost": 10, "stakeholder": 10, "scope": 10, "delivery": 10}
    signals = []

    scoring_rules = [
        ("complexity", {"high": 20, "medium": 10}, "delivery"),
        ("stakeholder_engagement", {"low": 18, "medium": 8}, "stakeholder"),
        ("schedule_pressure", {"high": 20, "medium": 10}, "schedule"),
        ("resource_availability", {"low": 18, "medium": 8}, "delivery"),
        ("scope_clarity", {"low": 18, "medium": 8}, "scope"),
        ("duration", {"2-5 Years": 8, "1-2 Years": 5, "2-5 سنوات": 8, "1-2 سنة": 5}, "schedule"),
        ("budget", {"> 5M SAR": 8, "1M - 5M SAR": 5, "أكثر من 5 مليون": 8, "1 مليون - 5 مليون": 5}, "cost"),
        ("team_size", {"100+": 8, "50-100": 5, "10-50": 2}, "delivery"),
    ]

    for field, weights, category in scoring_rules:
        raw_value = inputs.get(field, "")
        points = weights.get(normalize_choice(raw_value), weights.get(raw_value, 0))
        if points:
            risk_score += points
            category_scores[category] += points
            signals.append({"source": field, "signal": raw_value, "points": points, "category": category})

    extracted_lower = extracted_text.lower()
    keyword_rules = [
        ("schedule", ["delay", "late", "behind schedule", "missed milestone", "تأخير", "متأخر", "تأخر"], 18, 35),
        ("cost", ["budget overrun", "cost increase", "financial issue", "over budget", "تجاوز الميزانية", "زيادة التكلفة"], 16, 35),
        ("stakeholder", ["stakeholder issue", "approval delay", "communication issue", "escalation", "تأخير الموافقات", "مشكلة تواصل"], 14, 35),
        ("scope", ["scope creep", "requirement change", "unclear requirements", "change request", "تغيير المتطلبات", "زحف النطاق"], 16, 35),
        ("delivery", ["dependency", "integration issue", "resource shortage", "technical debt", "نقص الموارد", "تكامل", "دين تقني"], 12, 25),
    ]

    for category, keywords, points, category_points in keyword_rules:
        matches = [keyword for keyword in keywords if keyword in extracted_lower][:5]
        if matches:
            risk_score += points
            category_scores[category] += category_points
            signals.append({"source": "document", "signal": ", ".join(matches), "points": points, "category": category})

    bounded_categories = {category: min(score, 100) for category, score in category_scores.items()}
    risk_score = min(risk_score, 100)
    return risk_score, bounded_categories, signals


def project_status(risk_score, labels):
    if risk_score >= 75:
        return labels["critical"]
    if risk_score >= 50:
        return labels["high"]
    if risk_score >= 25:
        return labels["medium"]
    return labels["stable"]


def build_risk_table(category_scores, language):
    labels = {
        "English": ["Schedule", "Cost", "Stakeholder", "Scope", "Delivery"],
        "العربية": ["الجدول الزمني", "التكلفة", "أصحاب المصلحة", "نطاق العمل", "التنفيذ"],
    }[language]
    keys = ["schedule", "cost", "stakeholder", "scope", "delivery"]
    return pd.DataFrame({"key": keys, "category": labels, "score": [category_scores[key] for key in keys]})


def build_heatmap_data(category_scores, language):
    risk_df = build_risk_table(category_scores, language)
    multipliers = {"schedule": 1.2, "cost": 1.4, "stakeholder": 0.8, "scope": 1.1, "delivery": 1.0}
    risk_df["probability"] = risk_df["score"].apply(lambda score: min(5, max(1, math.ceil(score / 20))))
    risk_df["impact"] = risk_df["key"].map(lambda key: min(5, max(1, math.ceil(category_scores[key] * multipliers[key] / 20))))
    risk_df["financial_impact"] = risk_df["score"] * risk_df["key"].map(multipliers) * 15000
    return risk_df


def build_timeline(category_scores, language):
    task_names = {
        "English": ["Initiation", "Scope Baseline", "Procurement", "Integration", "Testing", "Executive Handover"],
        "العربية": ["البدء", "اعتماد النطاق", "المشتريات", "التكامل", "الاختبار", "التسليم التنفيذي"],
    }[language]
    status_labels = {
        "English": {
            "critical": "Critical Path",
            "delayed": "Delayed",
            "track": "On Track",
        },
        "العربية": {
            "critical": "المسار الحرج",
            "delayed": "متأخر",
            "track": "ضمن الخطة",
        },
    }[language]
    starts = pd.date_range("2026-01-05", periods=6, freq="28D")
    durations = [24, 32, 42, 36, 30, 18]
    risk_values = [
        category_scores["stakeholder"],
        category_scores["scope"],
        category_scores["cost"],
        category_scores["delivery"],
        category_scores["schedule"],
        max(category_scores.values()),
    ]
    data = []
    for index, name in enumerate(task_names):
        risk = risk_values[index]
        data.append({
            "task": name,
            "start": starts[index],
            "finish": starts[index] + pd.Timedelta(days=durations[index] + int(risk / 8)),
            "risk": risk,
            "status": status_labels["critical"] if risk >= 55 or index in [2, 3] else (status_labels["delayed"] if risk >= 40 else status_labels["track"]),
        })
    return pd.DataFrame(data)
