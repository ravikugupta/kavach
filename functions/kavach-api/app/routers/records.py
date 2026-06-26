from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, HTTPException
from app.db import query, query_one

router = APIRouter(prefix="/api/records", tags=["records"])


@router.get("/fir")
def list_firs(city: Optional[str] = None, crime_type: Optional[str] = None, status: Optional[str] = None, limit: int = 50):
    sql = """
        SELECT f.fir_id, f.crime_type, f.date_filed, f.status, l.area_name, l.city
        FROM fir f JOIN locations l ON f.location_id = l.location_id
    """
    conditions, params = [], []
    if city:
        conditions.append("l.city = ?")
        params.append(city)
    if crime_type:
        conditions.append("f.crime_type = ?")
        params.append(crime_type)
    if status:
        conditions.append("f.status = ?")
        params.append(status)
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY f.date_filed DESC LIMIT ?"
    params.append(limit)
    return {"results": query(sql, tuple(params))}


@router.get("/fir/{fir_id}")
def get_fir(fir_id: str):
    fir = query_one("""SELECT f.*, l.area_name, l.city FROM fir f
                        JOIN locations l ON f.location_id = l.location_id
                        WHERE f.fir_id=?""", (fir_id,))
    if not fir:
        raise HTTPException(status_code=404, detail="FIR not found")

    accused = query(
        """SELECT a.accused_id, a.name, a.age, a.gender, fa.role FROM fir_accused fa
           JOIN accused a ON fa.accused_id = a.accused_id WHERE fa.fir_id=?""", (fir_id,)
    )
    victims = query(
        """SELECT v.victim_id, v.name, v.age, v.gender FROM fir_victims fv
           JOIN victims v ON fv.victim_id = v.victim_id WHERE fv.fir_id=?""", (fir_id,)
    )
    return {"fir": fir, "accused": accused, "victims": victims}


@router.get("/accused")
def list_accused(min_risk: float = 0.0, limit: int = 50):
    rows = query(
        "SELECT accused_id, name, age, gender, prior_offenses, risk_score FROM accused "
        "WHERE risk_score >= ? ORDER BY risk_score DESC LIMIT ?",
        (min_risk, limit)
    )
    return {"results": rows}


@router.get("/accused/{accused_id}")
def get_accused(accused_id: int):
    row = query_one("SELECT * FROM accused WHERE accused_id=?", (accused_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Accused not found")
    return row


@router.get("/meta/cities")
def cities():
    rows = query("SELECT DISTINCT city FROM locations ORDER BY city")
    return {"cities": [r["city"] for r in rows]}


@router.get("/meta/crime-types")
def crime_types():
    rows = query("SELECT DISTINCT crime_type FROM fir ORDER BY crime_type")
    return {"crime_types": [r["crime_type"] for r in rows]}
