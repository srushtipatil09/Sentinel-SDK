# Sentinel AI — An Autonomous AI On-Call Engineer for Any App

## ONE-LINE PITCH

A drop-in SDK that gives any application an autonomous AI SRE — streaming telemetry, deduplicating errors, correlating breaking git deployments, conducting 9-node LangGraph RCA with Gemini, and scoring confidence to cut MTTR from hours to minutes.

---

## THE PROBLEM

Production failures are expensive, chaotic, and slow to resolve:

- **Alert fatigue:** Teams drown in hundreds of duplicate, noisy alerts without context or business prioritization.
- **Manual root-cause hunt:** Engineers waste hours manually correlating logs, traces, exception stack traces, and recent git commits.
- **Static observability tools:** Traditional tools (Sentry, Datadog, New Relic) collect and chart errors, but do not reason about them, cannot cross-reference historical postmortems, and cannot tell engineers what to fix first.

**Result:** High Mean-Time-To-Resolution (MTTR), engineer burnout, and costly downtime.

---

## THE SOLUTION

Sentinel AI is an end-to-end platform pairing a lightweight client SDK with a multi-agent AI backend that turns raw error streams into resolved incidents:

1. **Detect:** Client SDKs stream enriched error signals (logs, uncaught exceptions, distributed trace spans, metrics, and deployment metadata).
2. **Ingest & Fingerprint:** FastAPI backend groups duplicate failures via deterministic route-normalized fingerprinting, records incidents in PostgreSQL, and streams telemetry to BigQuery & Pub/Sub.
3. **Analyze & Correlate:** BigQuery ML runs ARIMA_PLUS time-series anomaly detection on error counts, while the correlation engine links error spikes directly to recent git commits and deployments.
4. **Reason & RAG:** A 9-node **LangGraph StateGraph** multi-agent pipeline queries historical postmortems and playbooks via ChromaDB + Vertex AI embeddings (`text-embedding-004`), calculates multi-factor confidence scores, and synthesizes root-cause hypotheses with Gemini 2.5 Flash.
5. **Act & Notify:** Live incident state is mirrored in real time to Firestore, dispatches alerts across Slack, Discord, Email, and webhooks, and visualizes RCA narratives, agent reasoning trees, and confidence breakdowns on a React dashboard.

---

## WHY IT'S DIFFERENT (AND DATA-DRIVEN)

| Capability | Traditional APM / Error Loggers | Sentinel AI (Implemented) |
|---|---|---|
| **Incident Processing** | Capture and display raw error lists | Detect + deduplicate + explain root cause + recommend actionable fixes |
| **Root Cause Analysis** | Manual search across disparate logs and traces | Automated 9-agent LangGraph workflow synthesizing logs, traces, exceptions, and code changes |
| **Knowledge Retrieval** | Static runbooks stored in wikis/Notion | Semantic RAG pipeline (Vertex AI `text-embedding-004` + ChromaDB) matching past incidents and postmortems |
| **Anomaly Detection** | Static static threshold alerts (e.g. `errors > 50`) | **BigQuery ML ARIMA_PLUS** time-series anomaly detection accounting for seasonality |
| **Confidence Scoring** | None / Binary alert status | **Multi-Factor Confidence Engine** evaluating evidence across 6 telemetry and knowledge dimensions |
| **Deploy Correlation** | Manual inspection of deployment logs | Automated correlation linking error surges directly to commit hashes, authors, and diffs |

---

## ARCHITECTURE

### Multi-Agent LangGraph Pipeline (`StateGraph`)

Incident analysis is driven by a 9-node directed graph orchestrated via **LangGraph**:

```
[ Incident Triggered ]
         │
         ▼
  1. Planner Agent ─────────────► Evaluates severity (P0-P3) and schedules domain agents
         │
         ▼
  2. Log Analysis Agent ────────► Computes frequency distributions, error levels, top messages
         │
         ▼
  3. Trace Analysis Agent ──────► Analyzes HTTP latencies, failing spans, and bottleneck endpoints
         │
         ▼
  4. Exception Analysis Agent ──► Parses stack traces, exception types, and root error lines
         │
         ▼
  5. Metrics Agent ─────────────► Evaluates metric spikes, CPU/memory/DB connection saturations
         │
         ▼
  6. Git / Deploy Agent ────────► Correlates error surge with recent deployment commits and authors
         │
         ▼
  7. RAG Retrieval Agent ───────► Semantic search over past postmortems & runbooks (ChromaDB + Vertex AI)
         │
         ▼
  8. Confidence Agent ──────────► Multi-factor mathematical scoring across all gathered evidence
         │
         ▼
  9. Final RCA Agent ───────────► Generates executive RCA narrative, root cause, and fixes via Gemini 2.5 Flash
         │
         ▼
   [ Complete RCA Report ]
```

---

## GOOGLE CLOUD TECH STACK

| Google Cloud Service | Purpose in Sentinel AI | Implementation Module |
|---|---|---|
| **Cloud Run** | Serverless compute hosting backend FastAPI API & React Nginx container | `Dockerfile`, `cloudbuild.yaml` |
| **Pub/Sub** | Asynchronous event bus (`telemetry-events`, `incident-events`, `ai-rca-events`) | `backend/queue/pubsub_client.py` |
| **BigQuery + BigQuery ML** | Long-term telemetry warehouse + ARIMA_PLUS time-series anomaly detection | `backend/analytics/bigquery_client.py` |
| **Vertex AI** | Managed 768-dimensional embeddings (`text-embedding-004`) for RAG vector search | `backend/embeddings/generator.py` |
| **Gemini 2.5 Flash** | Multi-agent reasoning, root-cause hypothesis generation, and remediation guidance | `backend/llm/gemini_client.py` |
| **Firestore (Native Mode)** | Real-time incident state mirror for instant status updates | `backend/database/firestore_client.py` |
| **Secret Manager** | Secure storage of API keys, DB connection strings, and JWT secrets | `deploy/README.md` |

---

## FULL TECH STACK (BY LAYER)

### 1. Client SDKs (Telemetry Ingestion)
- **Python SDK (`sentinelai-telemetry-sdk` on PyPI):**
  - Thread-safe memory buffering and batch dispatching.
  - Automatic stack trace capturing with `capture_exception()`.
  - Structured logging with `capture_log()`.
  - Distributed tracing with `capture_trace()`.
  - Deployment tracking with `capture_deployment(version, commit_hash, author)`.
- **Browser JavaScript SDK (`observeai-browser.js`):**
  - Intercepts unhandled JS errors via `window.onerror` and `unhandledrejection`.
  - Monkey-patches `window.fetch` to capture HTTP $\ge$ 500 network errors.
  - Injects distributed `x-trace-id` headers on outgoing requests.
  - Flushes reliably using `navigator.sendBeacon` on tab close/visibility changes.

### 2. Ingestion & Core Backend
- **Framework:** Python 3.11 + FastAPI with async route handlers.
- **Validation:** Pydantic v2 for typed telemetry schemas (`IngestPayloadSchema`).
- **Security:** Project API key generation, hashing, encrypted storage, and rotation.
- **Authentication:** JWT (OAuth2 Password Bearer) with RBAC (Admin, Member, Viewer).

### 3. Primary Storage & Vector Store
- **PostgreSQL:** Primary relational database (Users, Projects, Services, Incidents, Timelines, RCA Reports, Notification Configurations).
- **SQLAlchemy 2.0 (Async) & Alembic:** ORM modeling and database migrations.
- **ChromaDB:** Local persistent vector database storing chunked postmortems and playbooks.
- **SQLite Fallback:** Self-contained testing/fallback via `aiosqlite`.

### 4. Analysis & Anomaly Detection
- **BigQuery ML ARIMA_PLUS:** Hourly/daily time-series models trained on error frequencies.
- **Deterministic Fingerprinting:** Normalizes dynamic route patterns (e.g. `/users/{id}`), combines HTTP status and exception types to deduplicate error floods into a single ongoing incident.
- **Multi-Factor Confidence Engine:** Calculates confidence scores ($0.0 - 1.0$) across logs, traces, exceptions, metrics, git correlation, and RAG similarity.

### 5. Multi-Agent AI & RAG Engine
- **LangGraph:** Cyclic/acyclic stateful agent orchestration.
- **Google GenAI / Generative AI SDK:** Integration with Gemini 2.5 Flash.
- **RAG Pipeline:** Document loaders (`.pdf`, `.docx`, `.md`, `.txt`) parsed and embedded with Vertex AI `text-embedding-004`.

### 6. Incident Response & Notifications
- **Notification Engine:** Multi-channel alerting dispatcher supporting:
  - Slack incoming webhooks.
  - Discord incoming webhooks.
  - Generic JSON webhooks.
  - SMTP email dispatch.

### 7. Dashboard & Frontend Console
- **Framework:** React 18, Vite, TailwindCSS, Lucide Icons.
- **Capabilities:**
  - Real-time incident management (triage, status changes, assignee management).
  - Visual AI Root Cause Analysis viewer with formatted remediation steps.
  - Multi-agent execution inspector showing individual agent decisions and execution times.
  - Telemetry breakdown (error frequency graphs, raw log logs, stack traces).
  - SDK onboarding guide and API key lifecycle manager.

### 8. DevOps & Deployment
- **Google Cloud Run:** Dual-container setup (Backend API + Frontend Nginx).
- **Google Cloud Build:** Automated CI/CD build manifests (`cloudbuild.yaml`).
- **Docker Compose:** Full local development stack (Postgres + Redis + Backend + Frontend).
