import pandas as pd
import json
import os

os.makedirs("E:/Projects/sentinelops/data/rca_eval", exist_ok=True)
df = pd.read_parquet("E:/Projects/sentinelops/data/rca_eval/raw/metrics.parquet")

services = [
    'ts-order-service',
    'ts-travel-service',
    'ts-inside-payment-service',
    'ts-auth-service',
    'ts-station-service',
    'ts-basic-service',
    'ts-consign-service',
    'ts-food-service',
    'ts-ticketinfo-service',
    'ts-train-service'
]

CONTAINER_MEM_LIMIT = 524288000.0  # 500 MiB

records = []
# Downsample to 5s intervals (or every 5 seconds) to match standard Prometheus scrape cadence
df_sampled = df.iloc[::5].copy()

for idx, row in df_sampled.iterrows():
    t = int(row['time'])
    for s in services:
        c_cpu = f"{s}_cpu"
        c_mem = f"{s}_mem"
        c_lat = f"{s}_latency-90"
        c_rps = f"{s}_workload"
        c_err = f"{s}_error"
        
        cpu_val = float(row[c_cpu]) if c_cpu in df.columns else 0.0
        mem_bytes = float(row[c_mem]) if c_mem in df.columns else 0.0
        mem_pct = round((mem_bytes / CONTAINER_MEM_LIMIT) * 100.0, 2)
        lat_val = round(float(row[c_lat]), 4) if c_lat in df.columns else 0.0
        rps_val = round(float(row[c_rps]), 2) if c_rps in df.columns else 0.0
        err_val = round(float(row[c_err]), 4) if c_err in df.columns else 0.0
        
        records.append({'timestamp': t, 'service': s, 'metric_name': 'cpu', 'metric_value': round(cpu_val, 2)})
        records.append({'timestamp': t, 'service': s, 'metric_name': 'mem', 'metric_value': mem_pct})
        records.append({'timestamp': t, 'service': s, 'metric_name': 'lat', 'metric_value': lat_val})
        records.append({'timestamp': t, 'service': s, 'metric_name': 'rps', 'metric_value': rps_val})
        records.append({'timestamp': t, 'service': s, 'metric_name': 'err', 'metric_value': err_val})

df_out = pd.DataFrame(records)
df_out.sort_values(by=['timestamp', 'service', 'metric_name'], inplace=True)
csv_path = "E:/Projects/sentinelops/data/rca_eval/trainticket_metrics.csv"
df_out.to_csv(csv_path, index=False)
print(f"Exported {len(df_out)} rows to {csv_path}")

ground_truth = {
    "dataset": "RCAEval_TrainTicket",
    "suite": "re1tt",
    "case": "re1tt_ts-order-service_mem_1",
    "fault_type": "memory_leak",
    "root_cause_service": "ts-order-service",
    "injection_start_timestamp": 1693334559,
    "slo_breach_timestamp": 1693334585,
    "slo_breach_type": "memory_exhaustion_85_percent",
    "latency_breach_timestamp": 1693334576,
    "latency_threshold_seconds": 0.50,
    "memory_threshold_percent": 85.0,
    "trace_start_timestamp": int(df['time'].min()),
    "trace_end_timestamp": int(df['time'].max()),
    "total_duration_seconds": int(df['time'].max() - df['time'].min()),
    "benign_duration_seconds": int(1693334559 - df['time'].min()),
    "fault_duration_seconds": int(df['time'].max() - 1693334559),
    "sample_step_seconds": 5,
    "monitored_services": services
}

gt_path = "E:/Projects/sentinelops/data/rca_eval/ground_truth.json"
with open(gt_path, "w", encoding="utf-8") as f:
    json.dump(ground_truth, f, indent=2)
print(f"Wrote ground truth metadata to {gt_path}")
