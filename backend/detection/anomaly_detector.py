import logging
import json
from backend.models.isolation_forest import anomaly_detector_model
from backend.detection.alert_manager import alert_manager
from backend.database import insert_anomaly_event

logger = logging.getLogger("sentinelops.detection")

def evaluate_metrics_for_anomalies(records: list[dict]):
    """
    Evaluates newly collected metric records using Isolation Forest.
    If anomaly is detected, logs event to database and triggers alert.
    """
    for rec in records:
        svc = rec.get("service_name")
        cpu = rec.get("cpu_percent", 0.0)
        mem = rec.get("memory_percent", 0.0)
        err = rec.get("error_rate", 0.0)
        lat = rec.get("latency_seconds", 0.0)
        req = rec.get("requests_total", 0.0)

        # Run Isolation Forest prediction
        eval_res = anomaly_detector_model.predict_sample(
            cpu=cpu,
            memory=mem,
            error_rate=err,
            latency=lat,
            requests=req
        )

        is_anomaly = eval_res["is_anomaly"]
        anomaly_score = eval_res["anomaly_score"]
        severity = eval_res["severity"]

        # Only log and alert on true anomalies
        if is_anomaly:
            details = {
                "cpu_percent": cpu,
                "memory_percent": mem,
                "error_rate": err,
                "latency_seconds": lat,
                "requests_total": req,
                "raw_score": eval_res["raw_score"]
            }

            event = {
                "service_name": svc,
                "model_name": "isolation_forest",
                "anomaly_score": anomaly_score,
                "is_anomaly": is_anomaly,
                "severity": severity,
                "details": json.dumps(details)
            }

            insert_anomaly_event(event)
            alert_manager.send_alert(
                service_name=svc,
                model_name="isolation_forest",
                anomaly_score=anomaly_score,
                severity=severity,
                details=details
            )
