# Microservices Health Monitor — Project Wiki
> Living document. Update this after every working session. Never let it go stale.

---

## Table of Contents
1. [What We Are Building](#1-what-we-are-building)
2. [System Architecture](#2-system-architecture)
3. [Environment Setup](#3-environment-setup)
4. [Phase Breakdown](#4-phase-breakdown)
5. [Prerequisites — What to Learn Before Each Phase](#5-prerequisites)
6. [Project Status Tracker](#6-project-status-tracker)
7. [Decision Log](#7-decision-log)
8. [How to Run the Project](#8-how-to-run-the-project)
9. [Team Responsibilities](#9-team-responsibilities)
10. [Interview Prep — Questions This Project Generates](#10-interview-prep)

---

## 1. What We Are Building

### Problem
Distributed applications run as multiple small services. When one fails, it can cascade.
Engineers find out **after** users complain. We want to find out **before**.

### Solution — 3 Layers
| Layer | Question Answered | Technology |
|---|---|---|
| Observation | What is each service doing right now? | Prometheus + TimescaleDB |
| Detection | Is anything behaving abnormally? | Isolation Forest |
| Prediction | Which service will fail in the next 5–10 minutes? | LSTM Autoencoder |

### What Makes This Not a Toy Project
- Uses **real production data**: Alibaba Cluster Trace (actual labeled failures from Alibaba's infrastructure)
- Compares ML against a **rule-based baseline** (CPU > 80% threshold) — we justify why ML wins
- All experiments tracked in **MLflow** with F1 scores, precision, recall
- Entire system starts with **one command**: `docker-compose up`
- Deployed to a live URL

### Data Source
**Alibaba Cluster Trace 2018**
- URL: https://github.com/alibaba/clusterdata
- Contains: real container CPU/memory metrics from Alibaba's production cluster
- Why: has actual labeled failure events — gives us ground truth for model evaluation
- Supplement with: Numenta Anomaly Benchmark (NAB) for additional labeled anomaly data

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   SIMULATED SERVICES                     │
│                                                          │
│  [User Service :8001]  [Order Service :8002]             │
│  [Payment Service :8003]                                 │
│         │  each exposes /metrics endpoint                │
└─────────┼────────────────────────────────────────────────┘
          │ scrapes every 15s
          ▼
    [Prometheus :9090]
    time-series metrics collector
          │ our collector reads from Prometheus HTTP API
          ▼
    [TimescaleDB :5432]
    PostgreSQL + time partitioning
    stores metrics for ML feature engineering
          │
          ▼
    [FastAPI Backend :8000]
    ├── Metrics Collector (APScheduler — runs every 30s)
    ├── Isolation Forest (real-time anomaly detection)
    ├── LSTM Autoencoder (predictive failure detection)
    ├── Alert Manager (email / Slack webhook)
    └── REST API (serves dashboard data)
          │
    ┌─────┴──────┐
    ▼            ▼
[Grafana :3000]  [MLflow :5000]
Live dashboards  Experiment tracking
```

### Key Data Flow
```
Service metrics → Prometheus → Our collector (every 30s) → TimescaleDB
                                                                │
                                                    Feature extraction
                                                                │
                                              Isolation Forest score
                                              LSTM reconstruction error
                                                                │
                                              If anomaly score > threshold
                                                                │
                                                        Alert fired
```

---

## 3. Environment Setup

> Complete this before touching any project code. Every team member does this on their machine.

### 3.1 Required Software

| Tool | Version | Purpose | Install |
|---|---|---|---|
| Python | 3.11+ | All backend code | python.org |
| Docker Desktop | Latest | Runs Prometheus, Grafana, TimescaleDB | docker.com |
| Git | Any | Version control | git-scm.com |
| VS Code | Any | Editor | code.visualstudio.com |
| Postman | Any | Testing REST APIs | postman.com |

### 3.2 VS Code Extensions to Install
- Python (Microsoft)
- Docker
- GitLens
- REST Client (alternative to Postman, works inside VS Code)
- GitHub Copilot (if available)

### 3.3 Python Environment Setup
```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/microservices-health-monitor
cd microservices-health-monitor

# 2. Create virtual environment (do this ONCE per machine)
python -m venv venv

# 3. Activate it (do this EVERY TIME you open a new terminal)
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Verify it works
python --version   # should show 3.11+
```

### 3.4 What Is a Virtual Environment and Why
A virtual environment is an isolated Python installation for this project only.
Without it, installing libraries for this project can break your other Python projects.
Rule: **always activate venv before running any project code.**
You know it's active when your terminal shows `(venv)` at the start.

### 3.5 Docker — What It Is and Why We Use It
Docker packages software into containers — self-contained units that include
the software and everything it needs to run. Think of it as a mini virtual machine
but much lighter.

We use Docker for:
- **Prometheus** — too complex to install manually; Docker makes it one line
- **TimescaleDB** — same
- **Grafana** — same
- **MLflow** — same

You don't write Docker code for these. You just use the official images.

```bash
# Verify Docker is installed and running
docker --version
docker-compose --version

# Test Docker works
docker run hello-world
# Should print "Hello from Docker!"
```

### 3.6 Environment Variables
Create a `.env` file in the project root (never commit this to GitHub):
```
DATABASE_URL=postgresql://admin:password@localhost:5432/metrics_db
PROMETHEUS_URL=http://localhost:9090
ALERT_EMAIL=your_team_email@gmail.com
SMTP_PASSWORD=your_app_password
SLACK_WEBHOOK_URL=https://hooks.slack.com/...  (optional)
SECRET_KEY=any_random_string_here
```

Add `.env` to `.gitignore` immediately.

### 3.7 Repository Structure
```
microservices-health-monitor/
├── services/                    # The 3 microservices being monitored
│   ├── user_service/
│   │   ├── main.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── order_service/
│   └── payment_service/
├── backend/                     # FastAPI backend + ML
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── scheduler.py
│   ├── models/
│   │   ├── isolation_forest.py
│   │   └── lstm_autoencoder.py
│   ├── detection/
│   │   ├── anomaly_detector.py
│   │   └── alert_manager.py
│   └── api/
│       ├── metrics.py
│       └── anomalies.py
├── data/                        # Training data, raw datasets
│   ├── alibaba_trace/
│   └── processed/
├── notebooks/                   # Jupyter notebooks for exploration
│   ├── 01_data_exploration.ipynb
│   ├── 02_isolation_forest.ipynb
│   └── 03_lstm_training.ipynb
├── prometheus.yml               # Prometheus scrape config
├── docker-compose.yml           # Entire stack in one file
├── schema.sql                   # TimescaleDB schema
├── requirements.txt             # Python dependencies
├── .env                         # Secrets (never commit)
├── .gitignore
├── README.md                    # Public-facing project description
└── PROJECT_WIKI.md              # This file
```

---

## 4. Phase Breakdown

### Phase 1 — Infrastructure (Weeks 1–2) → Review 1 Target
**Goal:** Data is flowing. Grafana shows live charts. Faculty can see a working system.

**Deliverables:**
- [ ] 3 microservices running with `/metrics` endpoints
- [ ] Prometheus scraping all 3 services
- [ ] TimescaleDB running with schema applied
- [ ] Collector job writing metrics to TimescaleDB every 30s
- [ ] Grafana showing at least 4 panels (CPU, latency, error rate, request rate)
- [ ] Fault injection working (`POST /fault/high_latency` changes service behavior)
- [ ] `docker-compose up` starts everything

**What to demo at Review 1:**
1. Open terminal → `docker-compose up`
2. Open Grafana → show live metrics
3. Inject a fault → show metrics spike in real time
4. Show TimescaleDB has the data (`SELECT * FROM service_metrics LIMIT 10`)

---

### Phase 2 — Isolation Forest (Weeks 3–5)
**Goal:** First ML model working, evaluated with real numbers.

**Deliverables:**
- [ ] Alibaba Cluster Trace downloaded and preprocessed
- [ ] Feature engineering pipeline (5 features per service per timestamp)
- [ ] Isolation Forest trained on normal data
- [ ] Evaluated on labeled failures: F1, precision, recall computed
- [ ] Anomaly scores stored in `anomaly_events` table
- [ ] Rule-based baseline built for comparison
- [ ] MLflow logging all experiments
- [ ] FastAPI endpoint: `GET /api/anomalies` returns recent anomalies

---

### Phase 3 — LSTM Autoencoder (Weeks 6–8)
**Goal:** Predictive model working. Can flag failure before it happens.

**Deliverables:**
- [ ] LSTM Autoencoder implemented in PyTorch
- [ ] Trained on 200+ hours of normal metric windows (30-min sequences)
- [ ] Reconstruction error threshold determined from validation set
- [ ] Evaluated: does it flag failure before Isolation Forest? By how many minutes?
- [ ] Compared against Isolation Forest in MLflow
- [ ] FastAPI endpoint: `GET /api/predictions` returns risk scores

---

### Phase 4 — Polish + Deploy (Weeks 9–11) → Review 2 Target
**Goal:** Live demo. Deployed URL. Professional README.

**Deliverables:**
- [ ] Alert system working (email or Slack webhook)
- [ ] Grafana dashboard finalized (anomaly overlay panel added)
- [ ] Deployed to DigitalOcean / Render
- [ ] README with architecture diagram, demo GIF, setup instructions
- [ ] 3-minute demo video recorded
- [ ] All experiments documented in MLflow

---

## 5. Prerequisites

> What each team member should learn BEFORE starting each phase.
> Use these as a checklist. Don't skip. You will get stuck otherwise.

### Before Phase 1 (Infrastructure)

**Everyone must know:**
- [ ] What is a REST API? What are GET, POST, PUT, DELETE?
- [ ] What is JSON? How do you read/write it in Python?
- [ ] What is Git? How do you commit, push, pull, branch, merge?
- [ ] What is a virtual environment? How do you activate one?

**Person setting up Prometheus must know:**
- [ ] What is a YAML file? (Prometheus config is YAML)
- [ ] What does "scraping" mean in the context of metrics?
- [ ] What is a Docker container vs a Docker image?
- [ ] How to read `docker-compose.yml` — what do `services`, `ports`, `volumes` mean?

**Person building microservices must know:**
- [ ] FastAPI basics: how to define a route, return JSON, use path parameters
- [ ] How to use `prometheus-client` Python library (Counter, Histogram, Gauge)
- [ ] What are HTTP status codes (200, 404, 500)?

**Resources (do these, not random YouTube videos):**
- FastAPI: https://fastapi.tiangolo.com/tutorial/ (first 5 sections only)
- Docker: https://docs.docker.com/get-started/ (Parts 1–3)
- Prometheus Python client: https://github.com/prometheus/client_python (README examples)

---

### Before Phase 2 (Isolation Forest)

**Everyone must know:**
- [ ] What is a pandas DataFrame? How do you load a CSV into one?
- [ ] What is train/test split? Why do we split data?
- [ ] What is a confusion matrix? What are precision and recall?
- [ ] What is F1 score and when do you use it instead of accuracy?

**Person doing ML must also know:**
- [ ] What is supervised vs unsupervised learning? (Isolation Forest is unsupervised)
- [ ] Conceptually: what is Isolation Forest? (random splits, isolation depth)
- [ ] What does `sklearn` mean and how to use it (fit, predict, decision_function)
- [ ] What is feature scaling and why it matters?

**Resources:**
- pandas: https://pandas.pydata.org/docs/getting_started/intro_tutorials/
- scikit-learn Isolation Forest: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html
- F1/precision/recall: StatQuest on YouTube — "Machine Learning Fundamentals: Sensitivity and Specificity" (12 min)

---

### Before Phase 3 (LSTM Autoencoder)

**Everyone must know:**
- [ ] What is a neural network at a conceptual level? (layers, weights, training)
- [ ] What is a loss function? What does "minimizing loss" mean?
- [ ] What is backpropagation at a concept level? (not math, just: "gradients flow backward")

**Person doing LSTM must also know:**
- [ ] What is a sequence? Why does order matter in time-series?
- [ ] What problem do vanilla RNNs have that LSTMs solve? (vanishing gradient)
- [ ] What is an autoencoder? (encoder compresses, decoder reconstructs)
- [ ] PyTorch basics: Tensor, nn.Module, forward(), optimizer.step()

**Resources:**
- PyTorch basics: https://pytorch.org/tutorials/beginner/basics/intro.html (first 4 sections)
- LSTM intuition: https://colah.github.io/posts/2015-08-Understanding-LSTMs/ (read this fully, it's the best LSTM explanation that exists)
- Autoencoder concept: "Autoencoder" on StatQuest YouTube (15 min)

---

### Before Phase 4 (Deploy)

**Everyone must know:**
- [ ] What is SSH? How do you connect to a remote server?
- [ ] What is a domain name vs an IP address?
- [ ] What does "exposing a port" mean in Docker?

**Person doing deployment must also know:**
- [ ] How to set up a DigitalOcean Droplet (Ubuntu)
- [ ] How to install Docker on a Linux server
- [ ] What is `nginx` and why we need it as a reverse proxy (optional but good)
- [ ] How to set environment variables on a server

---

## 6. Project Status Tracker

> Update this every Friday. One sentence per item. Be honest.

### Week 1
| Task | Owner | Status | Notes |
|---|---|---|---|
| Repo created, .gitignore set up | | ⬜ Not started | |
| user_service built with /metrics | | ⬜ Not started | |
| order_service built with /metrics | | ⬜ Not started | |
| payment_service built with /metrics | | ⬜ Not started | |
| Prometheus scraping all 3 | | ⬜ Not started | |
| TimescaleDB running in Docker | | ⬜ Not started | |
| Schema.sql applied | | ⬜ Not started | |

### Week 2
| Task | Owner | Status | Notes |
|---|---|---|---|
| Collector job (APScheduler) | | ⬜ Not started | |
| Grafana connected to Prometheus | | ⬜ Not started | |
| Grafana dashboard: 4 panels | | ⬜ Not started | |
| Fault injection endpoint working | | ⬜ Not started | |
| docker-compose.yml wrapping all | | ⬜ Not started | |
| Review 1 demo rehearsed | | ⬜ Not started | |

### Week 3–5
| Task | Owner | Status | Notes |
|---|---|---|---|
| Alibaba trace downloaded | | ⬜ Not started | |
| Data preprocessing notebook | | ⬜ Not started | |
| Isolation Forest trained | | ⬜ Not started | |
| Baseline rule-based system | | ⬜ Not started | |
| Evaluation: F1/precision/recall | | ⬜ Not started | |
| MLflow logging set up | | ⬜ Not started | |
| Anomaly API endpoint | | ⬜ Not started | |

### Week 6–8
| Task | Owner | Status | Notes |
|---|---|---|---|
| LSTM Autoencoder implemented | | ⬜ Not started | |
| Training pipeline complete | | ⬜ Not started | |
| Threshold calibration | | ⬜ Not started | |
| Comparison: IF vs LSTM in MLflow | | ⬜ Not started | |
| Prediction API endpoint | | ⬜ Not started | |

### Week 9–11
| Task | Owner | Status | Notes |
|---|---|---|---|
| Alert system (email/Slack) | | ⬜ Not started | |
| Grafana anomaly overlay panel | | ⬜ Not started | |
| Deployed to live URL | | ⬜ Not started | |
| README finalized | | ⬜ Not started | |
| Demo video recorded | | ⬜ Not started | |

**Status key:** ⬜ Not started · 🔄 In progress · ✅ Done · ❌ Blocked (add reason in Notes)

---

## 7. Decision Log

> Every time you make a non-obvious technical decision, log it here.
> Future you will thank present you. Interviewers will ask about these.

| Date | Decision | Why | Alternatives Rejected |
|---|---|---|---|
| [date] | TimescaleDB over plain PostgreSQL | Time-partitioned queries 10–100x faster for metric data | Plain PostgreSQL (slower), InfluxDB (different query language, steeper learning curve) |
| [date] | Alibaba Cluster Trace over synthetic data | Real labeled failure events — gives credible ground truth for evaluation | Synthetic only (weak claim), Google Cluster Trace (less suitable for ML) |
| [date] | Isolation Forest over k-means for anomaly detection | Handles high-dimensional data better; no need to specify number of clusters; works on unlabeled data | K-means (needs cluster count), DBSCAN (sensitive to epsilon parameter), Z-score (univariate only) |
| [date] | LSTM Autoencoder over simple LSTM classifier | No labeled failure sequences for supervised training; autoencoder learns from normal data only | Supervised LSTM (needs labeled failures), Prophet (univariate only) |
| [date] | MLflow for experiment tracking | Industry standard; free; integrates with scikit-learn and PyTorch natively | Weights & Biases (paid above limits), manual logging (not reproducible) |

---

## 8. How to Run the Project

### First time setup
```bash
git clone https://github.com/YOUR_USERNAME/microservices-health-monitor
cd microservices-health-monitor
cp .env.example .env          # then fill in your values
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Start everything
```bash
docker-compose up
```

### Access points once running
| Service | URL | What you see |
|---|---|---|
| User Service | http://localhost:8001 | Service API |
| User Metrics | http://localhost:8001/metrics | Raw Prometheus metrics |
| Prometheus | http://localhost:9090 | Metrics query interface |
| Grafana | http://localhost:3000 | Live dashboards (admin/admin) |
| TimescaleDB | localhost:5432 | Connect via psql or DBeaver |
| FastAPI Backend | http://localhost:8000 | Our API |
| FastAPI Docs | http://localhost:8000/docs | Auto-generated API docs |
| MLflow | http://localhost:5000 | Experiment tracking |

### Inject a fault (for testing/demo)
```bash
# Make payment service simulate high latency
curl -X POST http://localhost:8003/fault/high_latency

# Make order service simulate cascade failure
curl -X POST http://localhost:8002/fault/cascade_failure

# Return to normal
curl -X POST http://localhost:8001/fault/normal
```

### Run ML training
```bash
# Train Isolation Forest
python backend/models/isolation_forest.py --train

# Train LSTM Autoencoder
python backend/models/lstm_autoencoder.py --train --epochs 100

# View results in MLflow
# Open http://localhost:5000
```

### Stop everything
```bash
docker-compose down           # stops containers
docker-compose down -v        # stops + deletes data volumes (fresh start)
```

---

## 9. Team Responsibilities

| Member | Primary Role | Phase 1 | Phase 2 | Phase 3 | Phase 4 |
|---|---|---|---|---|---|
| Uday | Backend + ML Lead | Collector job, FastAPI core | Isolation Forest, MLflow | LSTM Autoencoder | Deployment |
| Member 1 | SE | Microservices + fault injection | Rule-based baseline | Evaluation pipeline | CI/CD |
| Member 2 | SE | Docker Compose, Prometheus config | Grafana dashboards | Alert system | README + docs |
| Member 3 | DS | TimescaleDB schema | Data preprocessing, F1 eval | Threshold analysis | Demo prep |

### Git Workflow
- `main` branch = always working, always demo-able
- Feature branches: `feature/isolation-forest`, `feature/lstm-model`
- Never push directly to `main`
- Open a Pull Request, one other member reviews, then merge
- Commit messages: `feat: add prometheus scrape config` / `fix: collector job error handling`

---

## 10. Interview Prep

### Questions This Project Generates (with one-line answer hints)

**Architecture:**
- What is the RED method? → Rate, Errors, Duration — the 3 metrics every service exposes
- Why TimescaleDB over PostgreSQL? → Same SQL, but auto time-partitioned — range queries 10–100x faster
- Why Prometheus instead of writing directly to DB? → PromQL makes time-series aggregation trivial; scraping is pull-based so services stay decoupled

**ML:**
- Why Isolation Forest for anomaly detection? → Handles multivariate anomalies; no labels needed; works where fixed thresholds fail
- Why LSTM Autoencoder and not a classifier? → No labeled failure sequences available; autoencoder learns normal patterns, anomaly = high reconstruction error
- How did you set your detection threshold? → 95th percentile of reconstruction error on normal validation data
- How did you evaluate without real production data? → Alibaba Cluster Trace has real labeled failures; we also inject synthetic faults and measure detection latency
- Why did ML beat your rule-based baseline? → Rules miss multivariate patterns (low CPU + high latency + rising errors together); IF catches the combination

**Engineering:**
- How does docker-compose work? → Defines all services in one YAML; `docker-compose up` starts the entire stack
- What is MLflow and why does it matter? → Tracks every training run's parameters and metrics — reproducibility and comparison
- How would you scale this to 100 services? → Prometheus federation, Kafka for metric streaming, model per service cluster

### Numbers to Know (fill in after you have real results)
- Isolation Forest F1 score: ___
- LSTM Autoencoder F1 score: ___
- Average minutes of warning before failure: ___
- Number of training hours of data: ___
- Number of services monitored: 3
- Metrics collected per service: 5 (CPU, memory, request rate, error rate, latency p95)
- Collection frequency: every 30 seconds
- Training dataset: Alibaba Cluster Trace 2018

---

*Last updated: [date] by [name]*
*Next update due: [date]*
