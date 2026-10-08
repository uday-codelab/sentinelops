

### 🚀 SentinelOps — Quickstart & Demo Guide

#### 1. Prerequisites
Make sure you have installed:
* **Docker Desktop** (Make sure Docker Desktop is **opened and running**).
* **Git**.

---

#### 2. Clone and Start the Platform (One Command)
Open a terminal (PowerShell / Command Prompt / Git Bash) and run:

```bash
# 1. Clone the repository
git clone https://github.com/uday-codelab/sentinelops.git

# 2. Enter the project folder
cd sentinelops

# 3. Build and launch all 7 containers in the background
docker compose up --build -d
```

*(Docker will automatically pull Prometheus, TimescaleDB, Grafana, and build all 3 microservices + backend engine. This takes ~1–2 minutes on first launch).*

---

#### 3. Open the Working Interfaces in Your Browser

| Interface | URL | Description & Credentials |
| :--- | :--- | :--- |
| **SentinelOps Control Center** | [http://localhost:8000](http://localhost:8000) | **Main Project Dashboard**: Real-time telemetry, service health, and interactive Chaos Injection testbed. |
| **Grafana Monitoring** | [http://localhost:3000](http://localhost:3000) | **Deep Observability**: Pre-built live charts (User: `admin` \| Pass: `admin`). |
| **Prometheus Engine** | [http://localhost:9090](http://localhost:9090) | **Raw Metrics & PromQL**: Scrape targets and RED metrics. |
| **FastAPI Interactive Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) | **REST API Documentation**: Live API endpoints and Swagger UI. |

---

#### 4. How to Test the Live Anomaly Detection (Demo Flow)

1. Open **`http://localhost:8000`** in your browser.
2. Watch the live background synthetic traffic keep all 3 microservices (`User`, `Order`, `Payment`) in **Healthy** status.
3. Click the **"Latency Spike"** or **"Cascade Failure"** button under *Chaos Fault Injection*.
4. **Instant Detection:** Notice how the **Isolation Forest ML model** immediately triggers a high-severity alert box at the top showing the anomaly score and root cause.
5. Open **`http://localhost:3000`** in Grafana to see the live time-series latency and error spike graphs.

---

#### 5. When Done Testing (To Stop Containers)
To cleanly stop all background services:
```bash
docker compose down
```
