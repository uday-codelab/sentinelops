from fastapi import FastAPI, Response, status
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, Gauge, make_asgi_app
import time
import random
from typing import Optional

app = FastAPI(title="Order Service", version="1.0.0")

# Prometheus Metrics
REQUESTS = Counter('http_requests_total', 'Total HTTP requests', ['service', 'method', 'endpoint', 'status'])
LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency in seconds', ['service', 'endpoint'])
CPU = Gauge('simulated_cpu_percent', 'Simulated CPU usage percentage', ['service'])
MEMORY = Gauge('simulated_memory_percent', 'Simulated memory usage percentage', ['service'])
ERROR_RATE = Gauge('current_error_rate', 'Simulated error rate probability', ['service'])

SERVICE_NAME = "order_service"

# Mount Prometheus metrics endpoint at /metrics
app.mount("/metrics", make_asgi_app())

# Fault mode states: 'normal', 'high_latency', 'cascade_failure', 'memory_leak'
FAULT_MODE = "normal"
simulated_memory_baseline = 50.0

class CreateOrderRequest(BaseModel):
    user_id: int
    item_id: int
    quantity: int = 1
    total_amount: float

@app.get("/")
def root():
    return {"service": SERVICE_NAME, "status": "running", "fault_mode": FAULT_MODE}

@app.get("/health")
def health():
    return {"status": "healthy" if FAULT_MODE == "normal" else "degraded", "service": SERVICE_NAME}

@app.post("/orders")
def create_order(order: CreateOrderRequest, response: Response):
    global FAULT_MODE, simulated_memory_baseline
    start_time = time.time()

    if FAULT_MODE == "normal":
        base_cpu, latency_ms, error_prob = 30, random.uniform(40, 90), 0.015
    elif FAULT_MODE == "high_latency":
        base_cpu, latency_ms, error_prob = 65, random.uniform(500, 1000), 0.10
    elif FAULT_MODE == "memory_leak":
        simulated_memory_baseline = min(98.0, simulated_memory_baseline + 2.0)
        base_cpu, latency_ms, error_prob = 75, random.uniform(200, 500), 0.20
    elif FAULT_MODE == "cascade_failure":
        base_cpu, latency_ms, error_prob = 94, random.uniform(1800, 3000), 0.50
    else:
        base_cpu, latency_ms, error_prob = 30, 60, 0.015

    time.sleep(latency_ms / 1000.0)

    # Dynamic metrics update
    current_cpu = min(100.0, max(5.0, base_cpu + random.gauss(0, 3.0)))
    current_mem = min(100.0, max(15.0, simulated_memory_baseline + random.gauss(0, 2.0)))
    CPU.labels(service=SERVICE_NAME).set(current_cpu)
    MEMORY.labels(service=SERVICE_NAME).set(current_mem)
    ERROR_RATE.labels(service=SERVICE_NAME).set(error_prob)

    duration = time.time() - start_time
    LATENCY.labels(service=SERVICE_NAME, endpoint="/orders").observe(duration)

    if random.random() < error_prob:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        REQUESTS.labels(service=SERVICE_NAME, method="POST", endpoint="/orders", status="500").inc()
        return {"error": "Failed to process order. Upstream service timeout.", "fault_mode": FAULT_MODE}

    REQUESTS.labels(service=SERVICE_NAME, method="POST", endpoint="/orders", status="201").inc()
    response.status_code = status.HTTP_201_CREATED
    return {
        "order_id": random.randint(10000, 99999),
        "user_id": order.user_id,
        "item_id": order.item_id,
        "status": "CONFIRMED",
        "service": SERVICE_NAME
    }

@app.get("/orders/{order_id}")
def get_order(order_id: int, response: Response):
    global FAULT_MODE
    start_time = time.time()

    latency_ms = random.uniform(20, 50) if FAULT_MODE == "normal" else random.uniform(300, 700)
    time.sleep(latency_ms / 1000.0)

    CPU.labels(service=SERVICE_NAME).set(min(100.0, max(5.0, 28 + random.gauss(0, 2))))
    MEMORY.labels(service=SERVICE_NAME).set(min(100.0, max(15.0, simulated_memory_baseline + random.gauss(0, 1.5))))
    ERROR_RATE.labels(service=SERVICE_NAME).set(0.01 if FAULT_MODE == "normal" else 0.15)

    duration = time.time() - start_time
    LATENCY.labels(service=SERVICE_NAME, endpoint="/orders/{order_id}").observe(duration)
    REQUESTS.labels(service=SERVICE_NAME, method="GET", endpoint="/orders/{order_id}", status="200").inc()

    return {"order_id": order_id, "status": "SHIPPED", "service": SERVICE_NAME}

@app.post("/fault/{mode}")
def inject_fault(mode: str):
    global FAULT_MODE, simulated_memory_baseline
    valid_modes = ["normal", "high_latency", "memory_leak", "cascade_failure"]
    if mode not in valid_modes:
        return {"error": f"Invalid mode. Choose from {valid_modes}"}
    
    FAULT_MODE = mode
    if mode == "normal":
        simulated_memory_baseline = 50.0
        CPU.labels(service=SERVICE_NAME).set(28.0)
        MEMORY.labels(service=SERVICE_NAME).set(50.0)
        ERROR_RATE.labels(service=SERVICE_NAME).set(0.015)
    elif mode == "high_latency":
        CPU.labels(service=SERVICE_NAME).set(65.0)
        MEMORY.labels(service=SERVICE_NAME).set(55.0)
        ERROR_RATE.labels(service=SERVICE_NAME).set(0.10)
    elif mode == "memory_leak":
        simulated_memory_baseline = 92.0
        CPU.labels(service=SERVICE_NAME).set(75.0)
        MEMORY.labels(service=SERVICE_NAME).set(92.0)
        ERROR_RATE.labels(service=SERVICE_NAME).set(0.20)
    elif mode == "cascade_failure":
        CPU.labels(service=SERVICE_NAME).set(96.0)
        MEMORY.labels(service=SERVICE_NAME).set(90.0)
        ERROR_RATE.labels(service=SERVICE_NAME).set(0.55)
        REQUESTS.labels(service=SERVICE_NAME, method="POST", endpoint="/orders", status="500").inc(5)
    return {"message": "Fault mode updated successfully", "service": SERVICE_NAME, "fault_mode": FAULT_MODE}
