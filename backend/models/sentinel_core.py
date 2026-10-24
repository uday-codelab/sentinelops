import numpy as np
import collections
import logging
from backend.models.isolation_forest import anomaly_detector_model

logger = logging.getLogger("sentinelops.ml.sentinel_core")

class SentinelHybridEngine:
    """
    Precursor-Aware SentinelOps Hybrid Engine.
    Evaluates three detection strategies side-by-side:
      1. Static Threshold Rule (Prometheus-style: Mem >= 85% or Lat >= 0.50s)
      2. Unsupervised Isolation Forest (Point-in-time multivariate outlier)
      3. Proposed Sentinel Precursor Engine:
         - Bivariate Load Normalization (Latency / max(RPS, 0.5))
         - Sliding window 1st-order temporal drift slope (beta)
         - Proactive Time-to-Breach (TTB) calculation
         - Benign flash crowd burst suppression
    """
    def __init__(self, window_size: int = 12):
        self.window_size = window_size
        # Rolling temporal buffer per service (stores last 12 ticks, ~3 mins at 15s scrape interval)
        self.history = collections.defaultdict(lambda: collections.deque(maxlen=window_size))
        # Thread-safe in-memory cache of latest evaluation per service
        self.latest_evaluations = {}

    def get_latest_state(self) -> dict:
        """Returns a snapshot of the latest evaluation state per service."""
        return dict(self.latest_evaluations)

    def evaluate(self, service_name: str, cpu: float, mem: float, err: float, lat: float, rps: float, iso_res: dict = None) -> dict:
        buffer = self.history[service_name]
        buffer.append({
            "cpu": cpu,
            "mem": mem,
            "err": err,
            "lat": lat,
            "rps": rps
        })

        # -------------------------------------------------------------
        # 1. Strategy 1: Static Rule Baseline
        # -------------------------------------------------------------
        static_alert = bool(mem >= 85.0 or lat >= 0.50)

        # -------------------------------------------------------------
        # 2. Strategy 2: Isolation Forest Baseline (Point-in-Time Outlier)
        # -------------------------------------------------------------
        if iso_res is None:
            iso_res = anomaly_detector_model.predict_sample(cpu, mem, err, lat, rps)
        iso_forest_alert = bool(iso_res.get("is_anomaly", False))

        # -------------------------------------------------------------
        # 3. Strategy 3: Proposed Sentinel Precursor Engine
        # -------------------------------------------------------------
        # A) Bivariate Load Ratio: Decouples legitimate traffic demand from degradation
        load_ratio = float(lat / max(rps, 0.5))

        # B) 1st-Order Memory Drift Slope (beta = d(mem)/dt)
        mem_series = [tick["mem"] for tick in buffer]
        if len(mem_series) >= 3:
            x_axis = np.arange(len(mem_series))
            slope, _ = np.polyfit(x_axis, mem_series, 1)
            beta = float(slope)
        else:
            beta = 0.0

        # C) Proactive Precursor Lead-Time & Time-To-Breach (TTB)
        precursor_flag = False
        ttb_seconds = 0.0
        # If memory is creeping upwards (beta > 0.35% per 15s tick) and above baseline 40%
        if beta > 0.35 and mem >= 40.0:
            remaining_capacity = 85.0 - mem
            if remaining_capacity > 0:
                ttb_ticks = remaining_capacity / beta
                ttb_seconds = round(float(ttb_ticks * 15.0), 1)
                # Fire precursor early warning if failure is forecasted within 5 minutes (300s)
                if 0 < ttb_seconds <= 300.0:
                    precursor_flag = True

        # D) Benign Burst Suppression:
        # High CPU/latency during a traffic surge is NOT internal failure if load ratio and memory slope are low
        is_burst_suppressed = False
        if (cpu > 70.0 or lat > 0.3) and (load_ratio <= 0.08 and beta <= 0.20):
            is_burst_suppressed = True

        # E) Sentinel Decision Synthesis
        sentinel_alert = False
        severity = "NORMAL"

        if precursor_flag:
            sentinel_alert = True
            severity = "CRITICAL" if ttb_seconds <= 90 else "WARNING"
        elif mem >= 85.0:
            sentinel_alert = True
            severity = "CRITICAL"
        elif (lat >= 0.50 or err >= 0.15) and not is_burst_suppressed:
            sentinel_alert = True
            severity = "CRITICAL" if (err >= 0.40 or lat >= 1.5) else "WARNING"

        res = {
            "service": service_name,
            "static_alert": static_alert,
            "iso_forest_alert": iso_forest_alert,
            "sentinel_alert": sentinel_alert,
            "precursor_alert": precursor_flag,
            "is_burst_suppressed": is_burst_suppressed,
            "severity": severity,
            "trend_slope": round(beta, 4),
            "estimated_ttb_seconds": round(ttb_seconds, 1),
            "load_ratio": round(load_ratio, 4),
            "details": {
                "cpu_percent": cpu,
                "memory_percent": mem,
                "error_rate": err,
                "latency_seconds": lat,
                "requests_total": rps,
                "raw_score": iso_res.get("raw_score", 0.0),
                "precursor_flag": precursor_flag,
                "ttb_seconds": round(ttb_seconds, 1),
                "trend_slope": round(beta, 4),
                "load_ratio": round(load_ratio, 4),
                "burst_suppressed": is_burst_suppressed
            }
        }

        # Cache latest evaluation in-memory
        self.latest_evaluations[service_name] = res
        return res

# Global singleton hybrid engine
sentinel_hybrid_engine = SentinelHybridEngine()
