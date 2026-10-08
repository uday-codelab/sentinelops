from fastapi import FastAPI, Response, status
from prometheus_client import Counter, Histogram, Gauge, make_asgi_app
import time
import random

app = FastAPI(title="User Service", version="1.0.0")

# Prometheus Metrics
REQUESTS = Counter('http_requests_total', 'Total HTTP requests', ['service', 'method', 'endpoint', 'status'])
LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency in seconds', ['service', 'endpoint'])
CPU = Gauge('simulated_cpu_percent', 'Simulated CPU usage percentage', ['service'])
MEMORY = Gauge('simulated_memory_percent', 'Simulated memory usage percentage', ['service'])
ERROR_RATE = Gauge('current_error_rate', 'Simulated error rate probability', ['service'])

SERVICE_NAME = "user_service"

# Mount Prometheus metrics endpoint at /metrics
app.mount("/metrics", make_asgi_app())

# Fault mode states: 'normal', 'high_latency', 'cascade_failure', 'cpu_spike'
FAULT_MODE = "normal"

@app.get("/")
def root():
    return {"service": SERVICE_NAME, "status": "running", "fault_mode": FAULT_MODE}

@app.get("/health")
def health():
    return {"status": "healthy" if FAULT_MODE == "normal" else "degraded", "service": SERVICE_NAME}

@app.get("/users/{user_id}")
def get_user(user_id: int, response: Response):
    global FAULT_MODE
    start_time = time.time()

    # Determine simulated behavior based on current fault mode
    if FAULT_MODE == "normal":
        base_cpu, latency_ms, error_prob = 22, random.uniform(30, 70), 0.01
    elif FAULT_MODE == "high_latency":
        base_cpu, latency_ms, error_prob = 55, random.uniform(400, 800), 0.08
    elif FAULT_MODE == "cpu_spike":
        base_cpu, latency_ms, error_prob = 92, random.uniform(150, 300), 0.05
    elif FAULT_MODE == "cascade_failure":
        base_cpu, latency_ms, error_prob = 96, random.uniform(1500, 2500), 0.45
    else:
        base_cpu, latency_ms, error_prob = 25, 50, 0.01

    # Simulate processing time
    time.sleep(latency_ms / 1000.0)

    # Update dynamic gauges with slight jitter
    current_cpu = min(100.0, max(5.0, base_cpu + random.gauss(0, 2.5)))
    current_mem = min(100.0, max(10.0, 42.0 + random.gauss(0, 3.0)))
    CPU.labels(service=SERVICE_NAME).set(current_cpu)
    MEMORY.labels(service=SERVICE_NAME).set(current_mem)
    ERROR_RATE.labels(service=SERVICE_NAME).set(error_prob)

    duration = time.time() - start_time
    LATENCY.labels(service=SERVICE_NAME, endpoint="/users/{user_id}").observe(duration)

    # Simulate failure based on error probability
    if random.random() < error_prob:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        REQUESTS.labels(service=SERVICE_NAME, method="GET", endpoint="/users/{user_id}", status="500").inc()
        return {"error": "Internal Server Error in User Service", "fault_mode": FAULT_MODE}

    REQUESTS.labels(service=SERVICE_NAME, method="GET", endpoint="/users/{user_id}", status="200").inc()
    return {
        "user_id": user_id,
        "name": f"User_{user_id}",
        "email": f"user{user_id}@example.com",
        "service": SERVICE_NAME
    }

@app.post("/fault/{mode}")
def inject_fault(mode: str):
    global FAULT_MODE
    valid_modes = ["normal", "high_latency", "cpu_spike", "cascade_failure"]
    if mode not in valid_modes:
        return {"error": f"Invalid mode. Choose from {valid_modes}"}
    
    FAULT_MODE = mode
    if mode == "normal":
        CPU.labels(service=SERVICE_NAME).set(24.0)
        MEMORY.labels(service=SERVICE_NAME).set(42.0)
        ERROR_RATE.labels(service=SERVICE_NAME).set(0.01)
    elif mode == "high_latency":
        CPU.labels(service=SERVICE_NAME).set(60.0)
        MEMORY.labels(service=SERVICE_NAME).set(55.0)
        ERROR_RATE.labels(service=SERVICE_NAME).set(0.08)
    elif mode == "cpu_spike":
        CPU.labels(service=SERVICE_NAME).set(95.0)
        MEMORY.labels(service=SERVICE_NAME).set(60.0)
        ERROR_RATE.labels(service=SERVICE_NAME).set(0.05)
    elif mode == "cascade_failure":
        CPU.labels(service=SERVICE_NAME).set(98.0)
        MEMORY.labels(service=SERVICE_NAME).set(85.0)
        ERROR_RATE.labels(service=SERVICE_NAME).set(0.50)
        REQUESTS.labels(service=SERVICE_NAME, method="GET", endpoint="/users/{user_id}", status="500").inc(5)
    return {"message": "Fault mode updated successfully", "service": SERVICE_NAME, "fault_mode": FAULT_MODE}
