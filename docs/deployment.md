# Kavach — Deployment Guide

## Local Development

```bash
./setup_and_run.sh
```
Opens `http://localhost:8000` — FastAPI serves both the API and the static frontend.

API docs: `http://localhost:8000/api/docs`

---

## Environment Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| `OLLAMA_HOST` | Local Ollama base URL (e.g. `http://localhost:11434`) | No |
| `OLLAMA_MODEL` | Ollama model name (default: `llama3`) | No |
| `ANTHROPIC_API_KEY` | Claude API key for LLM enhancement | No |
| `GEMINI_API_KEY` | Google Gemini API key (fallback LLM) | No |

Copy `.env.example` → `.env` and set values. Without any LLM key the app works fully offline using rule-based NLU.

---

## Running Tests

```bash
cd backend
source venv/bin/activate
python -m pytest tests/ -v
```

39 unit tests cover auth role enforcement and forecast service logic.

---

## Zoho Catalyst Deployment

### Service Mapping

| Kavach Component | Catalyst Service |
|-----------------|-----------------|
| FastAPI backend | Advanced I/O Function (`python3.9` stack) |
| HTML/CSS/JS frontend | Static Hosting (Web Client) |
| SQLite DB (prototype) | Embedded in function package |
| SQLite DB (production) | Catalyst DataStore or Cloud Scale DB |
| Audit log | Catalyst Logs or App Logs |
| Auth tokens | Catalyst Vault (for secrets) |

### Steps

1. **Install Catalyst CLI**
   ```bash
   npm install -g zoho-catalyst-cli
   catalyst login
   ```

2. **Initialise project** in the repo root
   ```bash
   catalyst init
   # Select: Advanced I/O Function
   # Stack: Python 3.9
   # Entry point: app.main:app
   ```

3. **Run the deploy script** (after uncommenting the deploy command)
   ```bash
   ./deploy_catalyst.sh
   ```

4. **Environment secrets** — set via Catalyst Console → Functions → Environment Variables:
   - `ANTHROPIC_API_KEY` or `GEMINI_API_KEY` (if LLM enhancement is desired)

5. **Custom domain** — configure in Catalyst Console → Hosting → Domains.

### Production Checklist

- [ ] Replace `allow_origins=["*"]` in `main.py` CORS middleware with specific origins
- [ ] Replace static token store in `auth.py` with JWT + a proper user DB
- [ ] Move SQLite to Catalyst DataStore or a managed Postgres instance
- [ ] Enable HTTPS (Catalyst handles this automatically via its CDN)
- [ ] Set `LOG_LEVEL=WARNING` for the uvicorn server
- [ ] Rotate demo tokens and disable the `/api/auth/demo-tokens` endpoint

---

## Architecture Diagram

```
Browser
  │
  ├─ GET /            → Catalyst Static Hosting  (HTML/CSS/JS)
  │
  └─ POST /api/*      → Catalyst Advanced I/O Function (FastAPI)
                                │
                          ┌─────┴──────┐
                          │  SQLite DB  │  (→ Catalyst DataStore in prod)
                          └────────────┘
```
