"""PMBOK Earned Value Management extraction and calculation engine.

This module is intentionally independent from the rule-based risk engine.
It extracts source control data from project documents, calculates standard
Earned Value Management metrics, and records confidence/missing-data context.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd


SOURCE_FIELDS = ("bac", "ac", "planned_percent", "actual_percent")

FIELD_LABELS = {
    "bac": "BAC",
    "ac": "AC",
    "planned_percent": "Planned %",
    "actual_percent": "Actual %",
}

FIELD_TERMS = {
    "bac": (
        "budget at completion",
        "approved budget",
        "project budget",
        "total budget",
        "baseline budget",
        "authorized budget",
        "approved cost",
        "contract value",
        "total project cost",
        "budget",
        "bac",
    ),
    "ac": (
        "actual cost",
        "actual costs",
        "cost incurred",
        "costs incurred",
        "current spending",
        "money spent",
        "spent to date",
        "expenditure",
        "actual expenditure",
        "actual spend",
        "cost to date",
        "incurred cost",
        "ac",
    ),
    "planned_percent": (
        "planned progress",
        "planned completion",
        "baseline progress",
        "planned percent",
        "planned percentage",
        "baseline completion",
        "planned % complete",
        "scheduled progress",
        "schedule baseline",
        "planned complete",
    ),
    "actual_percent": (
        "actual progress",
        "physical progress",
        "work completed",
        "percent complete",
        "% complete",
        "actual completion",
        "actual percent",
        "actual percentage",
        "progress to date",
        "completed work",
        "actual complete",
    ),
}

NEGATIVE_CONTEXT = {
    "bac": ("actual", "spent", "incurred", "to date", "variance", "overrun"),
    "ac": ("budget at completion", "approved budget", "planned", "baseline", "bac"),
    "planned_percent": ("actual", "physical", "completed", "work completed"),
    "actual_percent": ("planned", "baseline", "scheduled"),
}

CURRENCY_PATTERN = re.compile(
    r"(?:(?:SAR|AED|USD|US\$|\$|ر\.س|ريال)\s*)?"
    r"(?P<number>\(?-?\d[\d,]*(?:\.\d+)?)"
    r"\s*(?P<scale>million|m|thousand|k|mn)?"
    r"(?:\s*(?:SAR|AED|USD|US\$|\$|ر\.س|ريال))?",
    re.IGNORECASE,
)

PERCENT_PATTERN = re.compile(
    r"(?P<number>\d{1,3}(?:\.\d+)?)\s*(?:%|percent|percentage|pct)",
    re.IGNORECASE,
)


@dataclass
class Candidate:
    field: str
    value: float
    confidence: float
    evidence: str
    method: str


def blank_source_data() -> Dict[str, Dict[str, Any]]:
    """Return a stable source-data shape for every EVM input field."""

    return {
        field: {
            "value": None,
            "confidence": 0.0,
            "evidence": "",
            "source": "missing",
            "method": "not_found",
        }
        for field in SOURCE_FIELDS
    }


def normalize_percent(value: Any) -> Optional[float]:
    """Convert percent-like values to a 0..1 decimal."""

    number = _to_float(value)
    if number is None:
        return None
    if number < 0:
        return None
    if number > 1:
        number = number / 100
    return min(number, 1.5)


def normalize_amount(value: Any) -> Optional[float]:
    number = _to_float(value)
    if number is None or number < 0:
        return None
    return number


def merge_source_data(
    primary: Dict[str, Dict[str, Any]], secondary: Optional[Dict[str, Dict[str, Any]]]
) -> Dict[str, Dict[str, Any]]:
    """Merge extracted source fields, keeping the highest-confidence value."""

    merged = blank_source_data()
    for field in SOURCE_FIELDS:
        first = primary.get(field, {})
        second = (secondary or {}).get(field, {})
        first_conf = float(first.get("confidence") or 0)
        second_conf = float(second.get("confidence") or 0)
        merged[field] = second if second_conf > first_conf else first
        if not merged[field]:
            merged[field] = blank_source_data()[field]
    return merged


def extract_evm_source_data(
    text: str, preview_df: Optional[pd.DataFrame] = None
) -> Dict[str, Dict[str, Any]]:
    """Extract BAC, AC, planned %, and actual % with confidence metadata.

    The extractor combines contextual text scanning with table/column scanning.
    It does not fabricate missing source values.
    """

    source_data = blank_source_data()
    text_candidates = _extract_from_text(text or "")
    table_candidates = _extract_from_table(preview_df)

    for candidate in text_candidates + table_candidates:
        current = source_data[candidate.field]
        if candidate.confidence > float(current.get("confidence") or 0):
            source_data[candidate.field] = {
                "value": candidate.value,
                "confidence": round(candidate.confidence, 2),
                "evidence": candidate.evidence[:260],
                "source": "document",
                "method": candidate.method,
            }

    return source_data


def calculate_evm_metrics(source_data: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate standard PMBOK Earned Value Management metrics."""

    bac = normalize_amount(_field_value(source_data, "bac"))
    ac = normalize_amount(_field_value(source_data, "ac"))
    planned_percent = normalize_percent(_field_value(source_data, "planned_percent"))
    actual_percent = normalize_percent(_field_value(source_data, "actual_percent"))

    pv = _safe_multiply(bac, planned_percent)
    ev = _safe_multiply(bac, actual_percent)
    sv = _safe_subtract(ev, pv)
    cv = _safe_subtract(ev, ac)
    spi = _safe_divide(ev, pv)
    cpi = _safe_divide(ev, ac)

    eac, eac_formula = _calculate_eac(bac=bac, ac=ac, ev=ev, cpi=cpi, spi=spi)
    etc = _safe_subtract(eac, ac)
    vac = _safe_subtract(bac, eac)
    tcpi, tcpi_formula = _calculate_tcpi(bac=bac, ev=ev, ac=ac, eac=eac)
    percent_complete = actual_percent if actual_percent is not None else _safe_divide(ev, bac)

    missing_sources = [
        FIELD_LABELS[field]
        for field in SOURCE_FIELDS
        if _field_value(source_data, field) is None
    ]
    assumptions = _build_assumptions(source_data, eac_formula, tcpi_formula)

    values = {
        "bac": bac,
        "pv": pv,
        "ev": ev,
        "ac": ac,
        "sv": sv,
        "cv": cv,
        "spi": spi,
        "cpi": cpi,
        "eac": eac,
        "etc": etc,
        "vac": vac,
        "tcpi": tcpi,
        "percent_complete": percent_complete,
        "planned_percent": planned_percent,
        "actual_percent": actual_percent,
    }

    complete_core = all(values[key] is not None for key in ("pv", "ev", "ac"))

    return {
        "source_data": source_data,
        "values": values,
        "formulas": {
            "pv": "PV = BAC x Planned %",
            "ev": "EV = BAC x Actual %",
            "sv": "SV = EV - PV",
            "cv": "CV = EV - AC",
            "spi": "SPI = EV / PV",
            "cpi": "CPI = EV / AC",
            "eac": eac_formula,
            "etc": "ETC = EAC - AC" if eac is not None and ac is not None else None,
            "vac": "VAC = BAC - EAC" if bac is not None and eac is not None else None,
            "tcpi": tcpi_formula,
            "percent_complete": "Percent Complete = Actual % or EV / BAC",
        },
        "traffic_lights": {
            "schedule": _schedule_traffic(spi),
            "cost": _cost_traffic(cpi),
            "forecast": _forecast_traffic(vac),
            "tcpi": _tcpi_traffic(tcpi),
        },
        "interpretation": {
            "schedule": _schedule_interpretation(spi),
            "cost": _cost_interpretation(cpi),
            "forecast": _forecast_interpretation(vac),
            "tcpi": _tcpi_interpretation(tcpi),
        },
        "missing_sources": missing_sources,
        "assumptions": assumptions,
        "complete_core": complete_core,
        "available": any(value is not None for value in values.values()),
    }


def evm_to_ai_context(evm_metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Create a compact JSON-serializable EVM context for the LLM prompt."""

    values = evm_metrics.get("values", {})
    return {
        "values": {key: _round_value(value) for key, value in values.items()},
        "traffic_lights": evm_metrics.get("traffic_lights", {}),
        "interpretation": evm_metrics.get("interpretation", {}),
        "missing_sources": evm_metrics.get("missing_sources", []),
        "assumptions": evm_metrics.get("assumptions", []),
        "formulas": evm_metrics.get("formulas", {}),
        "complete_core": evm_metrics.get("complete_core", False),
    }


def format_currency(value: Optional[float]) -> str:
    if value is None:
        return "Not available"
    return f"{value:,.0f}"


def format_index(value: Optional[float]) -> str:
    if value is None:
        return "Not available"
    return f"{value:.2f}"


def format_percent(value: Optional[float]) -> str:
    if value is None:
        return "Not available"
    return f"{value * 100:.1f}%"


def _extract_from_text(text: str) -> List[Candidate]:
    normalized = _normalize_text(text)
    candidates: List[Candidate] = []

    for match in CURRENCY_PATTERN.finditer(normalized):
        amount = _amount_from_match(match)
        if amount is None:
            continue
        window = _window(normalized, match.start(), match.end(), radius=130)
        score_window = _score_window(normalized, match.start(), match.end())
        for field in ("bac", "ac"):
            score = _context_score(field, score_window)
            if score > 0:
                candidates.append(
                    Candidate(
                        field=field,
                        value=amount,
                        confidence=min(0.95, 0.42 + score * 0.1),
                        evidence=window.strip(),
                        method="contextual_currency_scan",
                    )
                )

    for match in PERCENT_PATTERN.finditer(normalized):
        percent = normalize_percent(match.group("number"))
        if percent is None:
            continue
        window = _window(normalized, match.start(), match.end(), radius=130)
        score_window = _score_window(normalized, match.start(), match.end())
        for field in ("planned_percent", "actual_percent"):
            score = _context_score(field, score_window)
            if score > 0:
                candidates.append(
                    Candidate(
                        field=field,
                        value=percent,
                        confidence=min(0.95, 0.42 + score * 0.1),
                        evidence=window.strip(),
                        method="contextual_percent_scan",
                    )
                )

    return candidates


def _extract_from_table(preview_df: Optional[pd.DataFrame]) -> List[Candidate]:
    if preview_df is None or preview_df.empty:
        return []

    candidates: List[Candidate] = []
    rows = preview_df.head(40)

    for column in rows.columns:
        column_text = _normalize_text(str(column))
        field = _field_from_context(column_text)
        if field:
            for value in rows[column].dropna().head(8):
                parsed = (
                    normalize_percent(value)
                    if field.endswith("percent")
                    else normalize_amount(value)
                )
                if parsed is None:
                    parsed = _parse_value_from_text(str(value), percent=field.endswith("percent"))
                if parsed is not None:
                    candidates.append(
                        Candidate(
                            field=field,
                            value=parsed,
                            confidence=0.82,
                            evidence=f"{column}: {value}",
                            method="table_column_scan",
                        )
                    )
                    break

    for _, row in rows.iterrows():
        row_text = _normalize_text(" ".join(str(value) for value in row.values if pd.notna(value)))
        field = _field_from_context(row_text)
        if not field:
            continue
        parsed = _parse_value_from_text(row_text, percent=field.endswith("percent"))
        if parsed is not None:
            candidates.append(
                Candidate(
                    field=field,
                    value=parsed,
                    confidence=0.74,
                    evidence=row_text[:260],
                    method="table_row_scan",
                )
            )

    return candidates


def _field_from_context(context: str) -> Optional[str]:
    scores = {field: _context_score(field, context) for field in SOURCE_FIELDS}
    best_field, best_score = max(scores.items(), key=lambda item: item[1])
    return best_field if best_score > 0 else None


def _context_score(field: str, context: str) -> int:
    score = 0
    for term in FIELD_TERMS[field]:
        if term in context:
            score += 2 if " " in term else 1
    for term in NEGATIVE_CONTEXT.get(field, ()):
        if term in context:
            score -= 1
    return max(score, 0)


def _parse_value_from_text(text: str, percent: bool) -> Optional[float]:
    pattern = PERCENT_PATTERN if percent else CURRENCY_PATTERN
    matches = list(pattern.finditer(text))
    if not matches:
        return None
    if percent:
        return normalize_percent(matches[-1].group("number"))
    return _amount_from_match(matches[-1])


def _amount_from_match(match: re.Match[str]) -> Optional[float]:
    raw = match.group("number")
    if raw is None:
        return None
    raw = raw.replace(",", "").replace("(", "-").replace(")", "")
    try:
        number = float(raw)
    except ValueError:
        return None
    scale = (match.group("scale") or "").lower()
    if scale in ("m", "mn", "million"):
        number *= 1_000_000
    elif scale in ("k", "thousand"):
        number *= 1_000
    return normalize_amount(number)


def _build_assumptions(
    source_data: Dict[str, Dict[str, Any]], eac_formula: Optional[str], tcpi_formula: Optional[str]
) -> List[str]:
    assumptions: List[str] = []
    for field in SOURCE_FIELDS:
        item = source_data.get(field, {})
        if item.get("value") is None:
            assumptions.append(f"{FIELD_LABELS[field]} was not found in the uploaded document.")
        elif float(item.get("confidence") or 0) < 0.65:
            assumptions.append(
                f"{FIELD_LABELS[field]} was extracted with low confidence from document context."
            )
    if eac_formula:
        assumptions.append(f"EAC formula selected: {eac_formula}.")
    if tcpi_formula:
        assumptions.append(f"TCPI formula selected: {tcpi_formula}.")
    return assumptions


def _calculate_eac(
    *, bac: Optional[float], ac: Optional[float], ev: Optional[float], cpi: Optional[float], spi: Optional[float]
) -> Tuple[Optional[float], Optional[str]]:
    if bac is None or ac is None or ev is None:
        return None, None

    remaining_work = bac - ev
    if remaining_work < 0:
        remaining_work = 0

    if cpi and spi and cpi > 0 and spi > 0 and cpi < 1 and spi < 1:
        return ac + remaining_work / (cpi * spi), "EAC = AC + (BAC - EV) / (CPI x SPI)"
    if cpi and cpi > 0:
        return bac / cpi, "EAC = BAC / CPI"
    return ac + remaining_work, "EAC = AC + (BAC - EV)"


def _calculate_tcpi(
    *, bac: Optional[float], ev: Optional[float], ac: Optional[float], eac: Optional[float]
) -> Tuple[Optional[float], Optional[str]]:
    if bac is None or ev is None or ac is None:
        return None, None
    if bac - ac > 0:
        return (bac - ev) / (bac - ac), "TCPI = (BAC - EV) / (BAC - AC)"
    if eac is not None and eac - ac > 0:
        return (bac - ev) / (eac - ac), "TCPI = (BAC - EV) / (EAC - AC)"
    return None, None


def _schedule_traffic(spi: Optional[float]) -> str:
    if spi is None:
        return "gray"
    if spi < 0.90:
        return "red"
    if spi < 1.00:
        return "yellow"
    return "green"


def _cost_traffic(cpi: Optional[float]) -> str:
    if cpi is None:
        return "gray"
    if cpi < 0.90:
        return "red"
    if cpi < 1.00:
        return "yellow"
    return "green"


def _forecast_traffic(vac: Optional[float]) -> str:
    if vac is None:
        return "gray"
    if vac < 0:
        return "red"
    if vac == 0:
        return "yellow"
    return "green"


def _tcpi_traffic(tcpi: Optional[float]) -> str:
    if tcpi is None:
        return "gray"
    if tcpi > 1.10:
        return "red"
    if tcpi > 1.00:
        return "yellow"
    return "green"


def _schedule_interpretation(spi: Optional[float]) -> str:
    if spi is None:
        return "Insufficient data to calculate schedule performance."
    if spi < 0.90:
        return "Behind schedule."
    if spi < 1.00:
        return "Slightly behind schedule."
    if spi == 1.00:
        return "On schedule."
    return "Ahead of schedule."


def _cost_interpretation(cpi: Optional[float]) -> str:
    if cpi is None:
        return "Insufficient data to calculate cost performance."
    if cpi < 0.90:
        return "Over budget with material cost pressure."
    if cpi < 1.00:
        return "Slightly over budget."
    if cpi == 1.00:
        return "On budget."
    return "Under budget."


def _forecast_interpretation(vac: Optional[float]) -> str:
    if vac is None:
        return "Insufficient data to calculate variance at completion."
    if vac < 0:
        return "Forecast indicates a cost overrun at completion."
    if vac == 0:
        return "Forecast is aligned to the approved budget."
    return "Forecast indicates underrun against the approved budget."


def _tcpi_interpretation(tcpi: Optional[float]) -> str:
    if tcpi is None:
        return "Insufficient data to calculate required future efficiency."
    if tcpi > 1.10:
        return "Recovery requires aggressive future cost efficiency."
    if tcpi > 1.00:
        return "Recovery requires improved cost efficiency."
    return "Remaining work can be completed within current efficiency expectations."


def _safe_multiply(left: Optional[float], right: Optional[float]) -> Optional[float]:
    if left is None or right is None:
        return None
    return left * right


def _safe_subtract(left: Optional[float], right: Optional[float]) -> Optional[float]:
    if left is None or right is None:
        return None
    return left - right


def _safe_divide(left: Optional[float], right: Optional[float]) -> Optional[float]:
    if left is None or right in (None, 0):
        return None
    return left / right


def _field_value(source_data: Dict[str, Dict[str, Any]], field: str) -> Any:
    return (source_data.get(field) or {}).get("value")


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _window(text: str, start: int, end: int, radius: int) -> str:
    return text[max(0, start - radius) : min(len(text), end + radius)]


def _score_window(text: str, start: int, end: int) -> str:
    left_boundary = max(text.rfind(".", 0, start), text.rfind(";", 0, start), text.rfind("\n", 0, start))
    right_candidates = [idx for idx in (text.find(".", end), text.find(";", end), text.find("\n", end)) if idx != -1]
    right_boundary = min(right_candidates) if right_candidates else len(text)
    left = max(0, left_boundary + 1, start - 90)
    right = min(len(text), right_boundary, end + 90)
    return text[left:right]


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    match = re.search(r"-?\d+(?:,\d{3})*(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", ""))
    except ValueError:
        return None


def _round_value(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 4)
    return value
