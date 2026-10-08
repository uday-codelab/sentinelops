-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- 1. Table for storing collected service metrics
CREATE TABLE IF NOT EXISTS service_metrics (
    time TIMESTAMPTZ NOT NULL,
    service_name VARCHAR(50) NOT NULL,
    cpu_percent DOUBLE PRECISION,
    memory_percent DOUBLE PRECISION,
    requests_total DOUBLE PRECISION,
    error_rate DOUBLE PRECISION,
    latency_seconds DOUBLE PRECISION
);

-- Convert service_metrics into a TimescaleDB hypertable partitioned by time
SELECT create_hypertable('service_metrics', 'time', if_not_exists => TRUE);

-- Create index for fast query lookups per service and time
CREATE INDEX IF NOT EXISTS idx_service_metrics_svc_time ON service_metrics (service_name, time DESC);

-- 2. Table for storing detected anomaly events and ML scores
CREATE TABLE IF NOT EXISTS anomaly_events (
    id SERIAL PRIMARY KEY,
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    service_name VARCHAR(50) NOT NULL,
    model_name VARCHAR(50) NOT NULL,
    anomaly_score DOUBLE PRECISION NOT NULL,
    is_anomaly BOOLEAN NOT NULL DEFAULT FALSE,
    severity VARCHAR(20) DEFAULT 'INFO',
    details JSONB
);

CREATE INDEX IF NOT EXISTS idx_anomaly_events_time ON anomaly_events (time DESC);
