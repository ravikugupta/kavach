# Kavach — KSP Conversational Crime Intelligence & Analytics Platform

**Kavach** (meaning "shield/armour") is a prototype Conversational AI and Crime
Analytics Platform built for the **KSP Datathon 2026** challenge: *"Intelligent
Conversational AI for KSP Crime Database."*

It lets investigators, analysts, and policymakers query a crime database using
natural language (English + Kannada keywords, with voice input), and provides
analytical capabilities grounded in criminology and sociological insights —
surfacing hidden relationships between crimes, offenders, victims, locations,
and socio-economic patterns.

> ⚠️ **Prototype uses a synthetic, randomly generated dataset.** No real case
> data, real names, or real persons are represented. Built for demonstration only.

---

## ✨ Features

| # | Area | What's implemented |
|---|------|--------------------|
| 1 | Conversational Crime Intelligence | Chat UI with intent-based NLU, context-aware follow-up, voice input (English & Kannada via Web Speech API), PDF export, basic Kannada keyword support |
| 2 | Criminal Network & Relationship Analysis | D3 force-directed graph explorer, organized-group detection via co-accused clustering |
| 3 | Crime Pattern & Trend Analytics | Chart.js bar, line, and doughnut charts; date-range filtering on `/api/analytics/trends` |
| 4 | Sociological Crime Insights | Socio-economic, education, age & gender distributions |
| 5 | Criminology-Based Offender Profiling | Risk scoring, modus-operandi summaries, repeat-offender ranking |
| 6 | Investigator Decision Support | FIR lookups, linked-case retrieval, case summaries |
| 7 | Financial Crime & Transaction Links | Flagged/high-value transaction listing, shared counterparty detection |
| 8 | Crime Forecasting & Early Warning | Linear-trend forecasting per crime type + hotspot risk scoring; alerts include **severity** field |
| 9 | Explainable AI | Every response includes an **Evidence** field citing records/queries used |
| 10 | Secure Role-Based Access | Token-based RBAC (`investigator` / `analyst` / `supervisor`), audit logging to JSONL, CORS middleware |
| 11 | Optional LLM Enhancement | Ollama, Anthropic Claude, or **Google Gemini** API (all optional, app fully offline without) |
| 12 | Dark / Light Mode | Glassmorphism design system with theme toggle; persisted in `localStorage` |

---

## 🏗️ Architecture

```
frontend/
  index.html           SPA shell (Chart.js + D3.js loaded from CDN)
  css/style.css        Premium dark-mode design system
  css/theme.css        Glassmorphism + light-mode CSS variables + theme toggle
  js/
    api.js             fetch wrappers
    app.js             SPA navigation + dark/light mode toggle
    chat.js            Chat UI, typing indicator, voice input (Kannada + EN)
    dashboard.js       Chart.js charts (bar, line, doughnut) + KPI cards
    network.js         D3 v7 force-directed graph with drag/tooltip

backend/app/
  main.py              FastAPI app, CORS, audit middleware, static serving
  auth.py              Token-based RBAC, role hierarchy, FastAPI dependencies
  db.py                SQLite access layer
  routers/
    auth_router.py     /api/auth/* — login, me, logout, demo-tokens
    chat.py            /api/chat — conversational endpoint + session history
    analytics_router.py /api/analytics/* — trends (+ date_range), hotspots, etc.
    records.py         /api/records/* — FIR / accused / victim lookups
    export.py          /api/export/{session}/pdf — ReportLab PDF export
    forecast_router.py /api/forecast/* — trend & hotspot forecasts
  services/
    nlu.py             Rule-based NLU (intent classification + entity extraction)
    analytics.py       Crime analytics; early-warning alerts with severity field
    forecast.py        Linear-regression forecasting + hotspot risk scoring
    llm.py             LLM enhancement — Ollama / Anthropic Claude / Gemini
    audit.py           JSONL audit logging service
  data/
    generate_data.py   Generates the synthetic SQLite database (kavach.db)

tests/
  test_auth.py         16 unit tests — token store, role enforcement
  test_forecast.py     23 unit tests — linear trend maths + DB-backed queries

docs/
  architecture.md      Design notes
  deployment.md        Local + Catalyst deployment guide
deploy_catalyst.sh     Zoho Catalyst deployment script (placeholder)
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+

### 1. Clone & run (one command)
```bash
chmod +x setup_and_run.sh && ./setup_and_run.sh
```

### Manual setup
```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python app/data/generate_data.py   # generates kavach.db
uvicorn app.main:app --reload --port 8000
```

Visit **http://localhost:8000** — API docs at **http://localhost:8000/api/docs**.

---

## 🧪 Running Tests

```bash
cd backend && source venv/bin/activate
python -m pytest tests/ -v
# 39 tests, 0 failures
```

---

## 💬 Example Queries

- "Show crime hotspots in Bengaluru"
- "List repeat offenders"
- "Show risk profile for accused #1"
- "Show network for accused #3"
- "Detect organized crime groups"
- "Show financial links"
- "Show socio-economic insights"
- "Show early warning alerts"
- "Show details for FIR-2025-1042"

---

## 🔑 Auth (Demo Tokens)

| Token | Role | Access |
|-------|------|--------|
| `demo` | investigator | Chat, FIR/accused lookups |
| `analyst-token-002` | analyst | All above + analytics + network |
| `supervisor-token-003` | supervisor | Full access + export |

Pass as `Authorization: Bearer <token>`. All endpoints are currently open in the
prototype; role checks are on `require_role()` guards ready to enable per-route.

---

## 🔌 Optional LLM Enhancement

```bash
# Option A — Ollama (local)
export OLLAMA_HOST=http://localhost:11434
export OLLAMA_MODEL=llama3

# Option B — Anthropic Claude
export ANTHROPIC_API_KEY=sk-ant-...

# Option C — Google Gemini
export GEMINI_API_KEY=AIza...
```

Without any key set, the rule-based NLU answers are used directly.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.9+, FastAPI, SQLite |
| Frontend | Vanilla HTML/CSS/JS, Chart.js 4, D3.js 7 |
| NLU | Rule-based intent/entity extraction (LLM-ready) |
| PDF export | ReportLab |
| Testing | pytest |
| Deployment target | Zoho Catalyst (Advanced I/O Function + Static Hosting) |

---

## 📦 Deployment

See [`docs/deployment.md`](docs/deployment.md) for full Catalyst deployment steps and production checklist.

---

## 📄 License

MIT — see [LICENSE](LICENSE).

---

## 🙏 Acknowledgements

Built for **KSP Datathon 2026** (Karnataka State Police, powered by H2S, technology partner Zoho Catalyst).
# kavach
