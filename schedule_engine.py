"""Professional Schedule Control engine for CPM, S-curve, and milestones."""

from __future__ import annotations

import re
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


ACTIVITY_TERMS = ("activity", "task", "work package", "wbs", "name", "description")
START_TERMS = ("start", "baseline start", "planned start", "early start", "es")
FINISH_TERMS = ("finish", "end", "baseline finish", "planned finish", "early finish", "ef")
DURATION_TERMS = ("duration", "days", "work days")
PREDECESSOR_TERMS = ("predecessor", "predecessors", "dependency", "dependencies", "pred")
MILESTONE_TERMS = ("milestone", "gate", "decision point", "phase gate")
PLANNED_DATE_TERMS = ("planned date", "baseline date", "target date", "planned finish", "baseline finish")
ACTUAL_DATE_TERMS = ("actual date", "forecast date", "actual finish", "forecast finish", "expected date")
PV_TERMS = ("pv", "planned value", "bcws")
EV_TERMS = ("ev", "earned value", "bcwp")
AC_TERMS = ("ac", "actual cost", "acwp", "cost incurred")
DATE_TERMS = ("date", "period", "month", "week", "status date", "data date")
ACTIVITY_NAME_PRIORITY = ("task", "activity name", "activity description", "work package", "name", "description", "activity")
START_PRIORITY = ("planned start", "baseline start", "early start", "start")
FINISH_PRIORITY = ("planned finish", "baseline finish", "early finish", "finish")
MILESTONE_NAME_PRIORITY = ("milestone", "gate", "decision point", "phase gate", "task", "activity")


def analyze_schedule_control(
    text: str,
    preview_df: Optional[pd.DataFrame],
    evm_metrics: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Analyze schedule-control data from uploaded files and EVM context."""

    activity_df, activity_assumptions = extract_activity_table(preview_df)
    cpm = calculate_cpm(activity_df)
    milestones, milestone_assumptions = extract_milestones(text, preview_df)
    s_curve, s_curve_assumptions = build_s_curve(preview_df, evm_metrics)
    forecast, forecast_assumptions = forecast_finish(activity_df, evm_metrics)

    assumptions = activity_assumptions + milestone_assumptions + s_curve_assumptions + forecast_assumptions
    missing = []
    if not cpm["available"]:
        missing.append("activity network with durations and predecessors")
    if milestones.empty:
        missing.append("milestone planned and actual/forecast dates")
    if s_curve.empty:
        missing.append("time-phased PV, EV, AC data")
    if not forecast["available"]:
        missing.append("baseline dates and SPI")

    return {
        "activities": activity_df,
        "critical_path": cpm["critical_path"],
        "float_table": cpm["float_table"],
        "milestones": milestones,
        "s_curve": s_curve,
        "forecast": forecast,
        "traffic_light": schedule_traffic(cpm, milestones, forecast, evm_metrics),
        "assumptions": assumptions,
        "missing_data": missing,
        "available": cpm["available"] or not milestones.empty or not s_curve.empty or forecast["available"],
    }


def extract_activity_table(preview_df: Optional[pd.DataFrame]) -> Tuple[pd.DataFrame, List[str]]:
    """Extract activity records from a CSV/XLSX preview when schedule columns exist."""

    assumptions: List[str] = []
    if preview_df is None or preview_df.empty:
        return pd.DataFrame(), ["No tabular activity data was available for CPM analysis."]

    columns = {col: _normalize(str(col)) for col in preview_df.columns}
    activity_col = _find_column(columns, ACTIVITY_NAME_PRIORITY)
    start_col = _find_column(columns, START_PRIORITY)
    finish_col = _find_column(columns, FINISH_PRIORITY)
    duration_col = _find_column(columns, DURATION_TERMS)
    predecessor_col = _find_column(columns, PREDECESSOR_TERMS)

    if not activity_col:
        return pd.DataFrame(), ["No activity/task column was detected for CPM analysis."]

    records = []
    for idx, row in preview_df.iterrows():
        name = str(row.get(activity_col, "")).strip()
        if not name or name.lower() == "nan":
            continue
        start = _parse_date(row.get(start_col)) if start_col else None
        finish = _parse_date(row.get(finish_col)) if finish_col else None
        duration = _parse_duration(row.get(duration_col)) if duration_col else None
        if duration is None and start is not None and finish is not None:
            duration = max((finish - start).days, 0)
        predecessors = _parse_predecessors(row.get(predecessor_col)) if predecessor_col else []
        records.append({
            "id": _activity_id(row, idx),
            "activity": name,
            "start": start,
            "finish": finish,
            "duration": duration,
            "predecessors": predecessors,
        })

    if not records:
        return pd.DataFrame(), ["Activity rows could not be parsed from the uploaded table."]

    df = pd.DataFrame(records)
    if predecessor_col is None:
        assumptions.append("No predecessor/dependency column was found, so CPM float cannot be calculated.")
    if df["duration"].isna().any():
        assumptions.append("Some activities are missing duration values.")
    return df, assumptions


def calculate_cpm(activity_df: pd.DataFrame) -> Dict[str, Any]:
    """Calculate CPM ES, EF, LS, LF, and Total Float from activity network data."""

    columns = ["id", "activity", "duration", "predecessors", "ES", "EF", "LS", "LF", "total_float", "is_critical"]
    if activity_df is None or activity_df.empty:
        return {"available": False, "float_table": pd.DataFrame(columns=columns), "critical_path": []}

    df = activity_df.copy()
    if df["duration"].isna().any() or not df["predecessors"].map(bool).any():
        return {"available": False, "float_table": pd.DataFrame(columns=columns), "critical_path": []}

    ids = [str(value) for value in df["id"]]
    id_set = set(ids)
    name_to_id = {_normalize(str(row["activity"])): str(row["id"]) for _, row in df.iterrows()}
    durations = {str(row["id"]): float(row["duration"]) for _, row in df.iterrows()}
    predecessors = {}
    for _, row in df.iterrows():
        act_id = str(row["id"])
        preds = []
        for pred in row["predecessors"]:
            pred_id = str(pred)
            normalized = _normalize(pred_id)
            if pred_id in id_set:
                preds.append(pred_id)
            elif normalized in name_to_id:
                preds.append(name_to_id[normalized])
        predecessors[act_id] = preds

    successors = {act_id: [] for act_id in ids}
    for act_id, preds in predecessors.items():
        for pred in preds:
            if pred in successors:
                successors[pred].append(act_id)

    order = _topological_order(ids, predecessors)
    if len(order) != len(ids):
        return {"available": False, "float_table": pd.DataFrame(columns=columns), "critical_path": []}

    es: Dict[str, float] = {}
    ef: Dict[str, float] = {}
    for act_id in order:
        es[act_id] = max([ef[pred] for pred in predecessors[act_id]] or [0])
        ef[act_id] = es[act_id] + durations[act_id]

    project_duration = max(ef.values()) if ef else 0
    lf: Dict[str, float] = {}
    ls: Dict[str, float] = {}
    for act_id in reversed(order):
        lf[act_id] = min([ls[succ] for succ in successors[act_id]] or [project_duration])
        ls[act_id] = lf[act_id] - durations[act_id]

    rows = []
    critical_path = []
    for _, row in df.iterrows():
        act_id = str(row["id"])
        total_float = min(ls[act_id] - es[act_id], lf[act_id] - ef[act_id])
        is_critical = abs(total_float) < 0.01
        if is_critical:
            critical_path.append(row["activity"])
        rows.append({
            "id": act_id,
            "activity": row["activity"],
            "duration": durations[act_id],
            "predecessors": ", ".join(predecessors[act_id]),
            "ES": round(es[act_id], 2),
            "EF": round(ef[act_id], 2),
            "LS": round(ls[act_id], 2),
            "LF": round(lf[act_id], 2),
            "total_float": round(total_float, 2),
            "is_critical": is_critical,
        })

    return {"available": True, "float_table": pd.DataFrame(rows), "critical_path": critical_path}


def extract_milestones(text: str, preview_df: Optional[pd.DataFrame]) -> Tuple[pd.DataFrame, List[str]]:
    """Extract milestone planned vs actual/forecast dates from table or text."""

    assumptions: List[str] = []
    table = _milestones_from_table(preview_df)
    if not table.empty:
        return table, assumptions

    text_rows = _milestones_from_text(text or "")
    if text_rows:
        return pd.DataFrame(text_rows), assumptions

    return pd.DataFrame(columns=["milestone", "planned_date", "actual_or_forecast_date", "slippage_days", "status"]), [
        "No milestone planned vs actual/forecast date pairs were detected."
    ]


def build_s_curve(preview_df: Optional[pd.DataFrame], evm_metrics: Optional[Dict[str, Any]]) -> Tuple[pd.DataFrame, List[str]]:
    """Build cumulative PV/EV/AC S-curve data from time-phased data or current EVM totals."""

    assumptions: List[str] = []
    table = _s_curve_from_table(preview_df)
    if not table.empty:
        return table, assumptions

    values = (evm_metrics or {}).get("values", {})
    pv, ev, ac = values.get("pv"), values.get("ev"), values.get("ac")
    if all(value is not None for value in (pv, ev, ac)):
        assumptions.append("S-curve uses start-to-current cumulative values from available EVM totals because no time-phased PV/EV/AC table was found.")
        return pd.DataFrame([
            {"period": "Start", "PV": 0, "EV": 0, "AC": 0},
            {"period": "Current", "PV": pv, "EV": ev, "AC": ac},
        ]), assumptions

    return pd.DataFrame(columns=["period", "PV", "EV", "AC"]), [
        "No time-phased PV, EV, and AC data was available for S-curve analysis."
    ]


def forecast_finish(activity_df: pd.DataFrame, evm_metrics: Optional[Dict[str, Any]]) -> Tuple[Dict[str, Any], List[str]]:
    """Forecast finish date using baseline dates and SPI when sufficient data exists."""

    assumptions: List[str] = []
    values = (evm_metrics or {}).get("values", {})
    spi = values.get("spi")
    if activity_df is None or activity_df.empty or spi in (None, 0):
        return {
            "available": False,
            "baseline_finish": None,
            "forecast_finish": None,
            "forecast_delay_days": None,
            "method": "Not enough schedule data",
        }, ["Forecast finish requires baseline start/finish dates and SPI."]

    starts = [value for value in activity_df.get("start", []) if pd.notna(value)]
    finishes = [value for value in activity_df.get("finish", []) if pd.notna(value)]
    if not starts or not finishes:
        return {
            "available": False,
            "baseline_finish": None,
            "forecast_finish": None,
            "forecast_delay_days": None,
            "method": "Not enough schedule data",
        }, ["Forecast finish requires parsed baseline activity start and finish dates."]

    baseline_start = min(starts)
    baseline_finish = max(finishes)
    baseline_duration = max((baseline_finish - baseline_start).days, 0)
    if baseline_duration == 0:
        return {
            "available": False,
            "baseline_finish": baseline_finish,
            "forecast_finish": None,
            "forecast_delay_days": None,
            "method": "Not enough schedule data",
        }, ["Baseline duration is zero, so SPI-based finish forecasting was not calculated."]

    forecast_duration = baseline_duration / spi
    forecast_finish_date = baseline_start + timedelta(days=round(forecast_duration))
    delay_days = (forecast_finish_date - baseline_finish).days
    assumptions.append("Forecast finish uses SPI-based duration projection: Forecast Duration = Baseline Duration / SPI.")
    return {
        "available": True,
        "baseline_finish": baseline_finish,
        "forecast_finish": forecast_finish_date,
        "forecast_delay_days": delay_days,
        "method": "Forecast Duration = Baseline Duration / SPI",
    }, assumptions


def schedule_to_ai_context(schedule_metrics: Dict[str, Any]) -> Dict[str, Any]:
    float_table = schedule_metrics.get("float_table", pd.DataFrame())
    milestones = schedule_metrics.get("milestones", pd.DataFrame())
    s_curve = schedule_metrics.get("s_curve", pd.DataFrame())
    return {
        "critical_path": schedule_metrics.get("critical_path", []),
        "float_summary": _records_for_ai(float_table, ["activity", "total_float", "is_critical"]),
        "milestone_slippage": _records_for_ai(milestones, ["milestone", "slippage_days", "status"]),
        "s_curve_points": _records_for_ai(s_curve, ["period", "PV", "EV", "AC"]),
        "forecast": _serialize_dates(schedule_metrics.get("forecast", {})),
        "traffic_light": schedule_metrics.get("traffic_light"),
        "assumptions": schedule_metrics.get("assumptions", []),
        "missing_data": schedule_metrics.get("missing_data", []),
    }


def schedule_traffic(cpm: Dict[str, Any], milestones: pd.DataFrame, forecast: Dict[str, Any], evm_metrics: Optional[Dict[str, Any]]) -> str:
    spi = ((evm_metrics or {}).get("values") or {}).get("spi")
    delayed_milestones = 0
    if milestones is not None and not milestones.empty and "status" in milestones.columns:
        delayed_milestones = int((milestones["status"] == "Delayed").sum())
    forecast_delay = forecast.get("forecast_delay_days")
    if spi is not None and spi < 0.9:
        return "red"
    if delayed_milestones > 0:
        return "red"
    if forecast_delay is not None and forecast_delay > 0:
        return "yellow" if forecast_delay <= 14 else "red"
    if spi is not None and spi < 1:
        return "yellow"
    if cpm.get("available") or spi is not None:
        return "green"
    return "gray"


def _milestones_from_table(preview_df: Optional[pd.DataFrame]) -> pd.DataFrame:
    if preview_df is None or preview_df.empty:
        return pd.DataFrame()
    columns = {col: _normalize(str(col)) for col in preview_df.columns}
    milestone_col = _find_column(columns, MILESTONE_NAME_PRIORITY)
    planned_col = _find_column(columns, PLANNED_DATE_TERMS)
    actual_col = _find_column(columns, ACTUAL_DATE_TERMS)
    if not milestone_col or not planned_col or not actual_col:
        return pd.DataFrame()
    rows = []
    for _, row in preview_df.iterrows():
        name = str(row.get(milestone_col, "")).strip()
        planned = _parse_date(row.get(planned_col))
        actual = _parse_date(row.get(actual_col))
        if not name or planned is None or actual is None:
            continue
        slippage = (actual - planned).days
        rows.append({
            "milestone": name,
            "planned_date": planned.date().isoformat(),
            "actual_or_forecast_date": actual.date().isoformat(),
            "slippage_days": slippage,
            "status": _milestone_status(slippage),
        })
    return pd.DataFrame(rows)


def _milestones_from_text(text: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    pattern = re.compile(
        r"(?P<name>[A-Za-z][A-Za-z0-9 \-/]{2,60})"
        r".{0,40}?(?:planned|baseline|target)\s+(?:date|finish)?\s*:?\s*(?P<planned>\d{4}-\d{1,2}-\d{1,2}|\d{1,2}/\d{1,2}/\d{2,4})"
        r".{0,60}?(?:actual|forecast|expected)\s+(?:date|finish)?\s*:?\s*(?P<actual>\d{4}-\d{1,2}-\d{1,2}|\d{1,2}/\d{1,2}/\d{2,4})",
        re.IGNORECASE,
    )
    for match in pattern.finditer(text):
        planned = _parse_date(match.group("planned"))
        actual = _parse_date(match.group("actual"))
        if planned is None or actual is None:
            continue
        slippage = (actual - planned).days
        rows.append({
            "milestone": match.group("name").strip(),
            "planned_date": planned.date().isoformat(),
            "actual_or_forecast_date": actual.date().isoformat(),
            "slippage_days": slippage,
            "status": _milestone_status(slippage),
        })
    return rows


def _s_curve_from_table(preview_df: Optional[pd.DataFrame]) -> pd.DataFrame:
    if preview_df is None or preview_df.empty:
        return pd.DataFrame()
    columns = {col: _normalize(str(col)) for col in preview_df.columns}
    date_col = _find_column(columns, DATE_TERMS)
    pv_col = _find_column(columns, PV_TERMS)
    ev_col = _find_column(columns, EV_TERMS)
    ac_col = _find_column(columns, AC_TERMS)
    if not all([date_col, pv_col, ev_col, ac_col]):
        return pd.DataFrame()
    df = preview_df[[date_col, pv_col, ev_col, ac_col]].copy()
    df.columns = ["period", "PV", "EV", "AC"]
    for col in ("PV", "EV", "AC"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["PV", "EV", "AC"])
    if df.empty:
        return pd.DataFrame()
    parsed_period = pd.to_datetime(df["period"], errors="coerce")
    if parsed_period.notna().any():
        df["_period_sort"] = parsed_period
        df = df.sort_values("_period_sort").drop(columns=["_period_sort"])
        df["period"] = pd.to_datetime(df["period"], errors="coerce").dt.strftime("%Y-%m-%d").fillna(df["period"].astype(str))
    cumulative_named = any("cum" in columns.get(col, "") or "cumulative" in columns.get(col, "") for col in (pv_col, ev_col, ac_col))
    if not cumulative_named:
        df[["PV", "EV", "AC"]] = df[["PV", "EV", "AC"]].cumsum()
    return df[["period", "PV", "EV", "AC"]]


def _find_column(columns: Dict[Any, str], terms: Tuple[str, ...]) -> Optional[Any]:
    for term in terms:
        for original, normalized in columns.items():
            if term in normalized:
                return original
    return None


def _activity_id(row: pd.Series, idx: int) -> str:
    for key in ("id", "ID", "Activity ID", "activity_id", "WBS", "wbs"):
        if key in row and pd.notna(row.get(key)):
            return str(row.get(key)).strip()
    return str(idx + 1)


def _parse_date(value: Any) -> Optional[pd.Timestamp]:
    if value is None or pd.isna(value):
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed


def _parse_duration(value: Any) -> Optional[float]:
    if value is None or pd.isna(value):
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", str(value))
    if not match:
        return None
    number = float(match.group(0))
    return number if number >= 0 else None


def _parse_predecessors(value: Any) -> List[str]:
    if value is None or pd.isna(value):
        return []
    text = str(value).strip()
    if not text or text.lower() in ("nan", "none", "-"):
        return []
    return [part.strip() for part in re.split(r"[,;/|]+", text) if part.strip()]


def _topological_order(ids: List[str], predecessors: Dict[str, List[str]]) -> List[str]:
    remaining = set(ids)
    order: List[str] = []
    while remaining:
        ready = sorted([act_id for act_id in remaining if all(pred in order or pred not in remaining for pred in predecessors[act_id])])
        if not ready:
            break
        for act_id in ready:
            order.append(act_id)
            remaining.remove(act_id)
    return order


def _milestone_status(slippage: int) -> str:
    if slippage <= 0:
        return "On Time"
    if slippage <= 7:
        return "At Risk"
    return "Delayed"


def _records_for_ai(df: pd.DataFrame, columns: List[str]) -> List[Dict[str, Any]]:
    if df is None or df.empty:
        return []
    existing = [column for column in columns if column in df.columns]
    return _serialize_dates(df[existing].head(12).to_dict("records"))


def _serialize_dates(value: Any) -> Any:
    if isinstance(value, list):
        return [_serialize_dates(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize_dates(item) for key, item in value.items()}
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    return value


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("_", " ").replace("-", " ")).strip().lower()
