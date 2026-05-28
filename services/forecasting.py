import pandas as pd


def build_forecast(risk_score, category_scores):
    periods = list(range(1, 9))
    delay_curve = [round((risk_score / 12) * (period ** 1.08), 1) for period in periods]
    variance_curve = [round((category_scores["cost"] / 18) * period * 1.7, 1) for period in periods]
    performance_curve = [max(40, round(100 - risk_score * 0.25 - period * 2.2, 1)) for period in periods]
    return pd.DataFrame({
        "period": periods,
        "predicted_delay_days": delay_curve,
        "budget_variance_pct": variance_curve,
        "performance_index": performance_curve,
    })


def performance_indicators(risk_score, category_scores):
    spi = max(0.55, round(1 - category_scores["schedule"] / 180, 2))
    cpi = max(0.55, round(1 - category_scores["cost"] / 190, 2))
    predicted_delay = round(risk_score * 0.42 + category_scores["schedule"] * 0.18)
    budget_variance = round(category_scores["cost"] * 0.32 + risk_score * 0.08, 1)
    critical_tasks = max(1, int((risk_score + category_scores["delivery"]) / 28))
    return {
        "spi": spi,
        "cpi": cpi,
        "predicted_delay": predicted_delay,
        "budget_variance": budget_variance,
        "critical_tasks": critical_tasks,
        "schedule_health": int(spi * 100),
        "budget_health": int(cpi * 100),
    }
