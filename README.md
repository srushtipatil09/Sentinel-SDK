# Sentinel AI — Platform User Guide & UI Navigation Manual

Welcome to **Sentinel AI**, an enterprise-grade autonomous Site Reliability Engineering (SRE) and AI Incident Commander platform. This user guide explains the entire user interface, page-by-page functionality, user access levels, and step-by-step operational workflows.

---

## Table of Contents

1. [Platform Overview & Core Concept](#1-platform-overview--core-concept)
2. [User Roles & Permissions (RBAC)](#2-user-roles--permissions-rbac)
3. [Authentication & Account Setup](#3-authentication--account-setup)
4. [Global Navigation & Workspace Layout](#4-global-navigation--workspace-layout)
5. [Page-by-Page Feature Guide](#5-page-by-page-feature-guide)
   - [5.1 Executive Dashboard (`/dashboard`)](#51-executive-dashboard-dashboard)
   - [5.2 Incident Queue & Triage (`/incidents`)](#52-incident-queue--triage-incidents)
   - [5.3 Incident Commander Detail View (`/incidents/:id`)](#53-incident-commander-detail-view-incidentsid)
   - [5.4 Microservice Topology & Health (`/services`)](#54-microservice-topology--health-services)
   - [5.5 Autonomous AI Investigations Audit (`/ai-investigations`)](#55-autonomous-ai-investigations-audit-ai-investigations)
   - [5.6 Live Log Explorer (`/logs`)](#56-live-log-explorer-logs)
   - [5.7 Performance Metrics & BigQuery ML (`/metrics`)](#57-performance-metrics--bigquery-ml-metrics)
   - [5.8 Knowledge Base & Enterprise RAG (`/knowledge`)](#58-knowledge-base--enterprise-rag-knowledge)
   - [5.9 Settings & Integrations (`/settings`)](#59-settings--integrations-settings)
   - [5.10 Profile & Security (`/settings/profile`)](#510-profile--security-settingsprofile)
6. [Operator Playbooks & "How-To" Guides](#6-operator-playbooks--how-to-guides)
   - [Playbook 1: Integrating a Microservice with the Sentinel SDK](#playbook-1-integrating-a-microservice-with-the-sentinel-sdk)
   - [Playbook 2: Investigating an Active Incident with Gemini RCA](#playbook-2-investigating-an-active-incident-with-gemini-rca)
   - [Playbook 3: Setting Up Slack, Discord & Email Alerts](#playbook-3-setting-up-slack-discord--email-alerts)
   - [Playbook 4: Uploading Historical Runbooks to Semantic RAG](#playbook-4-uploading-historical-runbooks-to-semantic-rag)
7. [User Access & Permissions Matrix](#7-user-access--permissions-matrix)
8. [Frequently Asked Questions & Troubleshooting](#8-frequently-asked-questions--troubleshooting)

---

## 1. Platform Overview & Core Concept

Traditional APM tools (Datadog, New Relic, Sentry) alert engineers *that* something is broken, leaving teams to manually search through logs, stack traces, and Git commits.

**Sentinel AI operates as an autonomous AI teammate:**
1. **Intercepts Failures:** Drop-in SDKs stream logs, distributed trace spans, and unhandled exceptions with sub-50ms latency.
2. **Deduplicates Cascades:** A deterministic route normalizer converts dynamic paths (`/orders/99a3` $\to$ `/orders/{id}`) and hashes the root stack frame, collapsing thousands of error bursts into a single actionable incident record.
3. **9-Agent Autonomous Investigation:** LangGraph orchestrates 9 specialized agents (Planner, Log, Trace, Exception, Metrics, Git, RAG, Confidence, and Gemini).
4. **Synthesizes Exact Fixes:** Google Gemini generates root-cause analyses, exact code diff patches, and long-term architectural guardrails.
5. **Omnichannel Alerting:** Alerts are delivered across Discord, Slack, and Email before on-call engineers even open their terminals.

---

## 2. User Roles & Permissions (RBAC)

Sentinel AI enforces multi-tenant organization boundaries and granular Role-Based Access Control:

| Role | Target Persona | Scope of Access |
|---|---|---|
| **OWNER** | CTO / VP of Engineering | Full administrative control: billing, organization deletion, inviting members, managing all projects, generating/revoking API keys, and notification dispatch rules. |
| **ADMIN** | Lead SRE / DevOps Manager | Full operational control: manage projects, invite members, generate API keys, configure alert webhooks, re-run AI investigations, and resolve incidents. |
| **MEMBER** | Software Engineer / SRE | Operational access: triage incidents, change incident status, view AI RCA reports, trigger re-analysis, query logs and metrics, upload runbooks to RAG. Cannot revoke API keys or manage organization members. |
| **VIEWER** | Stakeholder / QA / Auditor | Read-only access: view dashboards, incidents, logs, metrics, and service maps. Cannot modify incident states, re-analyze, or access secrets. |

---

## 3. Authentication & Account Setup

### 3.1 Registration (`/register`)
* **URL:** `http://localhost:5173/register`
* **Fields:** Full Name, Work Email, Password (minimum 8 characters), and Initial Project / Organization Name.
* **Behavior:** Automatically provisions your user profile, default organization, and an initial `production` project. JWT tokens (`sentinelai_access_token` and `sentinelai_refresh_token`) are securely stored in browser storage.

### 3.2 Login (`/login`)
* **URL:** `http://localhost:5173/login`
* **Credentials:** Work Email and Password.
* **Auto-Redirection:** Authenticated users are automatically redirected to `/dashboard`. Unauthenticated sessions attempting to access protected routes are routed back to `/login`.

### 3.3 Password Recovery (`/forgot-password` & `/reset-password`)
* Input your registered email to receive a secure password reset token.
* Follow the link to `/reset-password` to establish a new password and automatically invalidate older session tokens.

---

## 4. Global Navigation & Workspace Layout

The application utilizes an intuitive, persistent layout across all views:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ [Sentinel AI Logo]  [Project: Production ▼]                          [🔔 Alerts (3)] [User Profile (JD)]│
├──────────────┬──────────────────────────────────────────────────────────────────────────────────────────┤
│ 📊 Dashboard │                                                                                          │
│ 🚨 Incidents │                                     MAIN CONTENT AREA                                    │
│ 🖥️ Services  │                                                                                          │
│ 🤖 AI Audits │                       (Incident Commander / Telemetry / Analytics)                       │
│ 📄 Logs      │                                                                                          │
│ 📈 Metrics   │                                                                                          │
│ 📚 Knowledge │                                                                                          │
│ ⚙️ Settings  │                                                                                          │
├──────────────┴──────────────────────────────────────────────────────────────────────────────────────────┤
│ [🌙 / ☀️ Dark Mode Toggle]                                                  [◀ Collapse Sidebar Button] │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 4.1 Collapsible Left Sidebar
* **Brand Header:** Sentinel AI pulse status and platform version badge.
* **Project Switcher Dropdown:** Fast switching between projects (e.g., `production`, `staging`, `payments-microservice`). Includes a **"+ New Project"** modal shortcut.
* **Navigation Links:** Instant routing to the 8 core operational pages.
* **Theme Toggle:** Switch between sleek dark mode (`bg-slate-900`) and high-contrast light mode.
* **Collapse Button:** Collapses sidebar into compact icon-only mode for maximum screen real estate during incident investigations.

### 4.2 Topbar
* **Active Project Context:** Displays current project name and environment tag.
* **Live Incident Alert Bell:** Opens the slide-over **Notification Drawer** showing recent automated alert dispatches and delivery statuses.
* **Profile Menu:** Quick access to User Profile settings and one-click session logout.

---

## 5. Page-by-Page Feature Guide

### 5.1 Executive Dashboard (`/dashboard`)

The central command center for engineering leads and on-call teams.

#### Key Metrics Cards:
* **Active Incidents:** Real-time count of unresolved outages requiring attention.
* **Critical (P0) Outages:** Immediate red-flag counter for high-severity failures.
* **24-Hour Error Volume:** Total aggregated exceptions ingested across all connected services.
* **Average MTTR:** Rolling Mean-Time-To-Resolution tracked in minutes.
* **Telemetry Counters:** Live totals for Logs Ingested Today, Trace Spans Today, and System Metrics Today.
* **AI RCA Accuracy Rate:** Verified accuracy percentage of Gemini root-cause syntheses.

#### User Actions:
1. **Drill Down to Incident:** Click any card in the **Recent Critical Incidents** table to jump directly to its Incident Commander view.
2. **Create New Project:** Click the **"+ New Project"** button in the header to spin up an isolated telemetry project.
3. **Switch Environment:** Filter dashboard data by toggling active projects in the sidebar.

---

### 5.2 Incident Queue & Triage (`/incidents`)

A high-density operational queue designed to eliminate alert fatigue.

#### Visual Filters & Controls:
* **Status Filter Buttons:**
  * `ALL`: View all incidents.
  * `CREATED`: Fresh incidents ingested, pending autonomous AI or engineer review.
  * `INVESTIGATING`: Actively undergoing 9-agent LangGraph analysis.
  * `IDENTIFIED`: Root cause identified by Gemini; fix is proposed.
  * `MONITORING`: Fix applied; telemetry monitoring verification phase.
  * `RESOLVED`: Outage closed and archived.
* **Severity Filter:** Filter by `P0 (Critical)`, `P1 (High)`, `P2 (Medium)`, or `P3 (Low)`.
* **Search Input:** Search in real-time by title, deterministic fingerprint hash, service name, or HTTP route.

#### Incident Table Columns:
* **Severity:** Color-coded pill (`P0` red, `P1` orange, `P2` amber, `P3` blue).
* **Title & Endpoint:** Route-normalized incident title (e.g., `TypeError: Cannot read properties of undefined in POST /api/v1/checkout`).
* **Service:** Originating microservice name.
* **Occurrences:** Total deduplicated error count collapsed under this fingerprint.
* **Status Dropdown:** Instant status transition without leaving the list view.
* **Last Seen:** Relative timestamp of the most recent error burst.

---

### 5.3 Incident Commander Detail View (`/incidents/:id`)

The core investigative hub where autonomous AI diagnoses are presented.

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ◀ Back to Incidents   INCIDENT-89412 [P1 - HIGH]   Status: [IDENTIFIED ▼]     Assignee: [Alex M. ▼]     │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 🤖 9-AGENT AUTONOMOUS ROOT CAUSE ANALYSIS (GOOGLE GEMINI 2.5 FLASH)                [⚡ Re-analyze AI]   │
│                                                                                                         │
│ Executive Summary:                                                                                      │
│ Unhandled null dereference in checkout controller causing 500 responses during payment payload parsing. │
│                                                                                                         │
│ Root Cause Diagnosis:                                                                                   │
│ File: controllers/checkoutController.js   Line: 42   Function: parseCustomerPayload()                   │
│ Reason: 'address' object is undefined when customer selects digital delivery.                           │
│                                                                                                         │
│ 🛠️ Recommended Code Patch Diff:                                                 [📋 Copy Code Diff]     │
│ ┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐ │
│ │ - const zip = data.customer.address.zipcode;                                                        │ │
│ │ + const zip = data?.customer?.address?.zipcode ?? '00000';                                          │ │
│ └─────────────────────────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                                         │
│ 🛡️ Long-Term Architectural Guardrail:                                                                  │
│ Enforce Zod runtime schema validation on incoming JSON payloads at the API Gateway level.              │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Multi-Factor Confidence Score: [ 94% - HIGH EVIDENCE ]  (Evaluated across 6 Telemetry Dimensions)       │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ [Stack Trace]  [Trace Spans Waterfall]  [Error Velocity Timeline]  [Team Discussion & Notes]            │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

#### Detailed Subsections:
1. **AI Root Cause Card:**
   * **Executive Summary:** Plain-English summary of the breakdown.
   * **Exact Code Pinpointing:** Exact file path, function signature, and line number identified by the `ExceptionAnalysisAgent`.
   * **Actionable Code Diff:** Unified code patch syntax generated by Gemini with a 1-click **"Copy Code Diff"** button for immediate Git commit.
   * **Architectural Guardrails:** Long-term design patterns to prevent identical future failures.
2. **Confidence Breakdown Meter:**
   * A mathematical evidence score ($0.00$ to $1.00$).
   * Combines evidence weights: Log Volume, Trace Latency, Stack Trace Clarity, Metric Correlation, Git Commit Delta, and Historical RAG Similarity.
3. **Agent Reasoning Tree:**
   * An interactive disclosure showing the exact reasoning path and execution time of each of the 9 LangGraph agents.
4. **Interactive Telemetry Tabs:**
   * **Stack Trace Explorer:** Colorized stack frames with framework/library noise filtered out.
   * **Trace Waterfall:** Visual timeline showing endpoint latency breakdown and bottleneck child spans.
   * **Occurrence Graph:** Time-series histogram tracking failure frequency over time.
   * **Discussion Thread:** Add notes, postmortem thoughts, or tag teammates.
5. **Key Actions:**
   * **"Re-analyze AI" Button:** Forces an immediate re-execution of the 9-node LangGraph pipeline against latest logs.
   * **Status Dropdown:** Update status to `INVESTIGATING`, `IDENTIFIED`, or `RESOLVED`.

---

### 5.4 Microservice Topology & Health (`/services`)

Visual inventory of all registered microservices and dependencies.

* **Interactive Service Graph (`<ServiceMap />`):** Visual node-link diagram illustrating dependencies between upstream and downstream services.
* **Service Inventory Cards:**
  * Status indicator (`HEALTHY` green or `DEGRADED` red).
  * Current P95 latency.
  * Active incident count linked to that service.
  * Connected SDK runtime version.
* **"Refresh Topology" Button:** Re-scans active telemetry streams to discover new endpoints or microservice nodes.

---

### 5.5 Autonomous AI Investigations Audit (`/ai-investigations`)

A historical ledger of every multi-agent investigation executed by Sentinel AI.

* **Audit History Items:**
  * Incident Title and triggering error type.
  * Agent badge: `9-Agent RCA`.
  * Multi-factor confidence score badge (e.g., `94% HIGH`).
  * Root-cause synopsis excerpt.
  * Execution timestamp and duration.
* **Usage:** Click any audit record to jump directly into the full Incident Commander view.

---

### 5.6 Live Log Explorer (`/logs`)

A high-performance log viewer with live streaming and search capabilities.

* **Log Controls:**
  * **Level Filter:** Filter by `ERROR`, `WARN`, `INFO`, or `DEBUG`.
  * **Search Query:** Search by keyword, user ID, or error message.
  * **Refresh Button:** Instantly poll the latest logs from Cloud SQL / BigQuery.
* **Log Row Features:**
  * Timestamp in user's configured timezone.
  * Structured log attributes drawer (click to expand JSON metadata).
  * Trace ID linking (click a Trace ID to view its distributed trace).

---

### 5.7 Performance Metrics & BigQuery ML (`/metrics`)

Deep operational performance analytics with ML-driven predictive forecasting.

* **Latency Percentiles Chart (Area Chart):** Tracks P50, P95, and P99 latency over time in milliseconds.
* **Throughput & Error Velocity (Bar Chart):** Compares total request throughput against error counts per minute.
* **BigQuery ML `ARIMA_PLUS` Integration:**
  * Displays seasonal upper and lower confidence boundaries.
  * Highlights statistical anomalies exceeding 95% confidence intervals before hard thresholds are breached.

---

### 5.8 Knowledge Base & Enterprise RAG (`/knowledge`)

The institutional memory library connecting ChromaDB and Google Vertex AI embeddings (`text-embedding-004`).

#### User Capabilities:
1. **Upload Runbooks & Playbooks:**
   * Click **"+ Upload Document"**.
   * Provide a Title, Category (`runbook`, `playbook`, or `postmortem`), and Markdown/text content.
   * The platform automatically chunks the content and creates 768-dimensional Vertex AI embeddings.
2. **Indexed Documents Inventory:**
   * View all indexed runbooks, chunk counts, and indexing status (`INDEXED` green badge).
3. **Interactive RAG Semantic Search:**
   * Enter natural-language queries (e.g., *"How do we handle Redis connection timeouts?"*).
   * View top-k matching documents with real-time cosine similarity scores.
   * **Why this matters:** When outages occur, the `RAGRetrievalAgent` automatically queries this vector space to supply Gemini with past verified resolutions.

---

### 5.9 Settings & Integrations (`/settings`)

The administrative and configuration engine with 4 specialized tabs:

#### Tab 1: SDK Onboarding (`?tab=sdk`)
* **Technology Selector:** Choose between **Node.js**, **Python**, **Browser JS**, or **Go**.
* **API Key Management:**
  * Click **"Generate Ingestion Key"** to create a cryptographically hashed project API key.
  * **Reveal Secret:** View and copy the full key (only shown once at creation).
  * **Revoke Key:** Revoke compromised keys with instant confirmation modal.
* **Drop-In Code Generator:** Automatically generates copy-paste initialization snippets pre-populated with your project's active API key and endpoint URL.

#### Tab 2: Omnichannel Alerting (`?tab=notifications`)
* **Add Alert Channel Modal:**
  * **Channel Type:** Choose between **Slack**, **Discord**, **Email (Resend/SMTP)**, or **Custom Webhook**.
  * **Target URL / Email:** Paste Slack/Discord webhook URL or destination email.
  * **Minimum Severity Filter:** Choose threshold (`P0 Only`, `P1 and Above`, `P2 and Above`, or `All`).
* **Interactive Actions:**
  * **"Test Notification" Button:** Dispatches a test card with immediate delivery feedback.
  * **Delivery Audit History:** View chronological logs of all outbound alert attempts with HTTP response codes and error details.

#### Tab 3: Organization & Team Governance (`?tab=org`) *(Owner/Admin Only)*
* View all organization members with role badges (`OWNER`, `ADMIN`, `MEMBER`, `VIEWER`).
* Click **"+ Invite Member"** to invite colleagues with role assignment and project scoping.

#### Tab 4: Profile & Security (`?tab=profile`)
* Update your Full Name and display Timezone.
* Change your password with current password verification.

---

## 6. Operator Playbooks & "How-To" Guides

### Playbook 1: Integrating a Microservice with the Sentinel SDK

1. Navigate to **Settings** $\to$ **SDK Onboarding** (`/settings?tab=sdk`).
2. Select your language (e.g., **Python**).
3. Click **"Generate Ingestion Key"**, name it `Payment-Service-Key`, and copy the generated key.
4. Install the SDK in your project:
   ```bash
   pip install sentinelai-telemetry-sdk
   ```
5. Initialize Sentinel in your application entry point:
   ```python
   from sentinelai_sdk import SentinelClient

   sentinel = SentinelClient(
       api_key="sentinel_live_your_key_here",
       endpoint="https://your-sentinel-instance.run.app",
       service_name="payment-service",
       environment="production"
   )

   # Automatically captures uncaught exceptions
   sentinel.init_exception_handler()
   ```
6. Verify connection by visiting **Services** (`/services`) to confirm `payment-service` appears as **HEALTHY**.

---

### Playbook 2: Investigating an Active Incident with Gemini RCA

1. When a production alert fires, click the link in your Discord/Slack card or open **Incidents** (`/incidents`).
2. Click on the active incident to open the **Incident Commander** view (`/incidents/:id`).
3. Review the **Executive Summary** and **Root Cause Diagnosis** for an instant explanation of the failure.
4. Inspect the **Recommended Code Patch Diff**. Click **"Copy Code Diff"** to paste the fix into your local IDE or create a hotfix pull request.
5. Review the **Confidence Score** (e.g., `94% HIGH`).
6. If new logs have arrived, click **"Re-analyze AI"** to instruct Gemini and LangGraph to re-evaluate the latest evidence.
7. Once the patch is deployed, change the status dropdown to **RESOLVED**.

---

### Playbook 3: Setting Up Slack, Discord & Email Alerts

1. Navigate to **Settings** $\to$ **Notifications** (`/settings?tab=notifications`).
2. Click **"+ Add Alert Channel"**.
3. Select **Discord Webhook** and paste your `#production-war-room` webhook URL.
4. Set the severity threshold to **P1** (ensures alerts only trigger for High and Critical outages).
5. Click **"Save Configuration"**.
6. Click the **"Send Test"** paper-airplane icon next to your newly created channel.
7. Verify that the interactive test embed card appears in your Discord channel within 2 seconds.

---

### Playbook 4: Uploading Historical Runbooks to Semantic RAG

1. Navigate to **Knowledge Base** (`/knowledge`).
2. Click **"+ Upload Document"**.
3. Set Title to `Postmortem: Database Connection Pool Exhaustion`.
4. Set Type to `runbook`.
5. Paste your Markdown resolution instructions (e.g., optimal pool sizing formulas, connection timeout settings).
6. Click **"Upload & Index"**.
7. Test retrieval by typing *"How to resolve pool timeout"* into the RAG Search bar to confirm the document returns with a high similarity score ($> 0.85$).

---

## 7. User Access & Permissions Matrix

| Feature / Action | OWNER | ADMIN | MEMBER | VIEWER |
|---|:---:|:---:|:---:|:---:|
| **View Dashboard, Incidents, Logs & Metrics** | ✅ | ✅ | ✅ | ✅ |
| **Change Incident Status (e.g. to RESOLVED)** | ✅ | ✅ | ✅ | ❌ |
| **Trigger "Re-analyze with AI"** | ✅ | ✅ | ✅ | ❌ |
| **Add Comments & Team Notes to Incidents** | ✅ | ✅ | ✅ | ❌ |
| **Upload Runbooks & Documents to RAG** | ✅ | ✅ | ✅ | ❌ |
| **Generate & View Project SDK API Keys** | ✅ | ✅ | ❌ | ❌ |
| **Revoke SDK API Keys** | ✅ | ✅ | ❌ | ❌ |
| **Add & Test Notification Channels (Slack/Discord)**| ✅ | ✅ | ❌ | ❌ |
| **Delete Notification Channels** | ✅ | ✅ | ❌ | ❌ |
| **Invite New Team Members to Organization** | ✅ | ✅ | ❌ | ❌ |
| **Change Member Roles or Remove Members** | ✅ | ❌ | ❌ | ❌ |
| **Delete Organization or Projects** | ✅ | ❌ | ❌ | ❌ |

---

## 8. Frequently Asked Questions & Troubleshooting

### Q: Why is an incident status showing "INVESTIGATING"?
**A:** When a new error fingerprint is detected, the 9-node LangGraph workflow automatically launches. This status indicates the agents are actively parsing traces, calculating latency percentiles, and generating the Gemini RCA report. Investigation typically finishes in under 25 seconds.

### Q: How does route normalization prevent alert storms?
**A:** Sentinel AI automatically detects dynamic path segments (e.g., UUIDs, numeric IDs, hashes) and transforms routes such as `/api/v1/users/e3b0c442.../orders/194` into `/api/v1/users/{id}/orders/{id}`. It hashes this normalized path with the exception type and top stack frame, ensuring 10,000 requests to different customer accounts collapse into a single incident.

### Q: What does a "Low Confidence Score" mean?
**A:** A score below `0.60 (LOW)` occurs when telemetry signals are incomplete — for example, if an error occurred without associated trace spans, or if the stack trace lacks user code frames. The RCA will still be synthesized, but engineers should verify the root cause manually.

### Q: How do I export or share an RCA report?
**A:** Every incident has a permanent URL (`/incidents/<id>`). In addition, notification cards sent to Slack, Discord, and Email include a direct deep-link and an executive summary ready for immediate executive reporting.
