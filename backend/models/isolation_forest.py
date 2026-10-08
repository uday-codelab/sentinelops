import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
import joblib
import os
import logging

logger = logging.getLogger("sentinelops.ml.isolation_forest")

MODEL_PATH = os.path.join(os.path.dirname(__file__), "isolation_forest.joblib")

class ServiceAnomalyDetector:
    """
    Isolation Forest based anomaly detector for microservice metrics.
    Monitors 5 core features:
    [cpu_percent, memory_percent, error_rate, latency_seconds, requests_total]
    """
    def __init__(self, contamination: float = 0.01, random_state: int = 42):
        self.contamination = contamination
        self.model = IsolationForest(
            n_estimators=100,
            contamination=contamination,
            random_state=random_state,
            n_jobs=-1
        )
        self.is_trained = False
        self._load_if_exists()

    def _load_if_exists(self):
        if os.path.exists(MODEL_PATH):
            try:
                self.model = joblib.load(MODEL_PATH)
                self.is_trained = True
                logger.info(f"Loaded existing Isolation Forest model from {MODEL_PATH}")
            except Exception as e:
                logger.warning(f"Could not load model: {e}")

    def save(self):
        joblib.dump(self.model, MODEL_PATH)
        logger.info(f"Model saved to {MODEL_PATH}")

    def generate_synthetic_training_data(self, n_samples: int = 2000) -> pd.DataFrame:
        """
        Generate realistic baseline training data representing normal healthy operations.
        Healthy ranges:
        - CPU: 15% to 55%
        - Memory: 30% to 65%
        - Error rate: 0% to 2%
        - Latency: 20ms to 150ms (0.02s - 0.15s)
        - Requests: 0.5 to 8.0 req/sec
        """
        np.random.seed(42)
        cpu = np.random.uniform(15.0, 55.0, size=n_samples)
        memory = np.random.uniform(30.0, 65.0, size=n_samples)
        error_rate = np.random.uniform(0.0, 0.02, size=n_samples)
        latency = np.random.uniform(0.02, 0.15, size=n_samples)
        requests = np.random.uniform(0.5, 8.0, size=n_samples)

        df = pd.DataFrame({
            "cpu_percent": cpu,
            "memory_percent": memory,
            "error_rate": error_rate,
            "latency_seconds": latency,
            "requests_total": requests
        })
        return df

    def train_baseline(self, data: pd.DataFrame = None):
        """Train or retrain Isolation Forest on normal baseline data"""
        if data is None:
            data = self.generate_synthetic_training_data()
            
        features = ["cpu_percent", "memory_percent", "error_rate", "latency_seconds", "requests_total"]
        X = data[features].values
        self.model.fit(X)
        self.is_trained = True
        self.save()
        logger.info(f"Isolation Forest model calibrated on {len(X)} baseline samples.")
        return self

    def predict_sample(self, cpu: float, memory: float, error_rate: float, latency: float, requests: float) -> dict:
        """
        Evaluate a live metric sample.
        Returns:
            is_anomaly: bool
            anomaly_score: float (scaled: higher is more anomalous, range ~ 0.0 to 1.0)
            severity: NORMAL, WARNING, CRITICAL
        """
        if not self.is_trained:
            self.train_baseline()

        X = np.array([[cpu, memory, error_rate, latency, requests]])
        raw_score = self.model.decision_function(X)[0]
        prediction = self.model.predict(X)[0] # 1 is normal, -1 is anomaly

        # Convert raw_score (typically -0.25 to +0.25) to normalized severity
        severity = float(np.clip(0.5 - (raw_score * 2.5), 0.0, 1.0))
        # Anomaly is only declared when significantly outside normal boundary
        is_anomaly = bool(prediction == -1 and raw_score < -0.06)

        if not is_anomaly:
            severity_label = "NORMAL"
        elif severity > 0.8 or raw_score < -0.12:
            severity_label = "CRITICAL"
        else:
            severity_label = "WARNING"

        return {
            "is_anomaly": is_anomaly,
            "anomaly_score": round(severity, 4),
            "raw_score": round(float(raw_score), 4),
            "severity": severity_label
        }

# Global detector singleton
anomaly_detector_model = ServiceAnomalyDetector()
