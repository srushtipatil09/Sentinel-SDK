# Sentinel AI — Google Cloud Stack Integration Map

This document maps every platform capability to the Google Cloud service that powers it and the module that implements it.

| Capability | Google Service | Module(s) |
|---|---|---|
| Telemetry warehouse + ML anomaly detection | **BigQuery** + **BigQuery ML** (ARIMA_PLUS) | [`backend/analytics/bigquery_client.py`](backend/analytics/bigquery_client.py) |
| Async event bus | **Pub/Sub** | [`backend/queue/pubsub_client.py`](backend/queue/pubsub_client.py), [`backend/queue/event_bus.py`](backend/queue/event_bus.py) |
| Live incident state mirror | **Firestore** | [`backend/database/firestore_client.py`](backend/database/firestore_client.py) |
| RCA reasoning (LLM) | **Gemini** (via `google-generativeai`) | [`backend/llm/gemini_client.py`](backend/llm/gemini_client.py) |
| Managed embeddings (768-dim) | **Vertex AI** (`text-embedding-004`) | [`backend/embeddings/generator.py`](backend/embeddings/generator.py) |
| Agentic RCA orchestration | **LangGraph** `StateGraph` | [`backend/agents/graph.py`](backend/agents/graph.py), [`backend/agents/workflow.py`](backend/agents/workflow.py) |
| Serverless hosting | **Cloud Run** | [`Dockerfile`](Dockerfile), [`cloudbuild.yaml`](cloudbuild.yaml) |
| Dashboards & BI | **Looker Studio** (connects to BigQuery) | Documentation only — see [`deploy/README.md`](deploy/README.md) |

## Feature Toggles

Every GCP integration is gated by a feature toggle in [`backend/config/settings.py`](backend/config/settings.py) (via environment variables).

| Toggle | Default | Description |
|---|---|---|
| `BIGQUERY_ENABLED` | `true` | BigQuery telemetry warehouse + ARIMA+ ML |
| `PUBSUB_ENABLED` | `true` | Pub/Sub event bus |
| `FIRESTORE_ENABLED` | `true` | Firestore incident state mirror |
| `VERTEX_AI_ENABLED` | `true` | Vertex AI managed embeddings (768-dim) |

## Google Cloud Native Architecture

```
Telemetry Stream ──► [Pub/Sub] ──► [BigQuery + BigQuery ML (ARIMA+)]
Live State       ──► [Firestore] (Real-time incident state mirror)
Embeddings       ──► [Vertex AI text-embedding-004] (768-dim managed embeddings)
RCA Agent Engine ──► [Gemini 2.5 Flash] + [LangGraph StateGraph]
Compute          ──► [Cloud Run]
```

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/analytics/anomaly-model/train` | `POST` | Train BigQuery ML ARIMA+ model |
| `/api/v1/analytics/anomalies` | `GET` | Detect anomalies (last hour) |
| `/api/v1/analytics/overview` | `GET` | Platform analytics overview |

## Deployment

See [`deploy/README.md`](deploy/README.md) for step-by-step `gcloud` commands.
