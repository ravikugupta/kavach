"""
Analytics services for Kavach: crime pattern, network, risk profiling,
sociological insights and basic forecasting.

These are intentionally simple, explainable implementations suitable for a
hackathon prototype -- each function returns both a result and a short
'evidence' / 'explanation' string so the conversational layer can cite its
reasoning (per the Explainable AI requirement).
"""

from __future__ import annotations
from typing import Optional
from collections import Counter, defaultdict
from app.db import query, query_one


# ---------------------------------------------------------------------------
# Crime pattern & trend analytics
# ---------------------------------------------------------------------------

def crime_trends(
    city: Optional[str] = None,
    crime_type: Optional[str] = None,
    date_range: Optional[tuple[str, str]] = None,
):
    """date_range: (start_date_str, end_date_str) in 'YYYY-MM-DD' format"""
    sql = """
        SELECT f.crime_type, f.date_filed, l.city, l.area_name
        FROM fir f
        JOIN locations l ON f.location_id = l.location_id
    """
    conditions = []
    params = []
    if city:
        conditions.append("l.city = ?")
        params.append(city)
    if crime_type:
        conditions.append("f.crime_type = ?")
        params.append(crime_type)
    if date_range:
        start, end = date_range
        conditions.append("date(f.date_filed) >= date(?)")
        conditions.append("date(f.date_filed) <= date(?)")
        params.extend([start, end])
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    rows = query(sql, tuple(params))

    by_type = Counter(r["crime_type"] for r in rows)
    by_month = Counter(r["date_filed"][:7] for r in rows)  # YYYY-MM
    by_city = Counter(r["city"] for r in rows)

    return {
        "total_cases": len(rows),
        "by_crime_type": dict(by_type.most_common()),
        "by_month": dict(sorted(by_month.items())),
        "by_city": dict(by_city.most_common()),
        "evidence": f"Computed from {len(rows)} FIR records"
                    + (f" filtered by city='{city}'" if city else "")
                    + (f" and crime_type='{crime_type}'" if crime_type else "")
                    + (f" for date range {date_range[0]} to {date_range[1]}" if date_range else "")
                    + ".",
    }


def crime_hotspots(top_n: int = 5):
    sql = """
        SELECT l.area_name, l.city, l.latitude, l.longitude, COUNT(*) as case_count
        FROM fir f
        JOIN locations l ON f.location_id = l.location_id
        GROUP BY l.location_id
        ORDER BY case_count DESC
        LIMIT ?
    """
    rows = query(sql, (top_n,))
    return {
        "hotspots": rows,
        "evidence": f"Top {top_n} locations ranked by total FIR count across all crime types.",
    }


# ---------------------------------------------------------------------------
# Criminal network analysis
# ---------------------------------------------------------------------------

def accused_network(accused_id: int, depth: int = 1):
    """
    Returns the immediate network (co-accused, victims, locations) for a
    given accused person, with simple BFS expansion for `depth` hops.
    """
    accused = query_one("SELECT * FROM accused WHERE accused_id = ?", (accused_id,))
    if not accused:
        return None

    nodes = {f"accused:{accused_id}": {"type": "accused", "id": accused_id, "label": accused["name"]}}
    edges = []
    frontier = [accused_id]
    visited_accused = {accused_id}

    for _ in range(depth):
        next_frontier = []
        for acc_id in frontier:
            links = query(
                """SELECT * FROM crime_links
                   WHERE (source_type='accused' AND source_id=?)
                      OR (target_type='accused' AND target_id=?)""",
                (str(acc_id), str(acc_id))
            )
            for link in links:
                # normalize so 'this' accused is always the source
                if link["source_type"] == "accused" and link["source_id"] == str(acc_id):
                    other_type, other_id, relation = link["target_type"], link["target_id"], link["relation"]
                else:
                    other_type, other_id, relation = link["source_type"], link["source_id"], link["relation"]

                node_key = f"{other_type}:{other_id}"
                if node_key not in nodes:
                    label = _label_for(other_type, other_id)
                    nodes[node_key] = {"type": other_type, "id": other_id, "label": label}

                edges.append({"source": f"accused:{acc_id}", "target": node_key, "relation": relation})

                if other_type == "accused":
                    oid = int(other_id)
                    if oid not in visited_accused:
                        visited_accused.add(oid)
                        next_frontier.append(oid)
        frontier = next_frontier

    return {
        "root_accused": {"id": accused["accused_id"], "name": accused["name"], "risk_score": accused["risk_score"]},
        "nodes": list(nodes.values()),
        "edges": edges,
        "evidence": f"Network expanded to {depth} hop(s) from accused #{accused_id} using the crime_links graph table "
                    f"({len(nodes)} entities, {len(edges)} relationships found).",
    }


def _label_for(node_type, node_id):
    if node_type == "accused":
        row = query_one("SELECT name FROM accused WHERE accused_id=?", (node_id,))
        return row["name"] if row else f"Accused #{node_id}"
    if node_type == "victim":
        row = query_one("SELECT name FROM victims WHERE victim_id=?", (node_id,))
        return row["name"] if row else f"Victim #{node_id}"
    if node_type == "location":
        row = query_one("SELECT area_name, city FROM locations WHERE location_id=?", (node_id,))
        return f"{row['area_name']}, {row['city']}" if row else f"Location #{node_id}"
    return f"{node_type} #{node_id}"


def detect_organized_groups(min_group_size: int = 3):
    """
    Very simple group detection: clusters accused who share >=1 co_accused
    link, using union-find over the crime_links table.
    """
    links = query("SELECT * FROM crime_links WHERE relation='co_accused'")

    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for link in links:
        a, b = link["source_id"], link["target_id"]
        union(a, b)
        find(a)
        find(b)

    groups = defaultdict(set)
    for node in parent:
        groups[find(node)].add(node)

    results = []
    for root, members in groups.items():
        if len(members) >= min_group_size:
            accused_rows = query(
                f"SELECT accused_id, name, risk_score FROM accused WHERE accused_id IN ({','.join(['?']*len(members))})",
                tuple(int(m) for m in members)
            )
            results.append({
                "group_size": len(members),
                "members": accused_rows,
                "avg_risk_score": round(sum(r["risk_score"] for r in accused_rows) / len(accused_rows), 2)
                                  if accused_rows else 0,
            })

    results.sort(key=lambda g: g["group_size"], reverse=True)
    return {
        "groups": results,
        "evidence": f"Detected via union-find clustering over co-accused relationships "
                    f"in crime_links; groups with >= {min_group_size} members shown.",
    }


# ---------------------------------------------------------------------------
# Sociological crime insights
# ---------------------------------------------------------------------------

def sociological_insights():
    accused_rows = query("SELECT economic_background, education_level, gender, age, prior_offenses FROM accused")
    victim_rows = query("SELECT economic_background, gender, age FROM victims")

    econ_dist = Counter(r["economic_background"] for r in accused_rows)
    edu_dist = Counter(r["education_level"] for r in accused_rows)
    gender_dist = Counter(r["gender"] for r in accused_rows)

    age_buckets = Counter()
    for r in accused_rows:
        age = r["age"]
        if age < 21:
            bucket = "18-20"
        elif age < 30:
            bucket = "21-29"
        elif age < 40:
            bucket = "30-39"
        elif age < 50:
            bucket = "40-49"
        else:
            bucket = "50+"
        age_buckets[bucket] += 1

    victim_econ_dist = Counter(r["economic_background"] for r in victim_rows)

    return {
        "accused_economic_background": dict(econ_dist.most_common()),
        "accused_education_level": dict(edu_dist.most_common()),
        "accused_gender_distribution": dict(gender_dist),
        "accused_age_distribution": dict(sorted(age_buckets.items())),
        "victim_economic_background": dict(victim_econ_dist.most_common()),
        "evidence": f"Aggregated over {len(accused_rows)} accused and {len(victim_rows)} victim records. "
                    "Note: prototype dataset is synthetic; in production this would correlate against "
                    "census/socio-economic indicators per area.",
    }


# ---------------------------------------------------------------------------
# Criminology-based offender profiling & risk scoring
# ---------------------------------------------------------------------------

def offender_risk_profile(accused_id: int):
    accused = query_one("SELECT * FROM accused WHERE accused_id=?", (accused_id,))
    if not accused:
        return None

    fir_rows = query(
        """SELECT f.fir_id, f.crime_type, f.date_filed, f.status, f.modus_operandi, fa.role
           FROM fir_accused fa
           JOIN fir f ON fa.fir_id = f.fir_id
           WHERE fa.accused_id=?
           ORDER BY f.date_filed""",
        (accused_id,)
    )

    mo_counter = Counter(r["modus_operandi"] for r in fir_rows)
    crime_type_counter = Counter(r["crime_type"] for r in fir_rows)

    risk_factors = []
    if accused["prior_offenses"] >= 3:
        risk_factors.append("Multiple prior offenses (>=3)")
    if len(fir_rows) >= 2 and len(crime_type_counter) == 1:
        risk_factors.append("Specializes in a single crime type (repeat pattern)")
    if any(r["status"] == "Under Investigation" for r in fir_rows):
        risk_factors.append("Has case(s) currently under active investigation")

    flagged_txns = query(
        "SELECT * FROM transactions WHERE accused_id=? AND flagged=1", (accused_id,)
    )
    if flagged_txns:
        risk_factors.append(f"{len(flagged_txns)} flagged financial transaction(s) linked to this person")

    return {
        "accused": {
            "id": accused["accused_id"],
            "name": accused["name"],
            "age": accused["age"],
            "gender": accused["gender"],
            "prior_offenses": accused["prior_offenses"],
            "risk_score": accused["risk_score"],
        },
        "case_history": fir_rows,
        "modus_operandi_summary": dict(mo_counter.most_common()),
        "crime_type_summary": dict(crime_type_counter.most_common()),
        "risk_factors": risk_factors,
        "flagged_transactions": flagged_txns,
        "evidence": f"Risk score is precomputed from prior-offense count + history pattern; "
                    f"{len(fir_rows)} linked FIR(s) and {len(flagged_txns)} flagged transaction(s) "
                    f"found for accused #{accused_id}.",
    }


def repeat_offenders(min_priors: int = 2, top_n: int = 10):
    rows = query(
        "SELECT accused_id, name, age, gender, prior_offenses, risk_score FROM accused "
        "WHERE prior_offenses >= ? ORDER BY risk_score DESC LIMIT ?",
        (min_priors, top_n)
    )
    return {
        "repeat_offenders": rows,
        "evidence": f"Accused with prior_offenses >= {min_priors}, ranked by precomputed risk score.",
    }


# ---------------------------------------------------------------------------
# Financial crime & transaction link analysis
# ---------------------------------------------------------------------------

def financial_links(min_amount: float = 100000):
    rows = query(
        """SELECT t.txn_id, t.accused_id, a.name, t.counterparty_account, t.amount, t.txn_date, t.flagged
           FROM transactions t
           JOIN accused a ON t.accused_id = a.accused_id
           WHERE t.amount >= ? OR t.flagged = 1
           ORDER BY t.amount DESC""",
        (min_amount,)
    )

    # group by counterparty to find shared accounts (possible money trails)
    by_counterparty = defaultdict(list)
    for r in rows:
        by_counterparty[r["counterparty_account"]].append(r)

    shared = {k: v for k, v in by_counterparty.items() if len(v) > 1}

    return {
        "transactions": rows,
        "shared_counterparty_accounts": shared,
        "evidence": f"{len(rows)} transactions either flagged or above INR {min_amount:,.0f}; "
                    f"{len(shared)} counterparty account(s) linked to multiple accused.",
    }


# ---------------------------------------------------------------------------
# Crime forecasting & early warning (simple heuristic)
# ---------------------------------------------------------------------------

def early_warning_alerts():
    alerts = []

    # 1. Crime types trending up month-over-month
    rows = query("SELECT crime_type, date_filed FROM fir")
    by_type_month = defaultdict(Counter)
    for r in rows:
        by_type_month[r["crime_type"]][r["date_filed"][:7]] += 1

    for crime_type, monthly in by_type_month.items():
        months = sorted(monthly.keys())
        if len(months) >= 2:
            last, prev = monthly[months[-1]], monthly[months[-2]]
            if last > prev and last >= 3:
                severity = "high" if (last - prev) > 5 else ("medium" if (last - prev) > 2 else "low")
                alerts.append({
                    "type": "trend_spike",
                    "severity": severity,
                    "message": f"{crime_type} cases rose from {prev} to {last} "
                               f"between {months[-2]} and {months[-1]}.",
                })

    # 2. Hotspot concentration
    hotspot_data = crime_hotspots(top_n=3)
    for h in hotspot_data["hotspots"]:
        if h["case_count"] >= 8:
            severity = "high" if h["case_count"] >= 12 else ("medium" if h["case_count"] >= 8 else "low")
            alerts.append({
                "type": "hotspot",
                "severity": severity,
                "message": f"{h['area_name']}, {h['city']} shows high case concentration "
                           f"({h['case_count']} FIRs) -- recommend increased patrol.",
            })

    # 3. Organized groups
    groups = detect_organized_groups(min_group_size=3)["groups"]
    for g in groups[:3]:
        severity = "high" if g["group_size"] >= 5 else ("medium" if g["group_size"] >= 3 else "low")
        alerts.append({
            "type": "organized_group",
            "severity": severity,
            "message": f"Possible organized group detected: {g['group_size']} linked accused, "
                       f"avg risk score {g['avg_risk_score']}.",
        })

    return {
        "alerts": alerts,
        "evidence": "Heuristic early-warning rules based on month-over-month trend deltas, "
                    "hotspot concentration thresholds, and co-accused clustering. "
                    "In production this would be backed by trained forecasting models.",
    }


# ---------------------------------------------------------------------------
# Dashboard KPI summary
# ---------------------------------------------------------------------------

def dashboard_summary():
    """
    Returns aggregate KPI stats for the dashboard hero cards.
    Intentionally a single pass over a small set of queries for speed.
    """
    total_firs = query_one("SELECT COUNT(*) as cnt FROM fir")["cnt"]
    open_firs = query_one("SELECT COUNT(*) as cnt FROM fir WHERE status='Under Investigation'")["cnt"]
    total_accused = query_one("SELECT COUNT(*) as cnt FROM accused")["cnt"]
    high_risk_accused = query_one("SELECT COUNT(*) as cnt FROM accused WHERE risk_score >= 0.7")["cnt"]
    total_victims = query_one("SELECT COUNT(*) as cnt FROM victims")["cnt"]
    flagged_txns = query_one("SELECT COUNT(*) as cnt FROM transactions WHERE flagged=1")["cnt"]

    alerts = early_warning_alerts()
    alert_count = len(alerts["alerts"])

    return {
        "total_firs": total_firs,
        "open_firs": open_firs,
        "total_accused": total_accused,
        "high_risk_accused": high_risk_accused,
        "total_victims": total_victims,
        "flagged_transactions": flagged_txns,
        "active_alerts": alert_count,
        "evidence": "Aggregate counts from fir, accused, victims, transactions tables.",
    }
