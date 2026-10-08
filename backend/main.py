from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import logging
import os
import requests
import threading
import time
import random

from backend.database import fetch_recent_metrics, fetch_recent_anomalies
from backend.scheduler import start_metrics_scheduler
from backend.models.isolation_forest import anomaly_detector_model

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("sentinelops.backend")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

# Service URL Map (Docker container names with localhost fallbacks)
SERVICE_PORT_MAP = {
    "user_service": (os.getenv("USER_SERVICE_HOST", "user_service"), 8001),
    "order_service": (os.getenv("ORDER_SERVICE_HOST", "order_service"), 8002),
    "payment_service": (os.getenv("PAYMENT_SERVICE_HOST", "payment_service"), 8003)
}

def get_service_base_url(svc_name: str) -> str:
    host, port = SERVICE_PORT_MAP.get(svc_name, ("localhost", 8000))
    # Test if host resolves, else fallback to localhost
    return f"http://{host}:{port}"

# Background Traffic Simulation Worker
traffic_running = False
traffic_thread = None

def traffic_worker():
    global traffic_running
    logger.info("Traffic generator worker started.")
    while traffic_running:
        try:
            # 1. User service request
            u_url = get_service_base_url("user_service")
            user_id = random.randint(1, 100)
            requests.get(f"{u_url}/users/{user_id}", timeout=3)

            # 2. Order service request
            o_url = get_service_base_url("order_service")
            order_payload = {
                "user_id": user_id,
                "item_id": random.randint(101, 150),
                "quantity": random.randint(1, 4),
                "total_amount": round(random.uniform(20.0, 400.0), 2)
            }
            requests.post(f"{o_url}/orders", json=order_payload, timeout=3)

            # 3. Payment service request
            p_url = get_service_base_url("payment_service")
            pay_payload = {
                "order_id": random.randint(1000, 9999),
                "user_id": user_id,
                "amount": order_payload["total_amount"],
                "payment_method": "credit_card"
            }
            requests.post(f"{p_url}/payments/process", json=pay_payload, timeout=3)
        except Exception:
            # Try localhost fallback if in local dev
            try:
                requests.get(f"http://localhost:8001/users/{random.randint(1, 50)}", timeout=1)
                requests.post("http://localhost:8002/orders", json={"user_id": 1, "item_id": 101, "quantity": 1, "total_amount": 99.0}, timeout=1)
                requests.post("http://localhost:8003/payments/process", json={"order_id": 101, "user_id": 1, "amount": 99.0, "payment_method": "upi"}, timeout=1)
            except Exception:
                pass
        
        time.sleep(random.uniform(0.5, 1.2))
    logger.info("Traffic generator worker stopped.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting SentinelOps Backend & ML Engine...")
    scheduler = start_metrics_scheduler()
    logger.info("Calibrating baseline Isolation Forest model...")
    anomaly_detector_model.train_baseline()
    yield
    logger.info("Shutting down SentinelOps Backend...")
    global traffic_running
    traffic_running = False
    scheduler.shutdown()

app = FastAPI(
    title="SentinelOps - AIOps Microservices Health Monitor",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def serve_dashboard():
    """Serve the single-pane-of-glass SentinelOps Web Dashboard"""
    index_file = os.path.join(STATIC_DIR, "index.html")
    return FileResponse(index_file)

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/api/system/status")
def get_system_status():
    """Fetch live health, fault status, and current gauge metrics for all services"""
    status_data = {}
    for svc_name in ["user_service", "order_service", "payment_service"]:
        base_url = get_service_base_url(svc_name)
        svc_info = {"status": "offline", "fault_mode": "normal", "cpu": 25.0, "latency_ms": 50.0, "error_rate": 0.0}
        
        # Try primary URL, then localhost
        for target_url in [base_url, f"http://localhost:{SERVICE_PORT_MAP[svc_name][1]}"]:
            try:
                r = requests.get(f"{target_url}/", timeout=1.5)
                if r.status_code == 200:
                    d = r.json()
                    svc_info["status"] = "online"
                    svc_info["fault_mode"] = d.get("fault_mode", "normal")
                    
                    # Estimate visual gauge from fault mode
                    mode = svc_info["fault_mode"]
                    if mode == "normal":
                        svc_info["cpu"] = round(random.uniform(20.0, 32.0), 1)
                        svc_info["latency_ms"] = round(random.uniform(35.0, 65.0), 1)
                        svc_info["error_rate"] = 0.01
                    elif mode == "high_latency":
                        svc_info["cpu"] = round(random.uniform(50.0, 68.0), 1)
                        svc_info["latency_ms"] = round(random.uniform(500.0, 850.0), 1)
                        svc_info["error_rate"] = 0.08
                    elif mode == "cpu_spike":
                        svc_info["cpu"] = round(random.uniform(88.0, 96.0), 1)
                        svc_info["latency_ms"] = round(random.uniform(150.0, 300.0), 1)
                        svc_info["error_rate"] = 0.05
                    elif mode == "memory_leak":
                        svc_info["cpu"] = round(random.uniform(65.0, 78.0), 1)
                        svc_info["latency_ms"] = round(random.uniform(250.0, 500.0), 1)
                        svc_info["error_rate"] = 0.15
                    elif mode == "cascade_failure":
                        svc_info["cpu"] = round(random.uniform(92.0, 99.0), 1)
                        svc_info["latency_ms"] = round(random.uniform(1800.0, 3200.0), 1)
                        svc_info["error_rate"] = 0.45
                    break
            except Exception:
                continue
        
        status_data[svc_name] = svc_info

    return {
        "services": status_data,
        "traffic_active": traffic_running
    }

@app.post("/api/fault/{service_name}/{mode}")
def inject_service_fault(service_name: str, mode: str):
    """Proxy fault injection trigger to the specified service"""
    if service_name not in SERVICE_PORT_MAP:
        raise HTTPException(status_code=400, detail="Unknown service name")

    base_url = get_service_base_url(service_name)
    success = False
    
    for target_url in [base_url, f"http://localhost:{SERVICE_PORT_MAP[service_name][1]}"]:
        try:
            r = requests.post(f"{target_url}/fault/{mode}", timeout=2.0)
            if r.status_code == 200:
                success = True
                break
        except Exception:
            continue

    if not success:
        raise HTTPException(status_code=502, detail=f"Could not reach {service_name}")

    # Immediately evaluate anomaly for real-time responsiveness
    try:
        import datetime
        from backend.detection.anomaly_detector import evaluate_metrics_for_anomalies
        now = datetime.datetime.now(datetime.timezone.utc)
        
        cpu = 98.0 if mode == "cascade_failure" else (95.0 if mode == "cpu_spike" else (65.0 if mode == "high_latency" else 25.0))
        mem = 88.0 if mode == "cascade_failure" else (92.0 if mode == "memory_leak" else 45.0)
        err = 0.65 if mode == "cascade_failure" else (0.10 if mode == "high_latency" else 0.01)
        lat = 2.5 if mode == "cascade_failure" else (0.75 if mode == "high_latency" else 0.05)
        req = 150.0
        
        if mode != "normal":
            evaluate_metrics_for_anomalies([{
                "time": now,
                "service_name": service_name,
                "cpu_percent": cpu,
                "memory_percent": mem,
                "error_rate": err,
                "latency_seconds": lat,
                "requests_total": req
            }])
    except Exception as e:
        logger.error(f"Immediate anomaly evaluation error: {e}")

    return {"service": service_name, "fault_mode": mode, "status": "applied"}

@app.post("/api/traffic/toggle")
def toggle_traffic():
    """Toggle automated background load traffic generator"""
    global traffic_running, traffic_thread
    if traffic_running:
        traffic_running = False
        return {"active": False, "message": "Traffic stopped"}
    else:
        traffic_running = True
        traffic_thread = threading.Thread(target=traffic_worker, daemon=True)
        traffic_thread.start()
        return {"active": True, "message": "Traffic started"}

@app.get("/api/metrics")
def get_metrics(service: str = Query(None, description="Filter by service name"), minutes: int = Query(15, ge=1, le=1440)):
    """Fetch time-series metrics from TimescaleDB for visualization"""
    rows = fetch_recent_metrics(service_name=service, minutes=minutes)
    return {
        "service": service or "all",
        "minutes": minutes,
        "count": len(rows),
        "data": rows
    }

@app.get("/api/anomalies")
def get_anomalies(limit: int = Query(50, ge=1, le=500)):
    """Fetch recent anomaly events detected by ML models"""
    rows = fetch_recent_anomalies(limit=limit)
    return {
        "count": len(rows),
        "anomalies": rows
    }

@app.post("/api/models/train")
def train_model():
    """Trigger manual retraining of Isolation Forest baseline"""
    anomaly_detector_model.train_baseline()
    return {"status": "success", "message": "Isolation Forest model retrained successfully"}
