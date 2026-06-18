"""
Conversational orchestration layer.

This module implements a lightweight intent-recognition + entity-extraction
pipeline so the prototype works fully offline (no API key required). If an
ANTHROPIC_API_KEY (or OLLAMA) is configured, it can optionally be used to
improve free-text understanding -- see `app/services/llm.py`.

Design goal: every response includes an `evidence` field citing which
records/queries were used, satisfying the Explainable AI requirement.
"""

from __future__ import annotations
from typing import Optional
import re
from app.db import query, query_one
from app.services import analytics

# Basic Kannada keyword map -> English intent keywords (prototype-level support)
KANNADA_KEYWORDS = {
    "ಕಳ್ಳತನ": "theft",
    "ಆರೋಪಿ": "accused",
    "ಪ್ರಕರಣ": "case",
    "ಹಿಂದಿನ": "previous",
    "ಜಾಲ": "network",
    "ಅಪಾಯ": "risk",
    "ಹಾಟ್‌ಸ್ಪಾಟ್": "hotspot",
}


def normalize_query(text: str) -> str:
    normalized = text
    for kn, en in KANNADA_KEYWORDS.items():
        normalized = normalized.replace(kn, en)
    return normalized


def extract_accused_id(text: str):
    match = re.search(r"accused\s*#?\s*(\d+)", text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    match = re.search(r"#\s*(\d+)", text)
    if match:
        return int(match.group(1))
    return None


def extract_fir_id(text: str):
    match = re.search(r"(FIR-\d{4}-\d+)", text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None


def extract_city(text: str):
    cities = ["Bengaluru", "Mysuru", "Hubli", "Mangaluru", "Belagavi", "Kalaburagi", "Tumakuru", "Shivamogga"]
    for city in cities:
        if city.lower() in text.lower():
            return city
    return None


def extract_crime_type(text: str):
    crime_types = [
        "Theft", "Burglary", "Vehicle Theft", "Robbery", "Assault",
        "Cybercrime - Financial Fraud", "Cyber Fraud", "Chain Snatching", "Cheating",
        "Counterfeit Currency", "Drug Peddling", "Extortion", "House Breaking"
    ]
    text_lower = text.lower()
    for ct in crime_types:
        if ct.lower() in text_lower:
            if ct == "Cyber Fraud":
                return "Cybercrime - Financial Fraud"
            return ct
    if "vehicle theft" in text_lower or "bike theft" in text_lower:
        return "Vehicle Theft"
    return None


def extract_name(text: str):
    """Try to extract a proper-noun person name (very simple heuristic)."""
    match = re.search(r"named?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", text)
    if match:
        return match.group(1)
    return None


# ---------------------------------------------------------------------------
# Intent classification (rule-based, ordered by specificity)
# ---------------------------------------------------------------------------

INTENT_PATTERNS = [
    ("fir_lookup", [r"\bfir[- ]?\d", r"case\s+status", r"details? of (case|fir)"]),
    ("accused_profile", [r"profile of accused", r"risk (score|profile)", r"behavioral profile", r"history of accused"]),
    ("accused_network", [r"network", r"connections? of", r"linked to accused", r"associates of"]),
    ("organized_groups", [r"organized (crime|group)", r"gang", r"criminal network groups?"]),
    ("repeat_offenders", [r"repeat offenders?", r"habitual (criminal|offender)", r"prior offen"]),
    ("financial_links", [r"financial", r"transaction", r"money trail", r"bank account"]),
    ("hotspots", [r"hotspot", r"crime hotspots?", r"high crime area"]),
    ("trends", [r"trend", r"pattern", r"over time", r"statistics", r"how many .* cases"]),
    ("sociological", [r"socio", r"demographic", r"age group", r"economic background", r"education"]),
    ("early_warning", [r"early warning", r"alert", r"forecast", r"emerging", r"predict"]),
    ("accused_search", [r"accused", r"offender", r"suspect"]),
    ("greeting", [r"^\s*(hi|hello|hey|namaskara|namaste)\b"]),
    ("help", [r"^\s*help\b", r"what can you do"]),
]


def classify_intent(text: str) -> str:
    text_norm = normalize_query(text).lower()
    for intent, patterns in INTENT_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, text_norm):
                return intent
    return "general_query"


# ---------------------------------------------------------------------------
# Main handler
# ---------------------------------------------------------------------------

def handle_query(text: str, context: Optional[dict] = None) -> dict:
    """
    Main entry point for the conversational layer.

    `context` carries lightweight conversation state (e.g. last referenced
    accused_id) so follow-up questions ("show their previous cases") work
    without repeating full context -- per the Context-Aware Conversations
    requirement.
    """
    context = context or {}
    text_norm = normalize_query(text)
    intent = classify_intent(text)

    accused_id = extract_accused_id(text_norm) or context.get("last_accused_id")
    fir_id = extract_fir_id(text_norm)
    city = extract_city(text_norm)
    crime_type = extract_crime_type(text_norm)

    response = {"intent": intent, "answer": "", "data": None, "evidence": "", "suggestions": []}

    if intent == "greeting":
        response["answer"] = (
            "Namaskara! I'm Kavach, the KSP Crime Intelligence Assistant. "
            "You can ask me about FIRs, accused persons, crime hotspots, "
            "criminal networks, offender risk profiles, and more -- in English or Kannada."
        )
        response["suggestions"] = [
            "Show crime hotspots in Bengaluru",
            "List repeat offenders",
            "Show network for accused #3",
        ]

    elif intent == "help":
        response["answer"] = (
            "I can help with: FIR/case lookups, accused profiles and risk scores, "
            "criminal network analysis, organized group detection, repeat offenders, "
            "financial transaction links, crime hotspots and trends, socio-demographic "
            "insights, and early-warning alerts."
        )

    elif intent == "fir_lookup":
        if fir_id:
            fir = query_one("""SELECT f.*, l.area_name, l.city FROM fir f
                                JOIN locations l ON f.location_id = l.location_id
                                WHERE f.fir_id = ?""", (fir_id,))
            if fir:
                accused_rows = query(
                    """SELECT a.accused_id, a.name, fa.role FROM fir_accused fa
                       JOIN accused a ON fa.accused_id = a.accused_id WHERE fa.fir_id=?""",
                    (fir_id,)
                )
                response["data"] = {"fir": fir, "accused": accused_rows}
                response["answer"] = (
                    f"{fir_id}: {fir['crime_type']} reported on {fir['date_filed']} "
                    f"in {fir['area_name']}, {fir['city']}. Status: {fir['status']}. "
                    f"Linked accused: {', '.join(a['name'] for a in accused_rows) if accused_rows else 'none on record'}."
                )
                response["evidence"] = f"Retrieved directly from FIR record {fir_id} and fir_accused linkage table."
            else:
                response["answer"] = f"I couldn't find any record for {fir_id}."
        else:
            response["answer"] = "Please provide an FIR number, e.g. 'Show details for FIR-2025-1042'."

    elif intent == "accused_profile":
        if accused_id:
            profile = analytics.offender_risk_profile(accused_id)
            if profile:
                response["data"] = profile
                response["answer"] = (
                    f"Accused #{accused_id} ({profile['accused']['name']}): "
                    f"age {profile['accused']['age']}, {profile['accused']['gender']}, "
                    f"{profile['accused']['prior_offenses']} prior offense(s), "
                    f"risk score {profile['accused']['risk_score']} / 1.0. "
                    f"Linked to {len(profile['case_history'])} case(s). "
                    + (f"Risk factors: {', '.join(profile['risk_factors'])}." if profile['risk_factors']
                       else "No major risk factors flagged.")
                )
                response["evidence"] = profile["evidence"]
                context["last_accused_id"] = accused_id
            else:
                response["answer"] = f"No record found for accused #{accused_id}."
        else:
            response["answer"] = "Please specify an accused ID, e.g. 'Show risk profile for accused #12'."

    elif intent == "accused_network":
        if accused_id:
            network = analytics.accused_network(accused_id, depth=1)
            if network:
                response["data"] = network
                related = [n["label"] for n in network["nodes"] if n["type"] != "accused" or n["id"] != accused_id]
                response["answer"] = (
                    f"Network for accused #{accused_id} ({network['root_accused']['name']}): "
                    f"{len(network['nodes'])-1} connected entities found "
                    f"(co-accused, victims, and locations). "
                    f"Examples: {', '.join(related[:5])}{'...' if len(related) > 5 else ''}."
                )
                response["evidence"] = network["evidence"]
                context["last_accused_id"] = accused_id
            else:
                response["answer"] = f"No record found for accused #{accused_id}."
        else:
            response["answer"] = "Please specify an accused ID, e.g. 'Show network for accused #5'."

    elif intent == "organized_groups":
        result = analytics.detect_organized_groups(min_group_size=3)
        response["data"] = result
        if result["groups"]:
            top = result["groups"][0]
            names = ", ".join(m["name"] for m in top["members"][:5])
            response["answer"] = (
                f"Found {len(result['groups'])} potential organized group(s). "
                f"Largest group has {top['group_size']} members "
                f"(avg risk score {top['avg_risk_score']}): {names}."
            )
        else:
            response["answer"] = "No organized groups meeting the size threshold were detected in the current dataset."
        response["evidence"] = result["evidence"]

    elif intent == "repeat_offenders":
        result = analytics.repeat_offenders(min_priors=2, top_n=10)
        response["data"] = result
        names = ", ".join(f"{r['name']} (#{r['accused_id']}, risk {r['risk_score']})" for r in result["repeat_offenders"][:5])
        response["answer"] = (
            f"Top repeat offenders by risk score: {names}."
            if result["repeat_offenders"] else "No repeat offenders found with 2+ prior offenses."
        )
        response["evidence"] = result["evidence"]

    elif intent == "financial_links":
        result = analytics.financial_links(min_amount=100000)
        response["data"] = result
        response["answer"] = (
            f"Found {len(result['transactions'])} high-value/flagged transactions. "
            f"{len(result['shared_counterparty_accounts'])} counterparty account(s) "
            f"are linked to multiple accused -- possible shared money trail."
        )
        response["evidence"] = result["evidence"]

    elif intent == "hotspots":
        result = analytics.crime_hotspots(top_n=5)
        response["data"] = result
        top = result["hotspots"][0] if result["hotspots"] else None
        response["answer"] = (
            f"Top crime hotspot is {top['area_name']}, {top['city']} with {top['case_count']} FIRs."
            if top else "No hotspot data available."
        )
        response["evidence"] = result["evidence"]

    elif intent == "trends":
        result = analytics.crime_trends(city=city, crime_type=crime_type)
        response["data"] = result
        top_type = next(iter(result["by_crime_type"]), None)
        response["answer"] = (
            f"Found {result['total_cases']} case(s)"
            + (f" in {city}" if city else "")
            + (f" for {crime_type}" if crime_type else "")
            + f". Most common crime type: {top_type} ({result['by_crime_type'].get(top_type, 0)} cases)."
            if result["total_cases"] else "No matching cases found."
        )
        response["evidence"] = result["evidence"]

    elif intent == "sociological":
        result = analytics.sociological_insights()
        response["data"] = result
        top_econ = next(iter(result["accused_economic_background"]), None)
        response["answer"] = (
            f"Among accused persons, the most common economic background is "
            f"'{top_econ}' ({result['accused_economic_background'].get(top_econ, 0)} individuals). "
            f"Age distribution: {result['accused_age_distribution']}."
        )
        response["evidence"] = result["evidence"]

    elif intent == "early_warning":
        result = analytics.early_warning_alerts()
        response["data"] = result
        if result["alerts"]:
            response["answer"] = "Early-warning alerts: " + " | ".join(a["message"] for a in result["alerts"][:3])
        else:
            response["answer"] = "No early-warning alerts triggered in the current dataset."
        response["evidence"] = result["evidence"]

    elif intent == "accused_search":
        name = extract_name(text_norm)
        if name:
            rows = query("SELECT accused_id, name, age, gender, risk_score FROM accused WHERE name LIKE ?", (f"%{name}%",))
            response["data"] = {"matches": rows}
            if rows:
                response["answer"] = (
                    "Found matching accused: " +
                    ", ".join(f"{r['name']} (#{r['accused_id']}, risk {r['risk_score']})" for r in rows)
                )
                if len(rows) == 1:
                    context["last_accused_id"] = rows[0]["accused_id"]
            else:
                response["answer"] = f"No accused found matching '{name}'."
            response["evidence"] = f"Matched against accused.name using LIKE '%{name}%'."
        else:
            response["answer"] = (
                "I can search accused by name or ID. Try: "
                "'Show risk profile for accused #7' or 'Search accused named Ramesh'."
            )

    else:  # general_query fallback
        response["answer"] = (
            "I'm not sure how to answer that yet in this prototype. Try asking about: "
            "FIR status, accused risk profiles, criminal networks, repeat offenders, "
            "crime hotspots, financial links, or early-warning alerts."
        )
        response["suggestions"] = [
            "Show crime hotspots",
            "List repeat offenders",
            "Show network for accused #1",
            "Show socio-economic insights",
        ]

    response["context"] = context
    return response
