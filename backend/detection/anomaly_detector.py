import logging
import json
from backend.models.sentinel_core import sentinel_hybrid_engine
from backend.detection.alert_manager import alert_manager
from backend.database import insert_anomaly_event

logger = logging.getLogger("sentinelops.detection")

def evaluate_metrics_for_anomalies(records: list[dict]):
    """
    Evaluates newly collected metric records through the multi-strategy
    SentinelHybridEngine (Static, Isolation Forest, and Sentinel Precursor).
    Logs comparative telemetry and records alerts to TimescaleDB.
    """
    for rec in records:
        svc = rec.get("service_name")
        cpu = float(rec.get("cpu_percent", 0.0))
        mem = float(rec.get("memory_percent", 0.0))
        err = float(rec.get("error_rate", 0.0))
        lat = float(rec.get("latency_seconds", 0.0))
        req = float(rec.get("requests_total", 0.0))

        # Run multi-strategy evaluation
        eval_res = sentinel_hybrid_engine.evaluate(
            service_name=svc,
            cpu=cpu,
            mem=mem,
            err=err,
            lat=lat,
            rps=req
        )

        static_alert = eval_res["static_alert"]
        iso_alert = eval_res["iso_forest_alert"]
        sentinel_alert = eval_res["sentinel_alert"]
        precursor = eval_res["precursor_alert"]
        suppressed = eval_res["is_burst_suppressed"]
        beta = eval_res["trend_slope"]
        ttb = eval_res["estimated_ttb_seconds"]
        load_ratio = eval_res["load_ratio"]
        severity = eval_res["severity"]
        details = eval_res["details"]

        # Log comparative decisions in container stdout
        logger.info(
            f"[COMPARATIVE EVAL] Svc: {svc:15s} | "
            f"Sentinel: {'ALERT' if sentinel_alert else 'OK':5s} "
            f"(Precursor: {precursor}, TTB: {ttb:5.1f}s, BurstSuppressed: {suppressed}) | "
            f"IsoForest: {'ALERT' if iso_alert else 'OK':5s} | "
            f"Static: {'ALERT' if static_alert else 'OK':5s} | "
            f"Slope: {beta:+.4f} | LoadRatio: {load_ratio:.4f}"
        )

        # Determine if any model triggered an alert
        has_any_alert = sentinel_alert or iso_alert or static_alert

        if has_any_alert:
            # Determine primary model attribution
            if precursor:
                model_name = "sentinel_precursor"
                score = round(min(1.0, max(0.5, 1.0 - (ttb / 300.0))), 3)
            elif sentinel_alert:
                model_name = "sentinel_hybrid"
                score = 0.95 if severity == "CRITICAL" else 0.75
            elif iso_alert:
                model_name = "isolation_forest"
                score = float(details.get("raw_score", 0.0))
            else:
                model_name = "static_rule"
                score = 1.0

            event_details = {
                **details,
                "static_alert": static_alert,
                "iso_forest_alert": iso_alert,
                "sentinel_alert": sentinel_alert,
                "model_attribution": model_name,
                "ttb_seconds": ttb
            }

            event = {
                "service_name": svc,
                "model_name": model_name,
                "anomaly_score": score,
                "is_anomaly": True,
                "severity": severity if sentinel_alert else ("CRITICAL" if static_alert else "WARNING"),
                "details": json.dumps(event_details)
            }

            try:
                insert_anomaly_event(event)
            except Exception as e:
                logger.error(f"Failed to insert anomaly event for {svc}: {e}")

            alert_manager.send_alert(
                service_name=svc,
                model_name=model_name,
                anomaly_score=score,
                severity=event["severity"],
                details=event_details
            )
