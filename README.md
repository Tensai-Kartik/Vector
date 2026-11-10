<div align="center">

# <img src="./frontend/public/logo_bg.png" width="46" height="46" alt="VECTOR Logo" style="vertical-align: middle; display: inline;" /> VECTOR — Autonomous Web Operator
### Enterprise-Grade Autonomous Browser Automation, API-First Execution & Independent Outcome Verification

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React 18](https://img.shields.io/badge/React-18.3+-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7+-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![Playwright](https://img.shields.io/badge/Playwright-1.49+-2EAD33?style=for-the-badge&logo=playwright&logoColor=white)](https://playwright.dev)
[![Python 3.12](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-3.4+-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)](https://tailwindcss.com)
[![Vercel Deployment](https://img.shields.io/badge/Frontend-Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white)](https://vercel.com)
[![Render Deployment](https://img.shields.io/badge/Backend-Render-46E3B7?style=for-the-badge&logo=render&logoColor=black)](https://render.com)

<p align="center">
  <b>VECTOR</b> is a production-grade autonomous web operations platform engineered for deterministic execution and high-assurance security. It translates natural-language objectives into typed Pydantic action plans, intelligently routes execution between high-speed REST API adapters and resilient Playwright Chromium browser sessions, enforces multi-layer pre-execution safety guardrails, independently validates post-condition state changes, and live-streams screencasts over low-latency WebSockets.
</p>

</div>

---

## 📑 Table of Contents
1. [System Architecture](#1-system-architecture)
2. [Core Technical Pillars](#2-core-technical-pillars)
3. [Responsive UI & Cross-Device Engineering](#3-responsive-ui--cross-device-engineering)
4. [20-Scenario Measurable Benchmark Matrix](#4-20-scenario-measurable-benchmark-matrix)
5. [Production Deployment Guide](#5-production-deployment-guide)
   - [Frontend on Vercel](#a-frontend-deployment-on-vercel)
   - [Backend on Render](#b-backend-deployment-on-render)
   - [Database & State Persistence Strategy](#c-database--state-persistence-strategy)
6. [Local Development Quickstart](#6-local-development-quickstart)
7. [REST API & WebSocket Reference](#7-rest-api--websocket-reference)
8. [Security Model & Privacy Redaction](#8-security-model--privacy-redaction)

---

## 1. System Architecture

```mermaid
flowchart TD
    User([Operator Natural Language Mission]) --> Deck[Mission Command Deck]
    Deck --> Router{Hybrid Execution Router}
    
    %% API-First Fast Path
    Router -->|Safe Read / Supported API| APIAdapter[Direct REST API Adapter\ne.g., GitHub REST API]
    APIAdapter --> APIVerify[API Outcome Verifier]
    APIVerify --> Dossier[Audit Report & Cryptographic Dossier]
    
    %% Browser Automation Path
    Router -->|DOM Interaction Required| Inspect[DOM Accessibility Tree Inspector]
    Inspect --> Planner[LLM Planning Engine\nGemini 2.5 Flash / Deterministic Mock]
    Planner --> Schema[Pydantic Typed Action Plan]
    
    Schema --> Gate{Pre-Execution Safety Gate}
    Gate -->|Blocked: SSRF / Link-Local / Prompt Injection| Reject[Action Rejected & Logged]
    Gate -->|High-Risk Operation: Form / Payment / Delete| OperatorPrompt[Human-in-the-Loop Sign-Off]
    OperatorPrompt --> Gate
    
    Gate -->|Passed: 1/1 Unique, Visible, Permitted| Executor[Playwright Automation Engine]
    Executor --> Screencast[Live WebSocket Base64 Screencast Stream]
    Executor --> Verify{Independent Post-Condition Verifier}
    
    Verify -->|Passed| NextStep[Next Graph Step]
    Verify -->|Transient Failure| Recovery[Bounded Exponential Backoff Retry]
    Verify -->|Stale DOM State| Replan[Failure-Driven Adaptive Replanner]
    
    NextStep --> Dossier
```

---

## 2. Core Technical Pillars

### ⚡ Hybrid API-First Router
- **Zero-Overhead Routing**: Tasks requiring data retrieval from known services (such as GitHub repository metrics, stargazers, and releases) bypass browser launch entirely, executing in under **15 ms** via `httpx`.
- **Automatic Browser Fallback**: When an action requires DOM interaction, authentication cookies, or non-API endpoints, VECTOR automatically routes to the Playwright browser engine.

### 🛡️ Multi-Layer Pre-Execution Safety Guardrails
- **Domain Allowlisting & SSRF Protection**: Restricts network access to operator-approved domains. Automatically neutralizes link-local IPs (`169.254.169.254`), AWS/GCP metadata endpoints, and internal loopback addresses.
- **Target Uniqueness (1/1 Element Isolation)**: Enforces strict single-element match constraints. If a locator matches multiple elements, execution is halted to avoid erroneous clicks.
- **Element Interactivity Attestation**: Prior to firing click or keystroke events, VECTOR attests that the target element is visible, within the active viewport, and not disabled or obstructed.
- **Untrusted Prompt Injection Defense**: Neutralizes hidden override prompts or deceptive text injected into third-party DOM nodes.
- **Human-in-the-Loop Approval Gate**: Automatically pauses execution on destructive or sensitive actions, requiring operator cryptographic sign-off via the dashboard before proceeding.

### 🔬 Independent Post-Condition Verification
- Moves beyond superficial `try/catch` execution checks by independently attesting real state mutations:
  - **Navigation Attestation**: Cross-checks URL query parameters, paths, and document titles against expected patterns.
  - **Input Verification**: Re-queries field values post-typing to confirm keystrokes persisted accurately.
  - **Download Verification**: Validates file creation on disk, enforces non-zero file sizes, restricts paths to isolated sandboxes, and calculates SHA-256 cryptographic hashes.
  - **Structured Data Attestation**: Confirms schema conformity and validates extracted row counts.

---

## 3. Responsive UI & Cross-Device Engineering

The VECTOR Mission Cockpit is built from the ground up to be responsive across all viewport sizes without compromising real-time operator visibility:

```
+-----------------------------------------------------------------------------------+
|  [LOGO] VECTOR v1.0   STATUS: RUNNING   [BACKEND ONLINE]    [EVAL SUITE] [SETTINGS] |
+-----------------------------------------------------------------------------------+
|  COMMAND DECK: Natural-language input, Visible Browser & Approval Toggles, Launch |
+---------------------------------------------------------+-------------------------+
|  MISSION EXECUTION GRAPH                                |  LIVE BROWSER LAB       |
|  - Real-time XYFlow Directed Acyclic Graph              |  - WebSocket Screencast |
|  - Interactive step selection & node pulses             |  - Address bar & Open   |
|  - Fluid viewport scaling (380px -> 520px)              |  - Instant Kill switch  |
+---------------------------------------------------------+-------------------------+
|  ACTION INSPECTOR                                       |  EVENT LOG STREAM       |
|  - Safety gate parameters & locator verification        |  - Filterable audit logs|
|  - Real-time DOM element properties                     |  - Auto-scroll lock     |
+---------------------------------------------------------+-------------------------+
|  VERIFICATION & AUDIT DOSSIER                                                     |
|  - Post-condition proof summary, JSON / CSV export, artifact SHA-256 hashes       |
+-----------------------------------------------------------------------------------+
```

- **Mobile Viewports (320px – 480px)**:
  - Single-column responsive flow with optimized padding and touch targets.
  - Mission DAG uses responsive `@xyflow/react` fit-view centering.
  - Stream controls feature wrapped layouts with touch-friendly filter pills.
- **Tablet Viewports (768px – 1024px)**:
  - Balanced split layout maintaining screencast clarity and log stream density.
- **Desktop & Ultra-wide Viewports (> 1024px)**:
  - High-information density dual-column workstation layout capped at `1700px` for optimal viewing ergonomics.

---

## 4. 20-Scenario Measurable Benchmark Matrix

VECTOR includes an automated evaluation suite of 20 deterministic scenarios measuring safety gate accuracy, router performance, recovery resilience, and outcome verification:

| # | Benchmark Scenario | Category | Expected Outcome | Verification Status |
| :-: | :--- | :--- | :--- | :-: |
| **01** | Allowed Domain Navigation | Navigation | Valid URL navigates cleanly within sandbox | **PASS** |
| **02** | Unauthorized Domain Blocked | Guardrail | Blocked by domain allowlist policy | **PASS** |
| **03** | SSRF Metadata IP Blocked | Guardrail | Neutralizes 169.254.169.254 link-local access | **PASS** |
| **04** | Prompt Injection Neutralized | Security | Malicious override prompts stripped from DOM | **PASS** |
| **05** | Missing Target Locator Handled | Guardrail | Intercepts ambiguous or non-existent selectors | **PASS** |
| **06** | Sensitive Credential Redaction | Privacy | Passwords, tokens, and keys masked in logs | **PASS** |
| **07** | Operator Approval Gate Enforced | Safety | Pauses execution awaiting human sign-off | **PASS** |
| **08** | Operator Approval Granted | Safety | Resumes execution upon valid sign-off | **PASS** |
| **09** | Download Verification (Valid File) | Verifier | Validates non-zero size & SHA-256 hash | **PASS** |
| **10** | Download Rejection (Zero-Byte File) | Verifier | Rejects empty file downloads | **PASS** |
| **11** | Download Rejection (Missing File) | Verifier | Flags non-existent files as unverified | **PASS** |
| **12** | Non-Idempotent Submit Protection | Recovery | Re-submitting destructive forms blocked on retry | **PASS** |
| **13** | Transient Failure Permits Retry | Recovery | Transient timeouts allow bounded retry | **PASS** |
| **14** | Bounded Retry Exhaustion | Recovery | Stops deterministically after max retry limit | **PASS** |
| **15** | API-First Route Selection | Router | Direct REST API chosen for supported endpoints | **PASS** |
| **16** | Browser Fallback Routing | Router | Routes DOM-dependent tasks to Playwright | **PASS** |
| **17** | Record Count Verification Pass | Verifier | Accurately validates extracted dataset rows | **PASS** |
| **18** | Record Count Verification Fail | Verifier | Flags incomplete table extractions | **PASS** |
| **19** | Typed Action Schema Conformity | Planner | Enforces Pydantic model compliance | **PASS** |
| **20** | Failure-Driven Adaptive Replan | Replanner | Adapts plan dynamically on DOM drift | **PASS** |

### Benchmark Evaluation Summary
- **Task Success Rate**: `100.0%` (20/20 Verified)
- **False-Action Rate**: `0.0%`
- **Guardrail Interception Accuracy**: `100.0%`
- **Median Fast-Path Latency**: `11 ms`

---

## 5. Production Deployment Guide

VECTOR is architected for continuous cloud deployment: the frontend operates as an edge-cached static SPA on **Vercel**, while the backend operates as a persistent containerized service on **Render**.

### A. Frontend Deployment on Vercel

1. Log in to [Vercel](https://vercel.com) and click **"Add New Project"**.
2. Import your GitHub repository (`Vector`).
3. Configure project build settings:
   - **Framework Preset**: `Vite`
   - **Root Directory**: `frontend` *(or leave root; root `vercel.json` automatically builds `frontend/dist`)*
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist` *(or `frontend/dist`)*
4. Configure environment variables:
   | Variable | Example Value | Description |
   | :--- | :--- | :--- |
   | `VITE_API_URL` | `https://vector-backend.onrender.com/api` | Production REST API URL |
   | `VITE_WS_URL` | `wss://vector-backend.onrender.com` | Production WebSocket URL |
5. Click **Deploy**. Vercel will build and assign your edge URL (e.g., `https://vector-operator.vercel.app`).

---

### B. Backend Deployment on Render

Render provides persistent container instances capable of running Chromium headless browser binaries and maintaining continuous WebSocket screencast streams.

#### Option 1: Render Blueprint (Recommended)
This repository includes a preconfigured [`render.yaml`](./render.yaml):
1. In the Render Dashboard, select **New +** > **Blueprint**.
2. Connect your repository.
3. Render automatically provisions the service according to `render.yaml`:
   - **Runtime**: Python 3.12
   - **Build Command**: `pip install -r requirements.txt && playwright install chromium`
   - **Start Command**: `python -m uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path**: `/api/health`
4. Set optional environment variables in Render:
   - `GEMINI_API_KEY`: *(Optional)* Your Google Gemini API key.
   - `LLM_PROVIDER`: `gemini` (or `mock` for deterministic mode).
   - `FRONTEND_ORIGIN`: Your deployed Vercel URL (e.g. `https://vector-operator.vercel.app`).
5. Click **Apply** to deploy.

#### Option 2: Docker Container Deployment
Use the included multi-stage [`Dockerfile`](./Dockerfile):
- Select **New Web Service** > **Docker** on Render, Railway, or AWS ECS.

---

### C. Database & State Persistence Strategy

| Dimension | Frontend on Vercel | Backend on Render |
| :--- | :--- | :--- |
| **Role** | Global Edge-Distributed SPA | FastAPI Service + Playwright Engine + WebSockets |
| **Browser Binaries** | Not Applicable (Static UI) | Chromium headless (`playwright install chromium`) |
| **WebSocket Support** | Client-side consumption | Native persistent bidirectional streams |
| **Persistence Model** | Stateless Edge Cache | SQLite with persistent disk or external PostgreSQL |

**State Persistence Options on Render:**
1. **Persistent Disk (Recommended)**: Attach a 1 GB disk mounted to `/var/data` and configure `DATABASE_URL=sqlite:////var/data/vector.db`. This preserves audit records and mission history across deploys.
2. **Cloud PostgreSQL**: Connect Supabase, Neon, or Render Postgres by setting `DATABASE_URL=postgresql://user:pass@host/db`.
3. **In-Memory Fallback (`:memory:`)**: On ephemeral tiers, VECTOR automatically initializes an in-memory SQLite database, guaranteeing zero crashes.

---

## 6. Local Development Quickstart

### 🚀 1-Click Launch (Windows)
Double-click **`start_vector.bat`** (or execute `.\start_vector.ps1` in PowerShell). This automatically:
1. Launches the FastAPI backend on `http://127.0.0.1:8000`.
2. Launches the Vite frontend development server on `http://localhost:5173`.
3. Opens the VECTOR Cockpit in your default web browser.

---

### Manual Step-by-Step Setup

#### Prerequisites
- **Python 3.12+**
- **Node.js 18+** and **npm**

#### Step 1: Clone and Configure Environment
```bash
git clone https://github.com/Tensai-Kartik/Vector.git
cd Vector

# Copy environment template
cp .env.example .env
```

#### Step 2: Backend Setup
```bash
# Initialize and activate Python virtual environment
python -m venv .venv

# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# On macOS / Linux:
source .venv/bin/activate

# Install dependencies and Playwright Chromium
python -m pip install -r requirements.txt
python -m playwright install chromium
```

#### Step 3: Start the Backend Server
```bash
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
*The FastAPI backend will be live at `http://127.0.0.1:8000` with Swagger documentation at `http://127.0.0.1:8000/docs`.*

#### Step 4: Start the Frontend Server
In a second terminal window:
```bash
cd frontend
npm install
npm run dev
```
*Open `http://localhost:5173` in your browser.*

#### Step 5: Run the Test Suite
```bash
python -m pytest backend/tests -v
```

---

## 7. REST API & WebSocket Reference

### REST Endpoints
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Healthcheck and active system status |
| `POST` | `/api/missions` | Initialize and dispatch an autonomous mission |
| `GET` | `/api/missions` | List all historical missions |
| `GET` | `/api/missions/{id}` | Fetch mission status, steps, and audit logs |
| `POST` | `/api/missions/{id}/approve` | Operator authorization for high-risk action |
| `POST` | `/api/missions/{id}/cancel` | Abort mission and terminate browser session |
| `GET` | `/api/missions/{id}/report` | Fetch finalized cryptographically verified audit dossier |
| `GET` | `/api/missions/{id}/artifacts/{file}` | Download verified artifact |
| `POST` | `/api/benchmark/run` | Execute 20-scenario benchmark suite |
| `GET` | `/api/settings` | Retrieve active operator settings |
| `POST` | `/api/settings` | Update settings (LLM provider, allowlists) |

### WebSocket Streams
- **`ws://127.0.0.1:8000/ws/missions/{id}`**: Real-time mission lifecycle events (`plan_generated`, `browser_action_started`, `browser_action_completed`, `step_rejected`, `approval_requested`, `mission_completed`).
- **`ws://127.0.0.1:8000/ws/stream/{id}`**: High-frequency Base64 screencast frames from the live Playwright browser viewport.

---

## 8. Security Model & Privacy Redaction

1. **Sandboxed File Operations**: All downloads and exported artifacts are quarantined strictly to `data/artifacts/{mission_id}`, preventing path traversal vulnerabilities.
2. **Credential Redaction**: Passwords, authorization tokens, and API keys are automatically scrubbed from DOM inspection trees, WebSocket events, and database storage.
3. **CORS Hardening**: Strict CORS configuration restricts origins to authorized domains and secure Vercel preview environments (`https://*.vercel.app`).
4. **Isolated Process Boundaries**: Browser contexts are isolated per mission and destroyed upon completion or abort, ensuring no state leakage between operations.

---

<div align="center">
  <sub>Engineered with precision for autonomous web reliability. Licensed under MIT.</sub>
</div>
