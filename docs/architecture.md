# Architecture Notes

This document complements the architecture and process-flow diagrams in the
KSP Datathon 2026 submission deck (`KSP_Datathon_2026_Submission.pptx`).

## Layered architecture

1. **Presentation Layer** — `frontend/` (chat UI, dashboards, network
   explorer, voice I/O via Web Speech API, PDF export trigger).
2. **API Gateway & Auth** — In this prototype, FastAPI + CORS middleware. In
   production, this maps to Catalyst's API Gateway with role-based access
   control (Investigator / Analyst / Supervisor / Policymaker roles) and
   audit logging.
3. **Conversational AI & Agent Orchestration** — `backend/app/services/nlu.py`
   performs intent classification and entity extraction (accused IDs, FIR
   numbers, cities, crime types, person names). `backend/app/services/llm.py`
   is an optional hook for LangChain/LLM-based enhancement (Ollama or
   Anthropic API) — the system is designed so this layer can be swapped for a
   full LangChain agent + RAG pipeline without changing the API contract.
4. **Analytics Modules** — `backend/app/services/analytics.py` implements:
   - Crime pattern & trend analytics (`crime_trends`, `crime_hotspots`)
   - Criminal network analysis (`accused_network`, `detect_organized_groups`)
   - Sociological insights (`sociological_insights`)
   - Offender risk profiling (`offender_risk_profile`, `repeat_offenders`)
   - Financial link analysis (`financial_links`)
   - Early warning / forecasting (`early_warning_alerts`)
5. **Data & Storage Layer** — SQLite (`kavach.db`) for the prototype. The
   schema (`fir`, `accused`, `victims`, `locations`, `fir_accused`,
   `fir_victims`, `transactions`, `crime_links`) is designed to map cleanly
   onto a production setup of:
   - Relational DB (PostgreSQL) for FIR/accused/victim/location records
   - Graph DB (Neo4j) for `crime_links` relationship edges
   - Vector store (FAISS/Pinecone) for RAG over case narratives
   - Financial transaction store

## Explainability

Every analytics function returns an `evidence` string describing exactly
which table(s)/computation produced the result. The `/api/chat` endpoint
surfaces this as an `evidence` field in every response, and the frontend
renders it inline under each assistant message — satisfying the "Explainable
AI & Transparent Analytics" requirement at the prototype level.

## Conversation context

`/api/chat` maintains a per-session `context` dict (in-memory for the
prototype) that stores the last-referenced `accused_id`, enabling follow-up
queries like "show their network" without repeating the ID — satisfying the
"Context-aware conversations" requirement.

## Multilingual support

- `nlu.py` includes a small Kannada keyword → English intent-keyword map as a
  starting point for bilingual support.
- The frontend's language selector switches the Web Speech API recognition
  language (`en-IN` / `kn-IN`) for voice input.
- Full Kannada NLU is intended to be handled by the optional LLM layer
  (`services/llm.py`), which can be pointed at a Kannada-capable model.

## Security & governance (production roadmap)

The prototype does not implement authentication. For a production
deployment on Catalyst:

- **Catalyst IAM** for role-based access control (Investigator / Analyst /
  Supervisor / Policymaker roles)
- **Audit logging** of all queries and analytics access, stored via Catalyst
  Data Store
- **Encryption** at rest and in transit for all crime records
- **Data minimization** in chat responses based on role (e.g. analysts may
  see aggregated stats but not full victim PII)
