# 🛡️ API Sentinel – API Monitoring & Health Analytics Platform

[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.15-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/flask-3.1.3-black.svg?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-red.svg?logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57.svg?logo=sqlite&logoColor=white)](https://sqlite.org/)
[![Chart.js](https://img.shields.io/badge/Chart.js-4.x-FF6384.svg?logo=chartdotjs&logoColor=white)](https://www.chartjs.org/)
[![Tests](https://img.shields.io/badge/pytest-27%20passed-success.svg?logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **API Sentinel** is an enterprise-grade, full-stack REST API monitoring, uptime intelligence, and health analytics platform built with **Python, Flask, SQLAlchemy, SQLite, and vanilla ES6+ with Chart.js**. Designed for DevOps engineers, software architects, and backend teams to track real network probes, detect outages instantly, measure latency percentiles, and analyze service reliability.

---

## 📑 Table of Contents

- [📌 Overview](#-overview)
- [🖼️ Screenshots & UI Showcase](#️-screenshots--ui-showcase)
- [🚀 Key Features](#-key-features)
- [🏗️ System Architecture](#️-system-architecture)
- [🛠️ Technology Stack](#️-technology-stack)
- [📂 Project Structure](#-project-structure)
- [💻 Installation & Local Setup](#-installation--local-setup)
- [🌱 Quick Start & One-Click Demo Seeder](#-quick-start--one-click-demo-seeder)
- [📡 REST API Documentation](#-rest-api-documentation)
- [🔒 Security & SSRF Defense Architecture](#-security--ssrf-defense-architecture)
- [🧪 Testing & Quality Assurance](#-testing--quality-assurance)
- [🚢 Production Deployment](#-production-deployment)
- [📄 License](#-license)

---

## 📌 Overview

Unlike toy dashboards with hardcoded or synthetic data, **API Sentinel performs real HTTP probes, records real network telemetry directly in an SQLite database, and computes mathematically accurate statistics** in real time:

- **100% Real Network Probes**: Dispatches live HTTP requests (`GET`, `POST`, `PUT`, `DELETE`, `PATCH`, `HEAD`) with sub-millisecond precision timing via `time.perf_counter()`.
- **Zero Fabricated Metrics**: All KPIs (Uptime %, Healthy / Degraded / Down counts, Average Latency, P95 Percentile) derive directly from SQLite database records.
- **Enterprise-Grade SSRF Protection**: Multi-layered IP filter blocks loopback, RFC 1918 private subnets, and cloud instance metadata endpoints (`169.254.169.254`).
- **Credential Protection**: Masks sensitive headers (`Authorization: Bearer ••••`, API keys) in API responses and frontend cards while preserving raw secrets across edits.
- **Clean Single-Page Application (SPA)**: Lightweight vanilla ES6+ JavaScript client with dark/light themes, dynamic polling, Chart.js visualizations, and instant toast notifications.

---

## 🖼️ Screenshots & UI Showcase

### 1. Executive Dashboard (Dark Theme)
```
+-----------------------------------------------------------------------------------------------+
|  [🛡️ API SENTINEL]   Dashboard   Endpoints   Analytics   Incidents   |  [Auto-Refresh: 10s] ☀️ 🌙|
+-----------------------------------------------------------------------------------------------+
|  [Total APIs]    [Healthy APIs]    [Degraded APIs]    [Failed APIs]    [System Latency]   [Uptime] |
|       6               4                 1                  1               185.6 ms        76.4%   |
+-----------------------------------------------------------------------------------------------+
|  LATENCY TIMELINE (Recent 30 Probes)                 |  HTTP STATUS DISTRIBUTION              |
|   ms ^                                               |                                        |
|  250 |       /\                                      |       2xx Success   [============] 753 |
|  150 |  _/\_/  \__/\_                                |       4xx Client    [==]            91 |
|   50 |________________                               |       5xx Server    [===]          138 |
|      +-------------------> Time                      |       Network Error [=]             13 |
+-----------------------------------------------------------------------------------------------+
|  LIVE HEALTH CHECK ACTIVITY FEED                                                              |
|  Status   Endpoint Name             HTTP Code   Latency    Checked At           Result        |
|  [OK]     GitHub Public Status      200 OK      185.58 ms  Just now             Healthy       |
|  [FAIL]   HTTPBin Failure (500)     500 Error   876.23 ms  1 min ago            Down          |
|  [WARN]   HTTPBin Delayed Check     200 OK     2727.90 ms  2 mins ago           Degraded      |
+-----------------------------------------------------------------------------------------------+
```

### 2. Monitored Endpoints Grid & Management
```
+-----------------------------------------------------------------------------------------------+
|  Filter: [ All Statuses v ]   [ All Methods v ]   [ Search endpoints... ]     [+ Add Endpoint] |
+-----------------------------------------------------------------------------------------------+
|  +-------------------------------------+  +-------------------------------------+             |
|  | [200 OK]  GitHub API Root     [GET] |  | [200 OK]  JSONPlaceholder    [GET]  |             |
|  | https://api.github.com              |  | https://jsonplaceholder.typicode... |             |
|  | Tags: prod, github                  |  | Tags: test, live                    |             |
|  | Uptime: 99.8%  | Latency: 171.3 ms  |  | Uptime: 100.0% | Latency: 70.7 ms   |             |
|  | [ Check Now ] [ Analytics ] [Edit]  |  | [ Check Now ] [ Analytics ] [Edit]  |             |
|  +-------------------------------------+  +-------------------------------------+             |
+-----------------------------------------------------------------------------------------------+
```

---

## 🚀 Key Features

### 1. 📊 Executive Dashboard
- **Key Performance Indicators (KPIs)**: Total Monitored APIs (Active vs. Paused breakdown), Healthy, Degraded (latencies $> 1200\text{ms}$), and Down counts.
- **System Uptime & Latency**: Dynamically computed from database ping records ($\frac{\text{Successful Checks}}{\text{Total Checks}} \times 100$).
- **Spline Latency Trend**: 30-sample interactive line chart tracking real-time network jitter.
- **HTTP Status Distribution**: Doughnut visualization categorizing 2xx, 3xx, 4xx, 5xx, and Network Errors.
- **Live Activity Feed**: Streaming audit trail of probe outcomes with status codes and failure diagnostics.

### 2. ⚙️ Robust Endpoint Management
- **Full CRUD Operations**: Create, edit, inspect, and delete monitored endpoints.
- **Configurable HTTP Methods**: `GET`, `POST`, `PUT`, `DELETE`, `PATCH`, `HEAD`.
- **Custom Request Payloads**: JSON body editing for write requests (`POST`, `PUT`, `PATCH`).
- **Flexible Headers**: Custom key-value request headers with quick presets (`Bearer Token`, `API Key`, `Content-Type: application/json`).
- **Granular Thresholds**: Custom request timeouts ($1 - 60\text{s}$), expected HTTP status codes, check frequencies ($10\text{s} - 1\text{h}$), and tags.
- **Active / Paused States**: Pause monitoring anytime without losing historical telemetry.

### 3. 🔍 Real-Time Health Probing Engine
- **Microsecond Precision**: Measures network round-trip time using Python `time.perf_counter()`.
- **Diagnostic Classification**: Differentiates between DNS failures, connection timeouts, SSL certificate verification issues, connection refusals, and HTTP code mismatches.
- **Manual "Check Now"**: Immediate on-demand probe triggering with live feedback and toast notifications.
- **Batch "Check All"**: Parallelized on-demand health verification across all active endpoints.
- **Automated Background Scheduler**: Built-in multi-threaded daemon that checks active endpoints according to their individual intervals.

### 4. 📈 Deep-Dive Analytics & Benchmarking
- **Endpoint Profiles**: Filter historical performance by 1 Hour, 24 Hours, 7 Days, or 30 Days.
- **Statistical Percentiles**: Minimum, Average, Maximum, and **P95 Latency** (95th percentile) calculations.
- **Benchmark Comparison**: Comparative ranking of all endpoints by uptime %, average response speed, and failure rate.

### 5. 🚨 Incident Lifecycle & Recovery Tracking
- **Automatic Incident Creation**: Instantly generates an open `Incident` when an endpoint fails.
- **Automatic Recovery**: Resolves incidents automatically when subsequent checks succeed.
- **Downtime Calculation**: Calculates total outage duration down to the second.
- **Zero Ghost Outages**: Pausing a failing endpoint cleanly resolves active incidents with user annotations.

### 6. 🔒 Enterprise Security & SSRF Protection
- **Multi-Tier SSRF Shield**: Pre-flight DNS resolution prevents probing internal subnets (`127.0.0.1`, RFC 1918 `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, AWS/GCP metadata `169.254.169.254`).
- **Masked Secrets**: Headers containing tokens or passwords display as masked bullets (`eyJh...••••...c0de`) in UI and API output, preventing token leakage.
- **Safe Merging**: Editing an endpoint with masked headers safely preserves the raw credential in the database.

### 7. 📥 Data Export & Accessibility
- **CSV Reports**: Export Endpoints Summary and Granular Check History logs (up to 1,000 records).
- **Persistent Theme Engine**: Dark & Light mode toggle with `localStorage` memory.
- **One-Click Demo Seeder**: Load 5 realistic test APIs instantly to explore features.

---

## 🏗️ System Architecture

```
+----------------------------------------------------------------------------------+
|                                CLIENT BROWSER                                    |
|   Vanilla ES6+ SPA  |  Chart.js 4.x  |  CSS3 Variable Design Tokens  |  Toasts   |
+----------------------------------------+-----------------------------------------+
                                         | HTTP / JSON REST APIs
                                         v
+----------------------------------------------------------------------------------+
|                                FLASK APP FACTORY                                 |
|                                                                                  |
|   [Web Blueprint]              [API Blueprint]               [Security Guard]    |
|   - GET / (UI)                 - CRUD /api/endpoints         - SSRF & IP Filter  |
|   - GET /health                - POST /check /toggle         - Header Masking    |
|                                - GET /stats /analytics       - Input Validator   |
+--------------------+-----------------------------------+-------------------------+
                     |                                   |
                     v                                   v
+------------------------------------+  +------------------------------------------+
|     BACKGROUND MONITOR WORKER      |  |         SQLAlchemy ORM (SQLite 3)        |
|  - Multi-threaded check loop       |  |  - Endpoint (URL, method, headers)       |
|  - time.perf_counter() latency     |  |  - CheckResult (status, latency, code)   |
|  - Incident resolution & creation  |  |  - Incident (downtime lifecycle)         |
|  - Foreign Key PRAGMA enforcement  |  |  - Foreign Keys & Cascade Deletes ON     |
+--------------------+---------------+  +------------------------------------------+
                     |
                     v (Actual HTTP Probes)
+----------------------------------------------------------------------------------+
|                         EXTERNAL REMOTE REST APIS                                |
|          https://api.github.com  |  https://jsonplaceholder.typicode.com         |
+----------------------------------------------------------------------------------+
```

---

## 🛠️ Technology Stack

| Component | Technology | Version | Purpose |
|---|---|---|---|
| **Backend Framework** | Python / Flask | 3.1.3 | High-throughput WSGI application and REST API |
| **ORM** | SQLAlchemy / Flask-SQLAlchemy | 2.0+ / 3.1.1 | Relational database abstraction and migrations |
| **Database** | SQLite 3 | Embedded | Local ACID storage with Foreign Key PRAGMA enforcement |
| **HTTP Client** | Requests | 2.31+ | High-precision HTTP probe engine |
| **Frontend Framework** | HTML5 / CSS3 / ES6+ | Modern | Frameworkless, dependency-free responsive SPA |
| **Visualizations** | Chart.js | 4.4.1 | Reactive spline latency graphs and status doughnut charts |
| **WSGI Server** | Gunicorn | 21.2+ | Production-grade multi-worker application server |
| **Test Framework** | Pytest | 8.x / 9.x | Comprehensive unit and integration test suite |

---

## 📂 Project Structure

```
api-sentinel/
├── app/
│   ├── __init__.py           # Application Factory, SQLite PRAGMA & scheduler lifecycle
│   ├── config.py             # Environment configurations (Dev, Test, Prod)
│   ├── extensions.py         # SQLAlchemy instance singleton
│   ├── models/
│   │   ├── __init__.py       # Model exports
│   │   ├── endpoint.py       # Monitored API Endpoint model with header masking
│   │   ├── check_result.py   # Historical ping telemetry record model
│   │   └── incident.py       # Outage incident lifecycle model
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── api.py            # RESTful API routes (CRUD, stats, checks, CSV)
│   │   └── web.py            # Web interface & service health probes
│   ├── services/
│   │   ├── __init__.py
│   │   ├── analytics.py      # Statistical calculations, percentiles, CSV exports
│   │   ├── monitor.py        # Real HTTP probe dispatcher & metric recorder
│   │   ├── scheduler.py      # Background daemon thread monitoring worker
│   │   └── security.py       # SSRF prevention, IP filtering, header secret preservation
│   ├── static/
│   │   ├── css/
│   │   │   ├── main.css      # SaaS design system, CSS variables & theme tokens
│   │   │   └── components.css# Badges, cards, tables, modals, toasts, loaders
│   │   └── js/
│   │       ├── app.js        # Core SPA router, theme switcher, demo seeder
│   │       ├── dashboard.js  # Dashboard KPIs & Chart.js graph controllers
│   │       ├── endpoints.js  # Endpoints CRUD, modal management & filters
│   │       ├── analytics.js  # Latency percentile calculations & comparison table
│   │       └── incidents.js  # Incident log rendering & duration viewer
│   └── templates/
│       └── index.html        # Responsive Single Page Application interface
├── scripts/
│   └── verify_live_monitoring.py # Standalone live JSONPlaceholder verification script
├── tests/
│   ├── conftest.py           # In-memory SQLite fixtures & mock DNS resolutions
│   ├── test_models.py        # Model creation, masking, and cascade delete tests
│   ├── test_security.py      # SSRF prevention, IP filtering & input validation tests
│   ├── test_monitor.py       # Health check execution, timeouts & errors tests
│   ├── test_api_routes.py    # REST API CRUD, secret preservation & toggle tests
│   └── test_analytics.py     # Uptime %, average latency & percentile math tests
├── .env.example              # Sample environment configuration template
├── .gitignore                # Comprehensive Git exclusion rules
├── gunicorn.conf.py          # Production WSGI server settings
├── Procfile                  # Render / Heroku process declaration
├── render.yaml               # Render cloud deployment blueprint
├── requirements.txt          # Python package dependencies
├── run.py                    # Application launch entry point
└── README.md                 # Project documentation
```

---

## 💻 Installation & Local Setup

### Prerequisites
- **Python**: Version `3.10` or higher installed.
- **Git**: Installed on your system.

### Step 1: Clone the Repository
```bash
git clone https://github.com/your-username/api-sentinel.git
cd api-sentinel
```

### Step 2: Set Up Virtual Environment

**On Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Copy the template configuration file:
```bash
# Linux / macOS
cp .env.example .env

# Windows
copy .env.example .env
```

Default settings in `.env.example`:
| Variable | Default Value | Description |
|---|---|---|
| `FLASK_ENV` | `development` | Environment mode (`development`, `production`, `testing`) |
| `FLASK_DEBUG` | `1` | Enable Flask auto-reloading in development |
| `SECRET_KEY` | `dev-secret-key...` | Cryptographic secret for sessions and cookies |
| `DATABASE_URL` | `sqlite:///instance/api_sentinel.db` | SQLite database file location |
| `ENABLE_BACKGROUND_SCHEDULER` | `true` | Run automated background check thread |
| `SCHEDULER_INTERVAL_SECONDS` | `10` | Frequency of background scheduler sweep |
| `ALLOW_LOCAL_MONITORING` | `false` | Allow monitoring `localhost` (set `true` only for dev) |
| `PORT` | `5000` | Port for the web server |
| `HOST` | `127.0.0.1` | Network interface host |

### Step 5: Start the Platform
```bash
python run.py
```

The SQLite database and tables will be initialized automatically in `instance/api_sentinel.db`.

Access the web interface at **[http://localhost:5000](http://localhost:5000)**.

---

## 🌱 Quick Start & One-Click Demo Seeder

When launching on a clean database, click the **"Load 5 Demo Test APIs"** button on the empty state banner to immediately populate realistic public test APIs:

1. **GitHub Public Status** (`https://api.github.com` - Healthy 200)
2. **HTTPBin Success** (`https://httpbin.org/status/200` - Healthy 200)
3. **JSONPlaceholder Posts** (`https://jsonplaceholder.typicode.com/posts/1` - Fast 200)
4. **Delayed Latency Simulator** (`https://httpbin.org/delay/2` - Degraded $> 1200\text{ms}$)
5. **HTTP 500 Failure Simulator** (`https://httpbin.org/status/500` - Down / Active Incident)

Within seconds, the dashboard charts and metrics will populate with real network telemetry.

---

## 📡 REST API Documentation

All API endpoints return JSON in the standardized format:
```json
{
  "success": true,
  "data": { ... },
  "message": "Operation description"
}
```

### 1. Dashboard & Analytics

#### `GET /api/dashboard/stats`
Fetches aggregated KPIs, 30-probe latency trend, and status code distribution.
```bash
curl -s http://localhost:5000/api/dashboard/stats
```

#### `GET /api/analytics/endpoint/<id>?hours=24`
Returns detailed latency percentiles (Min, Avg, Max, P95) and historical probe data for an endpoint.
```bash
curl -s "http://localhost:5000/api/analytics/endpoint/1?hours=24"
```

#### `GET /api/analytics/comparison`
Returns comparative benchmark rankings across all monitored endpoints.
```bash
curl -s http://localhost:5000/api/analytics/comparison
```

---

### 2. Endpoint Management

#### `GET /api/endpoints`
List all monitored endpoints with optional filtering.
- **Query Parameters**:
  - `status`: Filter by `healthy`, `degraded`, `down`, `paused`
  - `method`: Filter by `GET`, `POST`, etc.
  - `search`: Case-insensitive search on name, URL, or tags
  - `tag`: Filter by specific tag

```bash
curl -s "http://localhost:5000/api/endpoints?status=healthy"
```

#### `POST /api/endpoints`
Add a new API endpoint to monitor.
```bash
curl -X POST http://localhost:5000/api/endpoints \
  -H "Content-Type: application/json" \
  -d '{
    "name": "GitHub API",
    "url": "https://api.github.com",
    "method": "GET",
    "expected_status": 200,
    "timeout": 10,
    "check_interval": 30,
    "tags": "git,prod",
    "headers": {
      "Accept": "application/vnd.github.v3+json"
    }
  }'
```

#### `GET /api/endpoints/<id>`
Retrieve details of a single endpoint.
```bash
curl -s http://localhost:5000/api/endpoints/1
```

#### `PUT /api/endpoints/<id>`
Update endpoint configuration. Safely preserves masked secret headers (`••••`).
```bash
curl -X PUT http://localhost:5000/api/endpoints/1 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "GitHub API Updated",
    "url": "https://api.github.com",
    "method": "GET",
    "timeout": 15
  }'
```

#### `DELETE /api/endpoints/<id>`
Delete an endpoint and cascade-delete its check history and incidents.
```bash
curl -X DELETE http://localhost:5000/api/endpoints/1
```

#### `POST /api/endpoints/<id>/check`
Trigger an immediate, on-demand real HTTP health check.
```bash
curl -X POST http://localhost:5000/api/endpoints/1/check
```

#### `POST /api/endpoints/<id>/toggle`
Toggle endpoint between active and paused states. Pausing an endpoint automatically resolves active downtime incidents.
```bash
curl -X POST http://localhost:5000/api/endpoints/1/toggle
```

---

### 3. Incidents & Reports

#### `GET /api/incidents?active=true`
Retrieve incident outage history.
```bash
curl -s "http://localhost:5000/api/incidents?active=true"
```

#### `GET /api/export/endpoints/csv`
Download a CSV report summarizing all monitored endpoints and health metrics.
```bash
curl -o endpoints.csv http://localhost:5000/api/export/endpoints/csv
```

#### `GET /api/export/checks/csv?endpoint_id=<id>`
Download granular historical check logs as CSV.
```bash
curl -o checks.csv "http://localhost:5000/api/export/checks/csv?endpoint_id=1"
```

---

## 🔒 Security & SSRF Defense Architecture

API Sentinel implements strict defense-in-depth protections:

1. **Protocol Restriction**: Only `http` and `https` schemes are accepted. Rejects dangerous protocols (`file://`, `ftp://`, `gopher://`).
2. **SSRF Pre-Flight DNS Inspection**:
   - Resolves domain to IP address prior to dispatching network requests.
   - Blocks private, loopback, and carrier IP ranges:
     - `127.0.0.0/8`, `::1` (Loopback)
     - `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` (RFC 1918 Private networks)
     - `169.254.169.254` (Cloud Instance Metadata services on AWS, GCP, Azure, DigitalOcean)
     - `fe80::/10` (IPv6 Link-Local)
3. **Sensitive Header Masking & Preservation**:
   - Tokens containing `Bearer`, `Token`, `api_key`, `secret` are masked in frontend cards and API responses (`eyJh...••••...c0de`).
   - The backend service safely merges masked updates without overwriting stored secrets.
4. **Memory Guard**: Response streaming limits body consumption to 512 KB to prevent memory exhaustion attacks.

---

## 🧪 Testing & Quality Assurance

API Sentinel maintains an automated test suite covering models, security filters, routes, and analytics math.

### Run Full Test Suite
```bash
python -m pytest -v
```

Output:
```text
============================= test session starts =============================
platform win32 -- Python 3.15.2, pytest-9.2.0
rootdir: E:\API Sentinel
collected 27 items

tests/test_analytics.py::test_analytics_calculations PASSED              [  3%]
tests/test_api_routes.py::test_get_endpoints_empty PASSED                [  7%]
tests/test_api_routes.py::test_create_endpoint_success PASSED            [ 11%]
tests/test_api_routes.py::test_create_endpoint_ssrf_blocked PASSED       [ 14%]
tests/test_api_routes.py::test_update_endpoint PASSED                    [ 18%]
tests/test_api_routes.py::test_delete_endpoint PASSED                    [ 22%]
tests/test_api_routes.py::test_toggle_endpoint_active PASSED             [ 25%]
tests/test_api_routes.py::test_check_endpoint_now_route PASSED           [ 29%]
tests/test_api_routes.py::test_dashboard_stats_route PASSED              [ 33%]
tests/test_api_routes.py::test_export_csv_routes PASSED                  [ 37%]
tests/test_api_routes.py::test_secret_preservation_on_update PASSED      [ 40%]
tests/test_api_routes.py::test_paused_state_preserved_on_edit PASSED     [ 44%]
tests/test_api_routes.py::test_toggle_pause_resolves_active_incidents PASSED [ 48%]
tests/test_models.py::test_endpoint_creation_and_defaults PASSED         [ 51%]
tests/test_models.py::test_endpoint_headers_parsing_and_masking PASSED   [ 55%]
tests/test_models.py::test_cascade_delete_check_results_and_incidents PASSED [ 59%]
tests/test_models.py::test_incident_resolution_duration PASSED           [ 62%]
tests/test_monitor.py::test_execute_health_check_success PASSED          [ 66%]
tests/test_monitor.py::test_execute_health_check_status_code_mismatch_creates_incident PASSED [ 70%]
tests/test_monitor.py::test_execute_health_check_timeout PASSED          [ 74%]
tests/test_monitor.py::test_execute_health_check_connection_error PASSED [ 77%]
tests/test_security.py::test_ip_restriction_filter PASSED                [ 81%]
tests/test_security.py::test_url_ssrf_rejections PASSED                  [ 85%]
tests/test_security.py::test_url_allow_local_override PASSED             [ 88%]
tests/test_security.py::test_valid_public_url PASSED                     [ 92%]
tests/test_security.py::test_endpoint_payload_validation_success PASSED  [ 96%]
tests/test_security.py::test_endpoint_payload_invalid_inputs PASSED      [100%]

============================= 27 passed in 1.51s ==============================
```

### Live Remote Integration Test
To execute a live end-to-end integration test against the JSONPlaceholder public API:
```bash
python scripts/verify_live_monitoring.py
```

---

## 🚢 Production Deployment

### 1. Deploy on Render (Recommended)
This repository includes a native [`render.yaml`](render.yaml) blueprint and [`Procfile`](Procfile).

1. Push your repository to GitHub.
2. In the [Render Dashboard](https://dashboard.render.com), click **New +** → **Blueprint**.
3. Select your repository. Render automatically provisions:
   - Python environment
   - Dependency installation (`pip install -r requirements.txt`)
   - Production WSGI start command (`gunicorn run:app --config gunicorn.conf.py`)
   - Persistent disk for `instance/` SQLite database

### 2. Standalone Linux / VM Deployment with Gunicorn
```bash
pip install -r requirements.txt
export FLASK_ENV=production
gunicorn run:app --config gunicorn.conf.py
```

### 3. Docker Deployment (Optional)
```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p instance

EXPOSE 5000

ENV FLASK_ENV=production
CMD ["gunicorn", "run:app", "--config", "gunicorn.conf.py"]
```

---

## 📄 License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for full details.
