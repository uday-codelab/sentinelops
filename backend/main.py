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
from backend.models.sentinel_core import sentinel_hybrid_engine
from backend.detection.anomaly_detector import evaluate_metrics_for_anomalies

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("sentinelops.backend")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

SERVICE_PORT_MAP = {
    "user_service": (os.getenv("USER_SERVICE_HOST", "user_service"), 8001),
    "order_service": (os.getenv("ORDER_SERVICE_HOST", "order_service"), 8002),
    "payment_service": (os.getenv("PAYMENT_SERVICE_HOST", "payment_service"), 8003)
}

SERVICES_LIST = ["user_service", "order_service", "payment_service"]

def get_service_base_url(svc_name: str) -> str:
    host, port = SERVICE_PORT_MAP.get(svc_name, ("localhost", 8000))
    return f"http://{host}:{port}"

# Background Traffic Simulation Worker
traffic_running = False
traffic_thread = None

def traffic_worker():
    global traffic_running
    logger.info("Traffic generator worker started.")
    while traffic_running:
        try:
            u_url = get_service_base_url("user_service")
            user_id = random.randint(1, 100)
            requests.get(f"{u_url}/users/{user_id}", timeout=3)

            o_url = get_service_base_url("order_service")
            order_payload = {
                "user_id": user_id,
                "item_id": random.randint(101, 150),
                "quantity": random.randint(1, 4),
                "total_amount": round(random.uniform(20.0, 400.0), 2)
            }
            requests.post(f"{o_url}/orders", json=order_payload, timeout=3)

            p_url = get_service_base_url("payment_service")
            pay_payload = {
                "order_id": random.randint(1000, 9999),
                "user_id": user_id,
                "amount": order_payload["total_amount"],
                "payment_method": "credit_card"
            }
            requests.post(f"{p_url}/payments/process", json=pay_payload, timeout=3)
        except Exception:
            try:
                requests.get(f"http://localhost:8001/users/{random.randint(1, 50)}", timeout=1)
                requests.post("http://localhost:8002/orders", json={"user_id": 1, "item_id": 101, "quantity": 1, "total_amount": 99.0}, timeout=1)
                requests.post("http://localhost:8003/payments/process", json={"order_id": 101, "user_id": 1, "amount": 99.0, "payment_method": "upi"}, timeout=1)
            except Exception:
                pass
        
        time.sleep(random.uniform(0.5, 1.2))
    logger.info("Traffic generator worker stopped.")

# Background Flash Crowd Scenario Worker
flash_crowd_running = False

def flash_crowd_worker():
    global flash_crowd_running
    flash_crowd_running = True
    logger.info("Executing Benign Flash Crowd Scenario (~25 req/s for 30s)...")
    end_time = time.time() + 30.0
    while time.time() < end_time and flash_crowd_running:
        try:
            u_url = get_service_base_url("user_service")
            o_url = get_service_base_url("order_service")
            requests.get(f"{u_url}/users/{random.randint(1, 50)}", timeout=0.8)
            requests.post(f"{o_url}/orders", json={
                "user_id": random.randint(1, 50),
                "item_id": random.randint(101, 150),
                "quantity": 1,
                "total_amount": 99.0
            }, timeout=0.8)
        except Exception:
            pass
        time.sleep(0.04)
    flash_crowd_running = False
    logger.info("Benign Flash Crowd Scenario finished.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting SentinelOps Backend & ML Engine...")
    scheduler = start_metrics_scheduler()
    logger.info("Calibrating baseline Isolation Forest model...")
    anomaly_detector_model.train_baseline()
    yield
    logger.info("Shutting down SentinelOps Backend...")
    global traffic_running, flash_crowd_running
    traffic_running = False
    flash_crowd_running = False
    scheduler.shutdown()

app = FastAPI(
    title="SentinelOps - Intelligent AIOps Platform",
    version="2.0.0",
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
    latest_state = sentinel_hybrid_engine.get_latest_state()
    status_data = {}
    
    precursor_active = False
    active_precursor_info = None
    burst_suppressed_active = False
    
    for svc_name in SERVICES_LIST:
        base_url = get_service_base_url(svc_name)
        svc_info = {
            "status": "offline", 
            "fault_mode": "normal", 
            "cpu": 25.0, 
            "memory": 45.0, 
            "latency_ms": 50.0, 
            "error_rate": 0.0,
            "rps": 2.0,
            "trend_slope": 0.0,
            "load_ratio": 0.04,
            "ttb_seconds": 0.0,
            "precursor_alert": False,
            "is_burst_suppressed": False,
            "static_alert": False,
            "iso_forest_alert": False,
            "sentinel_alert": False,
            "severity": "NORMAL"
        }
        
        # Check actual microservice endpoint for fault_mode & online status
        for target_url in [base_url, f"http://localhost:{SERVICE_PORT_MAP[svc_name][1]}"]:
            try:
                r = requests.get(f"{target_url}/", timeout=1.5)
                if r.status_code == 200:
                    d = r.json()
                    svc_info["status"] = "online"
                    svc_info["fault_mode"] = d.get("fault_mode", "normal")
                    break
            except Exception:
                continue
        
        # Overlay real-time ML metrics from sentinel_hybrid_engine
        eval_res = latest_state.get(svc_name)
        if eval_res:
            details = eval_res.get("details", {})
            svc_info["cpu"] = round(float(details.get("cpu_percent", 25.0)), 1)
            svc_info["memory"] = round(float(details.get("memory_percent", 45.0)), 1)
            svc_info["latency_ms"] = round(float(details.get("latency_seconds", 0.05)) * 1000.0, 1)
            svc_info["error_rate"] = round(float(details.get("error_rate", 0.01)), 4)
            svc_info["rps"] = round(float(details.get("requests_total", 2.0)), 2)
            svc_info["trend_slope"] = round(float(eval_res.get("trend_slope", 0.0)), 4)
            svc_info["load_ratio"] = round(float(eval_res.get("load_ratio", 0.0)), 4)
            svc_info["ttb_seconds"] = round(float(eval_res.get("estimated_ttb_seconds", 0.0)), 1)
            svc_info["precursor_alert"] = bool(eval_res.get("precursor_alert", False))
            svc_info["is_burst_suppressed"] = bool(eval_res.get("is_burst_suppressed", False))
            svc_info["static_alert"] = bool(eval_res.get("static_alert", False))
            svc_info["iso_forest_alert"] = bool(eval_res.get("iso_forest_alert", False))
            svc_info["sentinel_alert"] = bool(eval_res.get("sentinel_alert", False))
            svc_info["severity"] = eval_res.get("severity", "NORMAL")
            
            if svc_info["precursor_alert"]:
                precursor_active = True
                active_precursor_info = {
                    "service": svc_name,
                    "ttb_seconds": svc_info["ttb_seconds"],
                    "trend_slope": svc_info["trend_slope"],
                    "memory_percent": svc_info["memory"]
                }
            if svc_info["is_burst_suppressed"]:
                burst_suppressed_active = True

        status_data[svc_name] = svc_info

    # 3-Way Strategy Comparison Matrix
    sentinel_matrix = {
        "static_rule": {
            s: ("CRITICAL" if status_data[s]["static_alert"] else "OK") for s in SERVICES_LIST
        },
        "isolation_forest": {
            s: ("ANOMALY" if status_data[s]["iso_forest_alert"] else "OK") for s in SERVICES_LIST
        },
        "sentinel_precursor": {
            s: (
                "PRECURSOR_ALERT" if status_data[s]["precursor_alert"]
                else ("BURST_SUPPRESSED" if status_data[s]["is_burst_suppressed"]
                else ("CRITICAL" if status_data[s]["sentinel_alert"] else "OK"))
            ) for s in SERVICES_LIST
        }
    }

    return {
        "services": status_data,
        "traffic_active": traffic_running,
        "sentinel_matrix": sentinel_matrix,
        "precursor_active": precursor_active,
        "active_precursor": active_precursor_info,
        "burst_suppressed_active": burst_suppressed_active
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
        now = datetime.datetime.now(datetime.timezone.utc)
        
        cpu = 98.0 if mode == "cascade_failure" else (95.0 if mode == "cpu_spike" else (65.0 if mode == "high_latency" else 25.0))
        mem = 88.0 if mode == "cascade_failure" else (68.0 if mode == "memory_leak" else 45.0)
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

# -----------------------------------------------------------------
# 4 Standardized Benchmark Scenario Triggers
# -----------------------------------------------------------------

@app.post("/api/scenarios/flash_crowd")
def scenario_flash_crowd():
    """Scenario 1: Benign Flash Crowd Traffic Surge (~25 req/s for 30s)"""
    import datetime
    now = datetime.datetime.now(datetime.timezone.utc)
    # Feed flash crowd vectors to engine: high CPU & high RPS, low load ratio, flat memory
    for svc in SERVICES_LIST:
        evaluate_metrics_for_anomalies([{
            "time": now,
            "service_name": svc,
            "cpu_percent": 75.0,
            "memory_percent": 45.0,
            "error_rate": 0.01,
            "latency_seconds": 0.08,
            "requests_total": 28.0
        }])
    
    t = threading.Thread(target=flash_crowd_worker, daemon=True)
    t.start()
    return {
        "status": "started",
        "scenario": "benign_flash_crowd",
        "description": "High RPS benign flash crowd dispatched. Tests false-positive suppression.",
        "duration_seconds": 30
    }

@app.post("/api/scenarios/memory_leak")
def scenario_memory_leak():
    """Scenario 2: Progressive Memory Leak on Order Service"""
    res = inject_service_fault("order_service", "memory_leak")
    # Feed 3 progressive ticks so 1st-order slope beta and TTB countdown immediately activate
    try:
        import datetime
        now = datetime.datetime.now(datetime.timezone.utc)
        for m_val in [50.0, 56.5, 63.5]:
            evaluate_metrics_for_anomalies([{
                "time": now,
                "service_name": "order_service",
                "cpu_percent": 35.0,
                "memory_percent": m_val,
                "error_rate": 0.01,
                "latency_seconds": 0.065,
                "requests_total": 4.0
            }])
    except Exception as e:
        logger.error(f"Error initializing memory leak precursor: {e}")

    return {
        "status": "applied",
        "scenario": "progressive_memory_leak",
        "target": "order_service",
        "description": "Memory creeping upwards. Demonstrates 1st-order drift slope and proactive TTB warning."
    }

@app.post("/api/scenarios/gateway_timeout")
def scenario_gateway_timeout():
    """Scenario 3: Gateway Contention / Timeout on Payment Service"""
    res = inject_service_fault("payment_service", "gateway_timeout")
    return {
        "status": "applied",
        "scenario": "gateway_timeout",
        "target": "payment_service",
        "description": "Downstream payment latency spike. Tests decoupled load ratio and root-cause localization."
    }

@app.post("/api/scenarios/cascade_failure")
def scenario_cascade_failure():
    """Scenario 4: Systemic Cascade Failure across Cluster"""
    inject_service_fault("user_service", "cascade_failure")
    inject_service_fault("order_service", "cascade_failure")
    inject_service_fault("payment_service", "cascade_failure")
    return {
        "status": "applied",
        "scenario": "cascade_failure",
        "target": "all_services",
        "description": "High CPU, high latency, and high error rate propagated across all services."
    }

@app.post("/api/scenarios/reset")
def scenario_reset():
    """Reset all services to normal baseline operations"""
    global flash_crowd_running
    flash_crowd_running = False
    import datetime
    now = datetime.datetime.now(datetime.timezone.utc)
    for s in SERVICES_LIST:
        try:
            inject_service_fault(s, "normal")
            # Clear hybrid engine history with clean baseline tick
            evaluate_metrics_for_anomalies([{
                "time": now,
                "service_name": s,
                "cpu_percent": 24.0,
                "memory_percent": 45.0,
                "error_rate": 0.005,
                "latency_seconds": 0.045,
                "requests_total": 2.5
            }])
        except Exception:
            pass
    return {"status": "success", "message": "All microservices reset to NORMAL operating mode"}

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
