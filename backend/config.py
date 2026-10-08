import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://admin:password@localhost:5432/metrics_db"
    )
    PROMETHEUS_URL: str = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
    COLLECTOR_INTERVAL_SECONDS: int = int(os.getenv("COLLECTOR_INTERVAL_SECONDS", "15"))
    ALERT_EMAIL: str = os.getenv("ALERT_EMAIL", "")
    SLACK_WEBHOOK_URL: str = os.getenv("SLACK_WEBHOOK_URL", "")

settings = Settings()
