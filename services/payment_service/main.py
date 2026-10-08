from fastapi import FastAPI, Response, status
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, Gauge, make_asgi_app
import time
import random

app = FastAPI(title="Payment Service", version="1.0.0")

# Prometheus Metrics
REQUESTS = Counter('http_requests_total', 'Total HTTP requests', ['service', 'method', 'endpoint', 'status'])
LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency in seconds', ['service', 'endpoint'])
CPU = Gauge('simulated_cpu_percent', 'Simulated CPU usage percentage', ['service'])
MEMORY = Gauge('simulated_memory_percent', 'Simulated memory usage percentage', ['service'])
ERROR_RATE = Gauge('current_error_rate', 'Simulated error rate probability', ['service'])

SERVICE_NAME = "payment_service"

# Mount Prometheus metrics endpoint at /metrics
app.mount("/metrics", make_asgi_app())

# Fault mode states: 'normal', 'high_latency', 'gateway_timeout', 'cascade_failure'
FAULT_MODE = "normal"

class PaymentProcessRequest(BaseModel):
    order_id: int
    user_id: int
    amount: float
    payment_method: str = "credit_card"

@app.get("/")
def root():
    return {"service": SERVICE_NAME, "status": "running", "fault_mode": FAULT_MODE}

@app.get("/health")
def health():
    return {"status": "healthy" if FAULT_MODE == "normal" else "degraded", "service": SERVICE_NAME}

@app.post("/payments/process")
def process_payment(payment: PaymentProcessRequest, response: Response):
    global FAULT_MODE
    start_time = time.time()

    if FAULT_MODE == "normal":
        base_cpu, latency_ms, error_prob = 35, random.uniform(50, 120), 0.02
    elif FAULT_MODE == "high_latency":
        base_cpu, latency_ms, error_prob = 70, random.uniform(600, 1200), 0.12
    elif FAULT_MODE == "gateway_timeout":
        base_cpu, latency_ms, error_prob = 85, random.uniform(1200, 2000), 0.40
    elif FAULT_MODE == "cascade_failure":
        base_cpu, latency_ms, error_prob = 98, random.uniform(2500, 4000), 0.60
    else:
        base_cpu, latency_ms, error_prob = 35, 80, 0.02

    time.sleep(latency_ms / 1000.0)

    # Dynamic metrics update
    current_cpu = min(100.0, max(5.0, base_cpu + random.gauss(0, 3.5)))
    current_mem = min(100.0, max(15.0, 55.0 + random.gauss(0, 2.5)))
    CPU.labels(service=SERVICE_NAME).set(current_cpu)
    MEMORY.labels(service=SERVICE_NAME).set(current_mem)
    ERROR_RATE.labels(service=SERVICE_NAME).set(error_prob)

    duration = time.time() - start_time
    LATENCY.labels(service=SERVICE_NAME, endpoint="/payments/process").observe(duration)

    if random.random() < error_prob:
        response.status_code = status.HTTP_502_BAD_GATEWAY
        REQUESTS.labels(service=SERVICE_NAME, method="POST", endpoint="/payments/process", status="502").inc()
        return {"error": "Payment gateway unreachable", "transaction_status": "FAILED", "fault_mode": FAULT_MODE}

    REQUESTS.labels(service=SERVICE_NAME, method="POST", endpoint="/payments/process", status="200").inc()
    return {
        "transaction_id": f"tx_{random.randint(100000, 999999)}",
        "order_id": payment.order_id,
        "amount": payment.amount,
        "status": "SUCCESS",
        "service": SERVICE_NAME
    }

@app.post("/fault/{mode}")
def inject_fault(mode: str):
    global FAULT_MODE
    valid_modes = ["normal", "high_latency", "gateway_timeout", "cascade_failure"]
    if mode not in valid_modes:
        return {"error": f"Invalid mode. Choose from {valid_modes}"}
    
    FAULT_MODE = mode
    if mode == "normal":
        CPU.labels(service=SERVICE_NAME).set(32.0)
        MEMORY.labels(service=SERVICE_NAME).set(55.0)
        ERROR_RATE.labels(service=SERVICE_NAME).set(0.02)
    elif mode == "high_latency":
        CPU.labels(service=SERVICE_NAME).set(70.0)
        MEMORY.labels(service=SERVICE_NAME).set(60.0)
        ERROR_RATE.labels(service=SERVICE_NAME).set(0.12)
    elif mode == "gateway_timeout":
        CPU.labels(service=SERVICE_NAME).set(85.0)
        MEMORY.labels(service=SERVICE_NAME).set(65.0)
        ERROR_RATE.labels(service=SERVICE_NAME).set(0.40)
    elif mode == "cascade_failure":
        CPU.labels(service=SERVICE_NAME).set(98.0)
        MEMORY.labels(service=SERVICE_NAME).set(88.0)
        ERROR_RATE.labels(service=SERVICE_NAME).set(0.65)
        REQUESTS.labels(service=SERVICE_NAME, method="POST", endpoint="/payments/process", status="502").inc(10)
    return {"message": "Fault mode updated successfully", "service": SERVICE_NAME, "fault_mode": FAULT_MODE}
