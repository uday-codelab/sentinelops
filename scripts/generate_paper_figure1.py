"""
SentinelOps Paper - Figure 1 Architecture Diagram Generator
Generates publication-quality, high-resolution vector (PDF) and raster (PNG, 300 DPI)
diagrams for Figure 1 of the IEEE conference paper.
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle, PathPatch
from matplotlib.path import Path

def create_figure1():
    # IEEE Publication Styling Configuration
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']
    plt.rcParams['font.size'] = 9.5
    plt.rcParams['axes.edgecolor'] = '#333333'
    plt.rcParams['axes.linewidth'] = 0.8
    plt.rcParams['pdf.fonttype'] = 42
    plt.rcParams['ps.fonttype'] = 42

    # Canvas dimensions: 17.0 x 8.0 inches for crisp, uncompressed IEEE double-column span
    fig, ax = plt.subplots(figsize=(17.0, 8.0), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    # Color Palette (IEEE Standard Muted Architecture Palette)
    # Block 1 - Microservices (Steel Blue)
    C_B1_BG = '#f4f8fc'
    C_B1_BORDER = '#1f77b4'
    C_B1_CARD = '#ffffff'
    C_B1_ACCENT = '#1a568c'

    # Block 2 - Telemetry Ingestion (Slate Purple)
    C_B2_BG = '#f8f6fc'
    C_B2_BORDER = '#6f42c1'
    C_B2_CARD = '#ffffff'
    C_B2_ACCENT = '#522b94'

    # Block 3 - SentinelOps Core Engine (Teal & Forest Green)
    C_B3_BG = '#eef8f5'
    C_B3_BORDER = '#0d7377'
    C_B3_CARD_A = '#f2faf5'  # Stage 1: Load Filter
    C_B3_BORDER_A = '#2ca02c'
    C_B3_CARD_B = '#fffbf2'  # Stage 2: Drift & TTB
    C_B3_BORDER_B = '#d96b14'

    # Block 4 - Control Plane (Crimson & Coral)
    C_B4_BG = '#fcf4f4'
    C_B4_BORDER = '#d62728'
    C_B4_CARD = '#ffffff'
    C_B4_ACCENT = '#9b1c1c'

    # Helper function for drawing rounded boxes
    def draw_box(x, y, w, h, bg_color, border_color, border_width=1.2, radius=1.0, linestyle='-'):
        box = FancyBboxPatch(
            (x, y), w, h,
            boxstyle=f"round,pad=0.2,rounding_size={radius}",
            facecolor=bg_color,
            edgecolor=border_color,
            linewidth=border_width,
            linestyle=linestyle,
            zorder=2
        )
        ax.add_patch(box)
        return box

    # Helper for styled header pills
    def draw_header_pill(x, y, w, h, title, subtitle, bg_color, text_color='#ffffff'):
        pill = FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.15,rounding_size=0.8",
            facecolor=bg_color,
            edgecolor='none',
            zorder=3
        )
        ax.add_patch(pill)
        ax.text(x + w / 2, y + h * 0.62, title, color=text_color, weight='bold',
                ha='center', va='center', fontsize=10.5, zorder=4)
        if subtitle:
            ax.text(x + w / 2, y + h * 0.22, subtitle, color=text_color,
                    ha='center', va='center', fontsize=8.0, style='italic', zorder=4)

    # Helper for straight/curved arrows
    def draw_arrow(x1, y1, x2, y2, label="", color="#4a5568", style="->", lw=1.6, label_pos=0.5, label_offset=(0, 2.5), rad=0.0):
        connectionstyle = f"arc3,rad={rad}" if rad != 0.0 else "arc3,rad=0"
        arrow = FancyArrowPatch(
            (x1, y1), (x2, y2),
            arrowstyle=style,
            connectionstyle=connectionstyle,
            color=color,
            linewidth=lw,
            mutation_scale=14,
            zorder=6
        )
        ax.add_patch(arrow)
        if label:
            lx = x1 + (x2 - x1) * label_pos + label_offset[0]
            ly = y1 + (y2 - y1) * label_pos + label_offset[1]
            ax.text(lx, ly, label, fontsize=8.2, color='#2d3748', weight='bold',
                    ha='center', va='center',
                    bbox=dict(boxstyle="round,pad=0.25", facecolor="#ffffff", edgecolor="#cbd5e0", lw=0.7),
                    zorder=7)

    # -------------------------------------------------------------
    # TOP TITLE BANNER
    # -------------------------------------------------------------
    title_box = FancyBboxPatch((1.5, 93.0), 97.0, 5.8,
                               boxstyle="round,pad=0.2,rounding_size=0.8",
                               facecolor='#1a202c', edgecolor='#0d1117', linewidth=1.0, zorder=2)
    ax.add_patch(title_box)
    ax.text(50.0, 96.4, "Fig. 1: Architectural Workflow of the SentinelOps Precursor-Aware Autonomous Reliability Framework",
            color='#ffffff', weight='bold', ha='center', va='center', fontsize=12.2, zorder=3)
    ax.text(50.0, 94.3, "End-to-End Ingestion, Bivariate Traffic Decoupling, Linear Temporal Drift Estimation, and Proactive Mitigation Dispatch",
            color='#a0aec0', style='italic', ha='center', va='center', fontsize=8.6, zorder=3)

    # BASE Y-COORDINATES: Main panels run from Y=5.5 to Y=91.5 (giving Y=0.5 to Y=5.0 for bottom feedback loop)
    Y_BOTTOM = 5.5
    Y_HEIGHT = 86.0

    # -------------------------------------------------------------
    # BLOCK 1: MONITORED MICROSERVICE MESH
    # -------------------------------------------------------------
    draw_box(1.5, Y_BOTTOM, 20.5, Y_HEIGHT, C_B1_BG, C_B1_BORDER, border_width=1.5, radius=1.4)
    draw_header_pill(2.5, 84.5, 18.5, 5.6, "1. Microservice Mesh", "Target Cluster & Synthetic Workload", C_B1_BORDER)

    # User Service Card
    draw_box(2.8, 67.5, 17.9, 15.5, C_B1_CARD, '#cbd5e0', border_width=0.9)
    draw_box(3.2, 79.2, 17.1, 3.2, '#ebf8ff', C_B1_BORDER, border_width=0.8)
    ax.text(11.75, 80.8, "User Service (:8001)", weight='bold', color=C_B1_ACCENT, ha='center', va='center', fontsize=9.0, zorder=5)
    ax.text(3.8, 76.2, "• Endpoints: /auth, /users, /profile", fontsize=8.0, color='#4a5568', zorder=5)
    ax.text(3.8, 72.8, "• Runtime: FastAPI / Uvicorn", fontsize=8.0, color='#4a5568', zorder=5)
    ax.text(3.8, 69.4, "• Baseline Profile: Normal User Ops", fontsize=8.0, color='#4a5568', zorder=5)

    # Order Service Card (Primary Fault Target)
    draw_box(2.8, 48.0, 17.9, 18.0, C_B1_CARD, '#cbd5e0', border_width=0.9)
    draw_box(3.2, 62.0, 17.1, 3.4, '#fffaf0', '#dd6b20', border_width=0.8)
    ax.text(11.75, 63.7, "Order Service (:8002)", weight='bold', color='#c05621', ha='center', va='center', fontsize=9.0, zorder=5)
    ax.text(3.8, 58.5, "• Endpoints: /orders, /checkout", fontsize=8.0, color='#4a5568', zorder=5)
    ax.text(3.8, 55.0, "• Fault Hook: POST /fault/memory_leak", fontsize=8.0, color='#c53030', weight='bold', zorder=5)
    ax.text(3.8, 51.5, "• Drift Rate: 1.5 - 2.5 MB/s uncollected", fontsize=8.0, color='#4a5568', zorder=5)

    # Payment Service Card
    draw_box(2.8, 29.5, 17.9, 17.0, C_B1_CARD, '#cbd5e0', border_width=0.9)
    draw_box(3.2, 42.6, 17.1, 3.4, '#ebf8ff', C_B1_BORDER, border_width=0.8)
    ax.text(11.75, 44.3, "Payment Service (:8003)", weight='bold', color=C_B1_ACCENT, ha='center', va='center', fontsize=9.0, zorder=5)
    ax.text(3.8, 39.0, "• Endpoints: /pay, /refund", fontsize=8.0, color='#4a5568', zorder=5)
    ax.text(3.8, 35.5, "• Fault Hook: POST /fault/gateway_timeout", fontsize=8.0, color='#c53030', weight='bold', zorder=5)
    ax.text(3.8, 32.0, "• External Gateway Dependency", fontsize=8.0, color='#4a5568', zorder=5)

    # Emitted Telemetry Box
    draw_box(2.8, 7.0, 17.9, 21.0, '#e2e8f0', '#718096', border_width=1.0)
    ax.text(11.75, 25.0, "EMITTED TELEMETRY STREAM", weight='bold', color='#1a202c', ha='center', va='center', fontsize=8.6, zorder=5)
    ax.text(3.8, 20.8, "• RED Metrics: Rate (RPS), Errors, Duration (P95)", fontsize=7.8, color='#2d3748', zorder=5)
    ax.text(3.8, 16.8, "• Resource Metrics: CPU (%), Memory (MB / %)", fontsize=7.8, color='#2d3748', zorder=5)
    ax.text(3.8, 12.8, "• Exporters: Prometheus Python Client @ /metrics", fontsize=7.8, color='#2d3748', zorder=5)
    ax.text(3.8, 9.0, "• Network: Internal Docker Bridge (sentinel_net)", fontsize=7.6, color='#4a5568', style='italic', zorder=5)

    # -------------------------------------------------------------
    # BLOCK 2: TELEMETRY INGESTION LAYER
    # -------------------------------------------------------------
    draw_box(25.0, Y_BOTTOM, 17.5, Y_HEIGHT, C_B2_BG, C_B2_BORDER, border_width=1.5, radius=1.4)
    draw_header_pill(26.0, 84.5, 15.5, 5.6, "2. Telemetry Ingestion", "Prometheus & TimescaleDB Pipeline", C_B2_BORDER)

    # Prometheus Card
    draw_box(26.0, 52.0, 15.5, 30.5, C_B2_CARD, '#cbd5e0', border_width=0.9)
    draw_box(26.5, 78.0, 14.5, 3.8, '#f3e8ff', C_B2_BORDER, border_width=0.8)
    ax.text(33.75, 79.9, "Prometheus Engine (:9090)", weight='bold', color=C_B2_ACCENT, ha='center', va='center', fontsize=9.0, zorder=5)
    ax.text(27.0, 74.0, "• Scrape Interval: Ts = 15s", fontsize=8.0, color='#2d3748', weight='bold', zorder=5)
    ax.text(27.0, 70.0, "• Pull Protocol: HTTP GET /metrics", fontsize=8.0, color='#4a5568', zorder=5)
    ax.text(27.0, 66.0, "• Metric Vector Assembler:", fontsize=8.0, color='#4a5568', zorder=5)
    ax.text(28.0, 62.5, "- http_requests_total (RPS)", fontsize=7.6, color='#5a32a3', zorder=5)
    ax.text(28.0, 59.0, "- http_request_duration_seconds", fontsize=7.6, color='#5a32a3', zorder=5)
    ax.text(28.0, 55.5, "- process_resident_memory_bytes", fontsize=7.6, color='#5a32a3', zorder=5)

    # TimescaleDB Card
    draw_box(26.0, 7.0, 15.5, 38.0, C_B2_CARD, '#cbd5e0', border_width=0.9)
    draw_box(26.5, 40.5, 14.5, 3.8, '#f3e8ff', C_B2_BORDER, border_width=0.8)
    ax.text(33.75, 42.4, "TimescaleDB Engine (:5432)", weight='bold', color=C_B2_ACCENT, ha='center', va='center', fontsize=9.0, zorder=5)
    ax.text(27.0, 36.5, "• Storage: PostgreSQL Hypertable", fontsize=8.0, color='#2d3748', weight='bold', zorder=5)
    ax.text(27.0, 32.5, "• Table: metrics_timeseries", fontsize=8.0, color='#4a5568', zorder=5)
    ax.text(27.0, 28.5, "• Partitioning: 2-Hour Chunking", fontsize=8.0, color='#4a5568', zorder=5)
    ax.text(27.0, 24.5, "• Compression: Native Delta-of-Delta", fontsize=8.0, color='#4a5568', zorder=5)
    ax.text(27.0, 20.0, "• Sliding Buffer:", fontsize=8.0, color='#2d3748', weight='bold', zorder=5)
    ax.text(28.0, 16.5, "  12-sample historical window", fontsize=7.8, color='#4a5568', zorder=5)
    ax.text(28.0, 13.0, "  per microservice entity", fontsize=7.8, color='#4a5568', zorder=5)
    ax.text(27.0, 9.2, "• Rolling Window: W = 180s", fontsize=7.8, color='#5a32a3', weight='bold', zorder=5)

    # Arrow from Prometheus to TimescaleDB
    draw_arrow(33.75, 52.0, 33.75, 45.2, label="Telemetry Sync", color=C_B2_BORDER, lw=1.5, label_pos=0.5, label_offset=(0, 0))

    # -------------------------------------------------------------
    # BLOCK 3: DUAL-STAGE SENTINELOPS PRECURSOR ENGINE (CORE NOVELTY)
    # -------------------------------------------------------------
    draw_box(45.5, Y_BOTTOM, 31.5, Y_HEIGHT, C_B3_BG, C_B3_BORDER, border_width=2.0, radius=1.4)
    draw_header_pill(47.0, 84.5, 28.5, 5.6, "3. SentinelOps Precursor Engine", "Dual-Stage Degradation & TTB Estimator", C_B3_BORDER)

    # Sub-block 3A: Stage 1 Bivariate Load Decoupling Filter
    draw_box(47.0, 48.0, 28.5, 34.5, C_B3_CARD_A, C_B3_BORDER_A, border_width=1.3)
    draw_box(47.5, 78.2, 27.5, 3.6, '#c6f6d5', '#22543d', border_width=0.8)
    ax.text(61.25, 80.0, "STAGE 1: Bivariate Load Decoupling Filter", weight='bold', color='#22543d', ha='center', va='center', fontsize=9.2, zorder=5)
    
    # Mathematical Equation Box for Load Ratio
    draw_box(48.5, 68.0, 25.5, 8.8, '#ffffff', '#38a169', border_width=0.9, radius=0.6)
    ax.text(61.25, 73.8, r"Normalized Bivariate Load Ratio: $\tilde{L}_t = \frac{\mathrm{Latency}_t}{\max(\mathrm{RPS}_t, 0.5)}$",
            color='#1a202c', weight='bold', ha='center', va='center', fontsize=9.0, zorder=5)
    ax.text(61.25, 70.2, r"Suppression Tripwire: $\tilde{L}_t < \tau_{\mathrm{load}} \quad (\tau_{\mathrm{load}} = 0.08)$",
            color='#276749', ha='center', va='center', fontsize=8.4, zorder=5)

    ax.text(48.5, 64.0, "• Flash Crowd Decision Logic:", fontsize=8.2, weight='bold', color='#2d3748', zorder=5)
    ax.text(49.5, 60.5, "  IF  RPS_t > 2.0 * mean(RPS)  AND  L_tilde < 0.08:", fontsize=7.8, color='#2c5282', weight='bold', zorder=5)
    ax.text(49.5, 57.0, "  ==> BENIGN SURGE IDENTIFIED: SUPPRESS ALARM", fontsize=7.8, color='#276749', weight='bold', zorder=5)
    ax.text(49.5, 53.5, "  • Result: Cuts False Alarms by >98% (FPR: 35.2% -> 0.4%)", fontsize=7.8, color='#2d3748', zorder=5)
    ax.text(49.5, 50.0, "  • Retains alerts for true bottlenecking (L_tilde >= 0.08)", fontsize=7.6, color='#718096', style='italic', zorder=5)

    # Sub-block 3B: Stage 2 Temporal Drift & Lead-Time Estimator
    draw_box(47.0, 7.0, 28.5, 37.0, C_B3_CARD_B, C_B3_BORDER_B, border_width=1.3)
    draw_box(47.5, 39.5, 27.5, 3.8, '#feebc8', '#7b341e', border_width=0.8)
    ax.text(61.25, 41.4, "STAGE 2: Temporal Drift & Lead-Time Estimator", weight='bold', color='#7b341e', ha='center', va='center', fontsize=9.2, zorder=5)

    # Mathematical Equation Box for Slope & TTB
    draw_box(48.5, 26.5, 25.5, 11.5, '#ffffff', '#dd6b20', border_width=0.9, radius=0.6)
    ax.text(61.25, 35.5, r"Temporal Drift Velocity ($\beta$ via OLS over $W=180\mathrm{s}$):",
            color='#1a202c', weight='bold', ha='center', va='center', fontsize=8.6, zorder=5)
    ax.text(61.25, 32.2, r"$\beta = \frac{dM}{dt} = \frac{\sum (t_i - \bar{t})(M_i - \bar{M})}{\sum (t_i - \bar{t})^2}$",
            color='#9c4221', ha='center', va='center', fontsize=9.2, zorder=5)
    ax.text(61.25, 28.5, r"Continuous Time-to-Breach: $\mathrm{TTB} = \frac{M_{\mathrm{thresh}} - M_t}{\beta}$",
            color='#c05621', weight='bold', ha='center', va='center', fontsize=8.8, zorder=5)

    ax.text(48.5, 23.0, "• Failure Horizon Classification:", fontsize=8.2, weight='bold', color='#2d3748', zorder=5)
    ax.text(49.5, 19.5, "  - TTB > 300s : Stable Operation (Normal State)", fontsize=7.8, color='#22543d', zorder=5)
    ax.text(49.5, 16.0, "  - 60s < TTB <= 300s : Precursor Warning (Amber)", fontsize=7.8, color='#b7791f', weight='bold', zorder=5)
    ax.text(49.5, 12.5, "  - TTB <= 60s : Imminent Breach Alert (Red)", fontsize=7.8, color='#c53030', weight='bold', zorder=5)
    ax.text(49.5, 9.0, "  • Head-Start Lead Time: 4.8 to 8.2 Minutes before crash", fontsize=7.8, color='#742a2a', weight='bold', zorder=5)

    # Arrow between Stage 1 and Stage 2
    draw_arrow(61.25, 48.0, 61.25, 44.0, label="Surge Decoupled", color=C_B3_BORDER, lw=1.5, label_pos=0.5, label_offset=(0, 0))

    # -------------------------------------------------------------
    # BLOCK 4: OUTPUT & SRE CONTROL PLANE
    # -------------------------------------------------------------
    draw_box(79.5, Y_BOTTOM, 19.0, Y_HEIGHT, C_B4_BG, C_B4_BORDER, border_width=1.5, radius=1.4)
    draw_header_pill(80.5, 84.5, 17.0, 5.6, "4. Output & SRE Plane", "Monitoring & Autonomous Mitigation", C_B4_BORDER)

    # SRE Dashboard Card
    draw_box(80.5, 48.0, 17.0, 34.5, C_B4_CARD, '#cbd5e0', border_width=0.9)
    draw_box(81.0, 78.2, 16.0, 3.6, '#fed7d7', C_B4_ACCENT, border_width=0.8)
    ax.text(89.0, 80.0, "Executive SRE UI (:8000)", weight='bold', color=C_B4_ACCENT, ha='center', va='center', fontsize=9.0, zorder=5)
    ax.text(81.5, 74.0, "• Live TTB Countdown Box", fontsize=8.0, color='#2d3748', weight='bold', zorder=5)
    ax.text(81.5, 70.5, "• Load Shield Indicator (Pill)", fontsize=8.0, color='#2d3748', zorder=5)
    ax.text(81.5, 66.5, "• 3-Way Comparative Matrix:", fontsize=8.0, color='#2d3748', weight='bold', zorder=5)
    ax.text(82.5, 63.0, "  1. Static Prometheus Threshold", fontsize=7.6, color='#718096', zorder=5)
    ax.text(82.5, 59.5, "  2. Scikit-Learn Isolation Forest", fontsize=7.6, color='#718096', zorder=5)
    ax.text(82.5, 56.0, "  3. SentinelOps Precursor (Ours)", fontsize=7.6, color='#2b6cb0', weight='bold', zorder=5)
    ax.text(81.5, 51.5, "• 1-Click Chaos Benchmark Suite", fontsize=8.0, color='#2c5282', weight='bold', zorder=5)

    # Actionable Alert & Remediation Card
    draw_box(80.5, 7.0, 17.0, 38.0, C_B4_CARD, '#cbd5e0', border_width=0.9)
    draw_box(81.0, 40.5, 16.0, 3.8, '#feebc8', '#9c4221', border_width=0.8)
    ax.text(89.0, 42.4, "Proactive Mitigation Dispatch", weight='bold', color='#9c4221', ha='center', va='center', fontsize=9.0, zorder=5)
    ax.text(81.5, 36.5, "• Mitigation Strategies:", fontsize=8.0, color='#2d3748', weight='bold', zorder=5)
    ax.text(82.5, 33.0, "  - Kubernetes Pod Pre-warming", fontsize=7.6, color='#4a5568', zorder=5)
    ax.text(82.5, 29.5, "  - Selective Traffic Draining", fontsize=7.6, color='#4a5568', zorder=5)
    ax.text(82.5, 26.0, "  - Proactive Container Restart", fontsize=7.6, color='#4a5568', zorder=5)
    ax.text(81.5, 21.5, "• Comparison with Baseline:", fontsize=8.0, color='#2d3748', weight='bold', zorder=5)
    ax.text(82.5, 18.0, "  - Static Alert: Fires AFTER crash", fontsize=7.6, color='#e53e3e', weight='bold', zorder=5)
    ax.text(82.5, 14.5, "  - Iso-Forest: 35.2% Alert Storm", fontsize=7.6, color='#e53e3e', zorder=5)
    ax.text(82.5, 10.8, "  - SentinelOps: 5.4m Head-Start", fontsize=7.6, color='#276749', weight='bold', zorder=5)

    # -------------------------------------------------------------
    # INTER-BLOCK CONNECTING PIPELINE ARROWS (FORWARD PATH)
    # -------------------------------------------------------------
    # Block 1 -> Block 2
    draw_arrow(22.0, 68.0, 25.0, 68.0, label="HTTP Scrape\nTs = 15s", color='#2b6cb0', lw=1.8, label_offset=(0, 5.5))
    
    # Block 2 -> Block 3
    draw_arrow(42.5, 68.0, 45.5, 68.0, label="Streaming Buffer\nW = 180s", color='#5a32a3', lw=1.8, label_offset=(0, 5.5))
    
    # Block 3 -> Block 4
    draw_arrow(77.0, 68.0, 79.5, 68.0, label="TTB State &\nShield Telemetry", color='#0d7377', lw=1.8, label_offset=(0, 5.5))

    # -------------------------------------------------------------
    # AUTONOMOUS MITIGATION FEEDBACK LOOP (CLEAN BOTTOM BUS)
    # -------------------------------------------------------------
    # Route via dedicated bottom channel Y=2.5, strictly below all cards and text
    feedback_path = Path([
        (89.0, 5.5),      # Exit bottom of Block 4
        (89.0, 2.4),      # Down to bottom channel
        (11.75, 2.4),     # Left across bottom channel
        (11.75, 5.5)      # Up to bottom of Block 1
    ], [
        Path.MOVETO,
        Path.LINETO,
        Path.LINETO,
        Path.LINETO
    ])
    
    patch = PathPatch(feedback_path, facecolor='none', edgecolor='#c53030',
                      linewidth=1.8, linestyle='--', zorder=6)
    ax.add_patch(patch)

    # Arrowhead entering Block 1
    arrow_head = FancyArrowPatch((11.75, 3.8), (11.75, 5.5),
                                 arrowstyle="->", color='#c53030',
                                 linewidth=1.8, mutation_scale=14, zorder=7)
    ax.add_patch(arrow_head)

    # Feedback Loop Pill Tag in the center of the bottom channel
    fb_tag = FancyBboxPatch((35.0, 1.2), 30.0, 2.4,
                            boxstyle="round,pad=0.2,rounding_size=0.6",
                            facecolor='#fff5f5', edgecolor='#feb2b2', linewidth=0.9, zorder=7)
    ax.add_patch(fb_tag)
    ax.text(50.0, 2.4, "Autonomous Mitigation Feedback Loop (Proactive Container Restart / Traffic Drain)",
            color='#c53030', weight='bold', ha='center', va='center', fontsize=8.0, zorder=8)

    # -------------------------------------------------------------
    # SAVE FIGURE IN MULTIPLE FORMATS
    # -------------------------------------------------------------
    output_dir = 'figures'
    os.makedirs(output_dir, exist_ok=True)

    pdf_path_dir = os.path.join(output_dir, 'figure1_architecture.pdf')
    png_path_dir = os.path.join(output_dir, 'figure1_architecture.png')
    pdf_path_root = 'figure1_architecture.pdf'
    png_path_root = 'figure1_architecture.png'

    plt.tight_layout()

    # Save PDF (Vector format for Overleaf / LaTeX)
    fig.savefig(pdf_path_dir, format='pdf', bbox_inches='tight', pad_inches=0.06)
    fig.savefig(pdf_path_root, format='pdf', bbox_inches='tight', pad_inches=0.06)
    print(f"[OK] Saved Vector PDF: {pdf_path_dir} and {pdf_path_root}")

    # Save PNG (Raster format @ 300 DPI)
    fig.savefig(png_path_dir, format='png', dpi=300, bbox_inches='tight', pad_inches=0.06)
    fig.savefig(png_path_root, format='png', dpi=300, bbox_inches='tight', pad_inches=0.06)
    print(f"[OK] Saved High-Res PNG (300 DPI): {png_path_dir} and {png_path_root}")

    plt.close(fig)

if __name__ == '__main__':
    create_figure1()
