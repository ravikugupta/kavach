from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, HTTPException
from app.services import analytics

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/hotspots")
def hotspots(top_n: int = 5):
    return analytics.crime_hotspots(top_n=top_n)


@router.get("/trends")
def trends(
    city: Optional[str] = None,
    crime_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    date_range = (start_date, end_date) if start_date and end_date else None
    return analytics.crime_trends(city=city, crime_type=crime_type, date_range=date_range)


@router.get("/sociological")
def sociological():
    return analytics.sociological_insights()


@router.get("/repeat-offenders")
def repeat_offenders(min_priors: int = 2, top_n: int = 10):
    return analytics.repeat_offenders(min_priors=min_priors, top_n=top_n)


@router.get("/organized-groups")
def organized_groups(min_group_size: int = 3):
    return analytics.detect_organized_groups(min_group_size=min_group_size)


@router.get("/financial-links")
def financial_links(min_amount: float = 100000):
    return analytics.financial_links(min_amount=min_amount)


@router.get("/early-warning")
def early_warning():
    return analytics.early_warning_alerts()


@router.get("/accused/{accused_id}/profile")
def accused_profile(accused_id: int):
    result = analytics.offender_risk_profile(accused_id)
    if not result:
        raise HTTPException(status_code=404, detail="Accused not found")
    return result


@router.get("/accused/{accused_id}/network")
def accused_network(accused_id: int, depth: int = 1):
    result = analytics.accused_network(accused_id, depth=depth)
    if not result:
        raise HTTPException(status_code=404, detail="Accused not found")
    return result


@router.get("/summary")
def summary():
    """Aggregate KPI stats for the dashboard hero cards."""
    return analytics.dashboard_summary()
