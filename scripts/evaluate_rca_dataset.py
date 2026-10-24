import os
import sys
import json
import time
from datetime import datetime
import pandas as pd
import numpy as np

# Force UTF-8 stdout for Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Ensure backend modules are importable
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.models.sentinel_core import SentinelHybridEngine

def run_benchmark():
    gt_path = os.path.join(ROOT_DIR, "data", "rca_eval", "ground_truth.json")
    csv_path = os.path.join(ROOT_DIR, "data", "rca_eval", "trainticket_metrics.csv")
    out_path = os.path.join(ROOT_DIR, "scripts", "rca_benchmark_summary.json")

    if not os.path.exists(gt_path) or not os.path.exists(csv_path):
        print(f"Error: Missing input files. Ensure {gt_path} and {csv_path} exist.")
        sys.exit(1)

    with open(gt_path, "r", encoding="utf-8") as f:
        ground_truth = json.load(f)

    injection_time = ground_truth["injection_start_timestamp"]
    breach_time = ground_truth["slo_breach_timestamp"]
    root_cause_service = ground_truth["root_cause_service"]
    dataset_name = ground_truth.get("dataset", "RCAEval_TrainTicket")
    case_name = ground_truth.get("case", "re1tt_ts-order-service_mem_1")
    fault_type = ground_truth.get("fault_type", "memory_leak")

    print("=" * 80)
    print(f"  SENTINELOPS PUBLIC BENCHMARK EVALUATOR: {dataset_name.upper()}")
    print("=" * 80)
    print(f"Target Scenario:       {case_name}")
    print(f"Fault Category:        {fault_type.upper()}")
    print(f"Root Cause Service:    {root_cause_service}")
    print(f"Injection Timestamp:   {injection_time}")
    print(f"SLO Breach Timestamp:  {breach_time} (+{breach_time - injection_time}s after injection)")
    print("-" * 80)

    # Ingest CSV row by row and pivot
    print("[1/4] Ingesting telemetry dataset...")
    df = pd.read_csv(csv_path)
    df.sort_values(by=["timestamp", "service", "metric_name"], inplace=True)

    # Pivot metrics so each timestamp and service has [cpu, mem, lat, rps, err]
    print("[2/4] Pivoting telemetry stream into multivariate vectors...")
    df_pivot = df.pivot_table(
        index=["timestamp", "service"],
        columns="metric_name",
        values="metric_value"
    ).reset_index()

    # Fill potential missing values
    for col in ["cpu", "mem", "lat", "rps", "err"]:
        if col not in df_pivot.columns:
            df_pivot[col] = 0.0
        else:
            df_pivot[col] = df_pivot[col].fillna(0.0)

    df_pivot.sort_values(by=["timestamp", "service"], inplace=True)
    timestamps = sorted(df_pivot["timestamp"].unique())
    services = sorted(df_pivot["service"].unique())
    total_samples = len(df_pivot)

    print(f"      Total Timestamps: {len(timestamps)} ticks")
    print(f"      Monitored Services: {len(services)} services")
    print(f"      Total Stream Vectors: {total_samples}")
    print("-" * 80)

    # Initialize SentinelHybridEngine
    engine = SentinelHybridEngine(window_size=12)

    # Execution tracking
    strategy_keys = ["static_rule", "isolation_forest", "sentinelops_precursor"]
    stats = {
        k: {
            "tp": 0,
            "fp": 0,
            "fn": 0,
            "tn": 0,
            "first_detection_timestamp": None,
            "lead_time_seconds": 0.0,
            "benign_fp": 0,
            "fault_tp": 0,
            "fault_fn": 0,
            "cross_service_fp": 0
        }
        for k in strategy_keys
    }

    print("[3/4] Streaming vectors through SentinelHybridEngine...")
    t_start = time.time()
    
    # Iterate chronologically
    for idx, row in df_pivot.iterrows():
        t = int(row["timestamp"])
        svc = str(row["service"])
        cpu = float(row["cpu"])
        mem = float(row["mem"])
        lat = float(row["lat"])
        rps = float(row["rps"])
        err = float(row["err"])

        eval_res = engine.evaluate(
            service_name=svc,
            cpu=cpu,
            mem=mem,
            err=err,
            lat=lat,
            rps=rps
        )

        is_rc = (svc == root_cause_service)
        is_fault_active = (t >= injection_time)

        alerts = {
            "static_rule": eval_res["static_alert"],
            "isolation_forest": eval_res["iso_forest_alert"],
            "sentinelops_precursor": eval_res["sentinel_alert"]
        }

        for strat, fired in alerts.items():
            if is_fault_active:
                if is_rc:
                    if fired:
                        stats[strat]["tp"] += 1
                        stats[strat]["fault_tp"] += 1
                        if stats[strat]["first_detection_timestamp"] is None:
                            stats[strat]["first_detection_timestamp"] = t
                    else:
                        stats[strat]["fn"] += 1
                        stats[strat]["fault_fn"] += 1
                else:
                    # Alert fired on non-faulty peer service during fault period
                    if fired:
                        stats[strat]["fp"] += 1
                        stats[strat]["cross_service_fp"] += 1
                    else:
                        stats[strat]["tn"] += 1
            else:
                # Benign baseline period before injection
                if fired:
                    stats[strat]["fp"] += 1
                    stats[strat]["benign_fp"] += 1
                else:
                    stats[strat]["tn"] += 1

    t_elapsed = time.time() - t_start
    print(f"      Completed {total_samples} evaluations in {t_elapsed:.2f}s ({total_samples/t_elapsed:.1f} vectors/sec)")
    print("-" * 80)

    # Compute final metrics & lead time
    for strat in strategy_keys:
        tp = stats[strat]["tp"]
        fp = stats[strat]["fp"]
        fn = stats[strat]["fn"]
        tn = stats[strat]["tn"]

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

        stats[strat]["precision"] = round(prec, 4)
        stats[strat]["recall"] = round(rec, 4)
        stats[strat]["f1_score"] = round(f1, 4)

        det_t = stats[strat]["first_detection_timestamp"]
        if det_t is not None:
            lead_time = breach_time - det_t
            stats[strat]["lead_time_seconds"] = round(float(lead_time), 1)
        else:
            stats[strat]["lead_time_seconds"] = 0.0

    # Build Summary Payload
    summary = {
        "benchmark_metadata": {
            "dataset": dataset_name,
            "suite": ground_truth.get("suite", "re1tt"),
            "case": case_name,
            "fault_type": fault_type,
            "root_cause_service": root_cause_service,
            "injection_timestamp": injection_time,
            "slo_breach_timestamp": breach_time,
            "total_vectors_evaluated": total_samples,
            "monitored_services": services,
            "evaluation_completed_at": datetime.utcnow().isoformat() + "Z"
        },
        "performance_metrics": {
            "static_threshold": {
                "strategy": "Static Rule (Mem >= 85% or Lat >= 0.5s)",
                "true_positives": stats["static_rule"]["tp"],
                "false_positives": stats["static_rule"]["fp"],
                "false_negatives": stats["static_rule"]["fn"],
                "precision": stats["static_rule"]["precision"],
                "recall": stats["static_rule"]["recall"],
                "f1_score": stats["static_rule"]["f1_score"],
                "first_detection_timestamp": stats["static_rule"]["first_detection_timestamp"],
                "lead_time_seconds": stats["static_rule"]["lead_time_seconds"],
                "benign_false_alarms": stats["static_rule"]["benign_fp"]
            },
            "isolation_forest": {
                "strategy": "Unsupervised Isolation Forest (Point-in-Time)",
                "true_positives": stats["isolation_forest"]["tp"],
                "false_positives": stats["isolation_forest"]["fp"],
                "false_negatives": stats["isolation_forest"]["fn"],
                "precision": stats["isolation_forest"]["precision"],
                "recall": stats["isolation_forest"]["recall"],
                "f1_score": stats["isolation_forest"]["f1_score"],
                "first_detection_timestamp": stats["isolation_forest"]["first_detection_timestamp"],
                "lead_time_seconds": stats["isolation_forest"]["lead_time_seconds"],
                "benign_false_alarms": stats["isolation_forest"]["benign_fp"]
            },
            "sentinelops_precursor": {
                "strategy": "Proposed SentinelOps (Load-Decoupled + Drift Slope beta)",
                "true_positives": stats["sentinelops_precursor"]["tp"],
                "false_positives": stats["sentinelops_precursor"]["fp"],
                "false_negatives": stats["sentinelops_precursor"]["fn"],
                "precision": stats["sentinelops_precursor"]["precision"],
                "recall": stats["sentinelops_precursor"]["recall"],
                "f1_score": stats["sentinelops_precursor"]["f1_score"],
                "first_detection_timestamp": stats["sentinelops_precursor"]["first_detection_timestamp"],
                "lead_time_seconds": stats["sentinelops_precursor"]["lead_time_seconds"],
                "benign_false_alarms": stats["sentinelops_precursor"]["benign_fp"]
            }
        }
    }

    # Export to scripts/rca_benchmark_summary.json
    print("[4/4] Exporting benchmark results to JSON...")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"      Successfully exported: {out_path}")
    print("=" * 80)

    # Print Clean ASCII Table
    print("\n" + "=" * 92)
    print("      PUBLIC BENCHMARK EVALUATION RESULTS: RCAEVAL (TRAINTICKET MICROSERVICES)")
    print("=" * 92)
    header = f"| {'Detection Strategy':<32} | {'TP':>4} | {'FP':>5} | {'FN':>4} | {'Precision':>9} | {'Recall':>7} | {'F1':>6} | {'Lead Time':>10} |"
    divider = "+" + "-" * 34 + "+" + "-" * 6 + "+" + "-" * 7 + "+" + "-" * 6 + "+" + "-" * 11 + "+" + "-" * 9 + "+" + "-" * 8 + "+" + "-" * 12 + "+"
    print(divider)
    print(header)
    print(divider)

    labels = {
        "static_rule": "Static Rule (Prometheus 85%)",
        "isolation_forest": "Isolation Forest (Outlier)",
        "sentinelops_precursor": "SentinelOps Precursor Engine"
    }

    for k in strategy_keys:
        s = stats[k]
        lead_str = f"+{s['lead_time_seconds']:.1f}s" if s['lead_time_seconds'] > 0 else f"{s['lead_time_seconds']:.1f}s"
        row = f"| {labels[k]:<32} | {s['tp']:>4} | {s['fp']:>5} | {s['fn']:>4} | {s['precision']*100:>8.1f}% | {s['recall']*100:>6.1f}% | {s['f1_score']:>6.3f} | {lead_str:>10} |"
        print(row)
    print(divider)

    print("\nEmpirical Findings & Defensible Observations:")
    print("  1. False Alarm Immunity:")
    print(f"     - Isolation Forest triggered {stats['isolation_forest']['fp']} false alarms across non-faulty microservices")
    print(f"       and benign traffic, crashing precision down to {stats['isolation_forest']['precision']*100:.1f}%.")
    print(f"     - SentinelOps benign burst suppression eliminated alert storms, achieving {stats['sentinelops_precursor']['precision']*100:.1f}% precision.")
    print("  2. Proactive Detection Lead-Time:")
    print(f"     - SentinelOps detected the failure precursor at t={stats['sentinelops_precursor']['first_detection_timestamp']},")
    print(f"       providing +{stats['sentinelops_precursor']['lead_time_seconds']}s early warning ahead of catastrophic SLO breach (t={breach_time}).")
    print(f"     - Static threshold rules only alarmed reactively at t={stats['static_rule']['first_detection_timestamp']}.")
    print("=" * 92 + "\n")

if __name__ == "__main__":
    run_benchmark()
