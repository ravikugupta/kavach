import os
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.routers import chat, analytics_router, records, export, auth_router, forecast_router

app = FastAPI(
    title="Kavach - KSP Crime Intelligence Platform",
    description=(
        "Intelligent Conversational AI and Crime Analytics Platform for the "
        "Karnataka State Police crime database. Supports natural language queries, "
        "criminal network analysis, crime trend forecasting, socio-demographic insights, "
        "offender risk profiling, and explainable AI evidence trails."
    ),
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Restrict to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Audit Middleware ──────────────────────────────────────────────────────────
@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    from app.services.audit import log_event
    start = time.monotonic()
    response = await call_next(request)
    elapsed_ms = round((time.monotonic() - start) * 1000)

    # Only log API calls (not static asset requests)
    if request.url.path.startswith("/api/"):
        auth_header = request.headers.get("authorization", "")
        token = auth_header.replace("Bearer ", "").strip() if auth_header else "anonymous"

        from app.auth import TOKENS
        user = TOKENS.get(token, {})

        log_event(
            method=request.method,
            path=request.url.path,
            user_id=user.get("user_id", "anonymous"),
            role=user.get("role", "none"),
            ip=request.client.host if request.client else "",
            status_code=response.status_code,
        )
    return response


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router.router)
app.include_router(chat.router)
app.include_router(analytics_router.router)
app.include_router(records.router)
app.include_router(export.router)
app.include_router(forecast_router.router)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "kavach-backend",
        "version": "1.0.0",
        "features": [
            "conversational_ai",
            "criminal_network_analysis",
            "crime_trend_analytics",
            "sociological_insights",
            "offender_risk_profiling",
            "financial_crime_analysis",
            "crime_forecasting",
            "early_warning_alerts",
            "explainable_ai",
            "role_based_access",
            "audit_logging",
        ],
    }


# ── Static Frontend ───────────────────────────────────────────────────────────
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
