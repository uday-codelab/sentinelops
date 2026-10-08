import psycopg2
from psycopg2.extras import execute_values, RealDictCursor
from backend.config import settings
import logging

logger = logging.getLogger("sentinelops.database")

def get_db_connection():
    """Get a raw psycopg2 connection to TimescaleDB"""
    return psycopg2.connect(settings.DATABASE_URL)

def insert_service_metrics(metrics: list[dict]):
    """
    Batch insert metric rows into TimescaleDB hypertable 'service_metrics'.
    Each dict contains: time, service_name, cpu_percent, memory_percent, requests_total, error_rate, latency_seconds
    """
    if not metrics:
        return
    
    query = """
        INSERT INTO service_metrics (time, service_name, cpu_percent, memory_percent, requests_total, error_rate, latency_seconds)
        VALUES %s
    """
    records = [
        (
            m["time"],
            m["service_name"],
            m.get("cpu_percent", 0.0),
            m.get("memory_percent", 0.0),
            m.get("requests_total", 0.0),
            m.get("error_rate", 0.0),
            m.get("latency_seconds", 0.0)
        )
        for m in metrics
    ]
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                execute_values(cur, query, records)
                conn.commit()
    except Exception as e:
        logger.error(f"Error saving metrics to TimescaleDB: {e}")

def insert_anomaly_event(event: dict):
    """
    Insert a detected anomaly record into 'anomaly_events' table.
    """
    query = """
        INSERT INTO anomaly_events (time, service_name, model_name, anomaly_score, is_anomaly, severity, details)
        VALUES (NOW(), %(service_name)s, %(model_name)s, %(anomaly_score)s, %(is_anomaly)s, %(severity)s, %(details)s)
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, event)
                conn.commit()
    except Exception as e:
        logger.error(f"Error logging anomaly event: {e}")

def fetch_recent_metrics(service_name: str = None, minutes: int = 30):
    """
    Fetch metrics for the past N minutes from TimescaleDB.
    """
    query = """
        SELECT time, service_name, cpu_percent, memory_percent, requests_total, error_rate, latency_seconds
        FROM service_metrics
        WHERE time >= NOW() - INTERVAL '%s minutes'
    """
    params = [minutes]
    if service_name:
        query += " AND service_name = %s"
        params.append(service_name)
    query += " ORDER BY time ASC"

    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                return cur.fetchall()
    except Exception as e:
        logger.error(f"Error fetching metrics from TimescaleDB: {e}")
        return []

def fetch_recent_anomalies(limit: int = 50):
    """
    Fetch recent anomalies detected by ML models.
    """
    query = """
        SELECT id, time, service_name, model_name, anomaly_score, is_anomaly, severity, details
        FROM anomaly_events
        ORDER BY time DESC
        LIMIT %s
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, (limit,))
                return cur.fetchall()
    except Exception as e:
        logger.error(f"Error fetching anomalies: {e}")
        return []
