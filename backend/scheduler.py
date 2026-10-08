import requests
import datetime
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from backend.config import settings
from backend.database import insert_service_metrics

logger = logging.getLogger("sentinelops.collector")

SERVICES = ["user_service", "order_service", "payment_service"]

def query_prometheus_instant(metric_name: str) -> dict[str, float]:
    """
    Query Prometheus instant vector for a given metric.
    Returns a dict of {service_name: value}.
    """
    url = f"{settings.PROMETHEUS_URL}/api/v1/query"
    try:
        response = requests.get(url, params={"query": metric_name}, timeout=3)
        if response.status_code == 200:
            data = response.json()
            results = {}
            if data.get("status") == "success":
                for item in data["data"]["result"]:
                    # Check service label or job name
                    svc = item["metric"].get("service") or item["metric"].get("job", "unknown")
                    val = float(item["value"][1])
                    results[svc] = val
                return results
    except Exception as e:
        logger.debug(f"Failed to query Prometheus for metric '{metric_name}': {e}")
    return {}

def collect_metrics_job():
    """
    Scheduled job that scrapes Prometheus, aggregates RED metrics,
    and inserts them into TimescaleDB.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    
    cpu_data = query_prometheus_instant("simulated_cpu_percent")
    mem_data = query_prometheus_instant("simulated_memory_percent")
    err_data = query_prometheus_instant("current_error_rate")
    req_data = query_prometheus_instant("sum(rate(http_requests_total[1m])) by (service)")
    lat_data = query_prometheus_instant("rate(http_request_duration_seconds_sum[1m]) / clamp_min(rate(http_request_duration_seconds_count[1m]), 0.0001)")

    records = []
    for svc in SERVICES:
        # Check if we have data for this service
        cpu = cpu_data.get(svc, 25.0)
        mem = mem_data.get(svc, 45.0)
        err = err_data.get(svc, 0.01)
        req = req_data.get(svc, 2.0)
        lat = lat_data.get(svc, 0.05)

        # Only insert if the service is active in Prometheus
        if svc in cpu_data:
            records.append({
                "time": now,
                "service_name": svc,
                "cpu_percent": cpu,
                "memory_percent": mem,
                "requests_total": req,
                "error_rate": err,
                "latency_seconds": lat
            })

    if records:
        insert_service_metrics(records)
        logger.info(f"Collected and stored metrics for {len(records)} services at {now.strftime('%H:%M:%S')}")
        
        # Run real-time ML anomaly detection
        try:
            from backend.detection.anomaly_detector import evaluate_metrics_for_anomalies
            evaluate_metrics_for_anomalies(records)
        except Exception as e:
            logger.error(f"Error running anomaly detector: {e}")
    else:
        logger.debug("No active service metrics found in Prometheus.")

def start_metrics_scheduler():
    """Start APScheduler in background"""
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        collect_metrics_job, 
        'interval', 
        seconds=settings.COLLECTOR_INTERVAL_SECONDS, 
        id="prometheus_collector"
    )
    scheduler.start()
    logger.info(f"Prometheus metrics collector started (every {settings.COLLECTOR_INTERVAL_SECONDS}s)")
    return scheduler
