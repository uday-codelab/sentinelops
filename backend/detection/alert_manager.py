import logging
import json
from datetime import datetime
from backend.config import settings

logger = logging.getLogger("sentinelops.alerts")

class AlertManager:
    """Handles anomaly event dispatching and notification delivery"""
    
    @staticmethod
    def send_alert(service_name: str, model_name: str, anomaly_score: float, severity: str, details: dict):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        alert_msg = (
            f"🚨 [SENTINELOPS ALERT] [{severity}] Service: {service_name} | "
            f"Model: {model_name} | Score: {anomaly_score:.2f} | Time: {timestamp}\n"
            f"Details: {json.dumps(details, indent=2)}"
        )
        
        if severity == "CRITICAL":
            logger.critical(alert_msg)
        else:
            logger.warning(alert_msg)

        # Optional: dispatch to Slack webhook or Email if configured
        if settings.SLACK_WEBHOOK_URL:
            # can post to webhook
            pass

alert_manager = AlertManager()
