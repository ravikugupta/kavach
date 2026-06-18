"""
Crime Forecasting Service for Kavach.

Implements simple statistical heuristics to predict near-future crime trends
without requiring any ML model training — suitable for a demo prototype that
must run offline.

Approach
--------
1. Compute monthly case counts per crime type.
2. Fit a linear trend (least-squares) over the last N months.
3. Extrapolate one month ahead and flag positive slopes as "rising".
4. Identify top rising crime types and top hotspot areas to produce
   actionable early-forecast alerts.

In production this module would be replaced by a trained SARIMA / LSTM model.
Every output includes an 'evidence' / 'methodology' field to satisfy the
Explainable AI requirement.
"""
from __future__ import annotations
from typing import Optional, List
from collections import Counter, defaultdict
from app.db import query


def _linear_trend(values: List[float]):
    """
    Return (slope, intercept) of a simple least-squares linear fit
    over the index range [0, len(values)-1].
    """
    n = len(values)
    if n < 2:
        return 0.0, values[0] if values else 0.0
    xs = list(range(n))
    mx = sum(xs) / n
    my = sum(values) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, values))
    den = sum((x - mx) ** 2 for x in xs)
    slope = num / den if den else 0.0
    intercept = my - slope * mx
    return slope, intercept


def forecast_crime_trends(city: Optional[str] = None, months_ahead: int = 1):
    """
    Forecast monthly crime counts for the next `months_ahead` months.

    Returns a dict with:
      - 'forecasts': list of {crime_type, historical_monthly, predicted_next_month, trend}
      - 'top_rising': list of crime types with steepest upward trend
      - 'evidence': explanation of the methodology
    """
    sql = """
        SELECT f.crime_type, f.date_filed, l.city
        FROM fir f
        JOIN locations l ON f.location_id = l.location_id
    """
    params: list = []
    if city:
        sql += " WHERE l.city = ?"
        params.append(city)

    rows = query(sql, tuple(params))

    # Aggregate by crime_type -> sorted monthly counts
    by_type_month: dict = defaultdict(Counter)
    all_months: set = set()
    for r in rows:
        month = r["date_filed"][:7]  # YYYY-MM
        by_type_month[r["crime_type"]][month] += 1
        all_months.add(month)

    sorted_months = sorted(all_months)

    forecasts = []
    for crime_type, monthly in by_type_month.items():
        # Fill zeros for missing months to get a uniform time-series
        counts = [monthly.get(m, 0) for m in sorted_months]
        slope, intercept = _linear_trend(counts)

        # Predicted next-month count (clamped to 0)
        predicted = max(0, round(intercept + slope * len(counts)))

        forecasts.append({
            "crime_type": crime_type,
            "historical_monthly": dict(zip(sorted_months, counts)),
            "trend_slope": round(slope, 3),
            "predicted_next_month": predicted,
            "trend": "rising" if slope > 0.5 else ("stable" if slope > -0.5 else "declining"),
        })

    forecasts.sort(key=lambda x: x["trend_slope"], reverse=True)
    top_rising = [f["crime_type"] for f in forecasts if f["trend"] == "rising"][:5]

    return {
        "city_filter": city or "all",
        "months_modelled": len(sorted_months),
        "forecasts": forecasts,
        "top_rising_crime_types": top_rising,
        "evidence": (
            f"Linear regression over {len(sorted_months)} months of FIR data"
            + (f" filtered to city='{city}'" if city else "")
            + ". Each crime type's trend slope is computed via least-squares. "
            "A positive slope >0.5 cases/month indicates a rising trend. "
            "Predicted next month = intercept + slope * (current_month_index + 1). "
            "This is a heuristic model; production systems should use SARIMA/LSTM."
        ),
    }


def forecast_hotspot_risk(top_n: int = 5):
    """
    Score each location for near-future risk based on recent case velocity.

    Risk score = (cases in last 3 months) / (total cases) weighted by total volume.
    """
    rows = query("""
        SELECT l.location_id, l.area_name, l.city, f.date_filed
        FROM fir f
        JOIN locations l ON f.location_id = l.location_id
        ORDER BY f.date_filed DESC
    """)

    all_months = sorted({r["date_filed"][:7] for r in rows})
    recent_cutoff = all_months[-3] if len(all_months) >= 3 else (all_months[0] if all_months else "")

    loc_total: Counter = Counter()
    loc_recent: Counter = Counter()

    for r in rows:
        key = (r["location_id"], r["area_name"], r["city"])
        loc_total[key] += 1
        if r["date_filed"][:7] >= recent_cutoff:
            loc_recent[key] += 1

    total_cases = sum(loc_total.values()) or 1

    scored = []
    for key, total in loc_total.most_common():
        loc_id, area, city = key
        recent = loc_recent.get(key, 0)
        velocity_ratio = recent / max(total, 1)
        risk = round((total / total_cases) * 0.6 + velocity_ratio * 0.4, 4)
        scored.append({
            "location_id": loc_id,
            "area_name": area,
            "city": city,
            "total_cases": total,
            "recent_cases_3m": recent,
            "risk_score": risk,
            "risk_level": "HIGH" if risk > 0.08 else ("MEDIUM" if risk > 0.04 else "LOW"),
        })

    scored.sort(key=lambda x: x["risk_score"], reverse=True)
    return {
        "hotspot_forecast": scored[:top_n],
        "evidence": (
            f"Risk score = 0.6 × (location case share) + 0.4 × (recent 3-month velocity). "
            f"Modelled from {len(rows)} FIRs. "
            f"Threshold: HIGH > 0.08, MEDIUM > 0.04, LOW ≤ 0.04."
        ),
    }
