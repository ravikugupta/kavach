"""
Forecast router for Kavach.

GET /api/forecast/trends          -> crime trend forecasts (linear regression)
GET /api/forecast/trends?city=... -> filter by city
GET /api/forecast/hotspots        -> hotspot risk scores for next period
"""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends
from app.services import forecast
from app.auth import require_role

router = APIRouter(prefix="/api/forecast", tags=["forecast"])


@router.get("/trends")
def trend_forecast(city: Optional[str] = None):
    """
    Returns per-crime-type linear trend forecasts and predicted next-month counts.
    No authentication required (public insight for awareness).
    """
    return forecast.forecast_crime_trends(city=city)


@router.get("/hotspots")
def hotspot_forecast(top_n: int = 5):
    """
    Returns risk-scored hotspot areas for the upcoming period.
    """
    return forecast.forecast_hotspot_risk(top_n=top_n)
