"""
Leakage AI Detector - Streamlit Dashboard
Interactive dashboard for water network leakage detection
and AI-powered reporting.
Author: Siddharth Shekhar Singh
"""

import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
import plotly.express as px
import os
from datetime import datetime

# ── Page Configuration ───────────────────────────────────────────
st.set_page_config(
    page_title="Leakage AI Detector",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Paths ────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, "data", "db", "leakage.db")

# ── Custom CSS ───────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1E88E5;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 1rem;
        color: #666;
        margin-top: 0;
    }
    .metric-card {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        border-left: 4px solid #1E88E5;
    }
    .critical-alert {
        background: #ffebee;
        border-left: 4px solid #f44336;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .high-alert {
        background: #fff3e0;
        border-left: 4px solid #ff9800;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .normal-alert {
        background: #e8f5e9;
        border-left: 4px solid #4caf50;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)


# ── Data Loading ─────────────────────────────────────────────────
@st.cache_data
def load_anomaly_data():
    """Load anomaly results from database."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT * FROM anomaly_results ORDER BY zone_id, reading_date",
        conn
    )
    conn.close()
    df["reading_date"] = pd.to_datetime(df["reading_date"])
    return df


@st.cache_data
def load_report():
    """Load the latest AI generated report."""
    docs_dir = os.path.join(BASE_DIR, "docs")
    reports  = [
        f for f in os.listdir(docs_dir)
        if f.startswith("leakage_report") and f.endswith(".txt")
    ]
    if not reports:
        return "No report found. Please run the report generator first."
    latest   = sorted(reports)[-1]
    with open(os.path.join(docs_dir, latest), "r", encoding="utf-8") as f:
        return f.read()


# ── Header ───────────────────────────────────────────────────────
st.markdown(
    '<p class="main-header">💧 Leakage AI Detector</p>',
    unsafe_allow_html=True
)
st.markdown(
    '<p class="sub-header">AI-powered water network leakage detection and automated reporting</p>',
    unsafe_allow_html=True
)
st.divider()

# ── Load Data ────────────────────────────────────────────────────
try:
    df = load_anomaly_data()
except Exception as e:
    st.error(f"❌ Database error: {e}")
    st.stop()

# ── Sidebar ──────────────────────────────────────────────────────
st.sidebar.image(
    "https://img.icons8.com/fluency/96/water.png",
    width=80
)
st.sidebar.title("🔧 Controls")
st.sidebar.divider()

# Zone selector
zones     = sorted(df["zone_id"].unique())
zone_names = {
    row["zone_id"]: f"{row['zone_id']} — {row['zone_name']}"
    for _, row in df.drop_duplicates("zone_id").iterrows()
}
selected_zone = st.sidebar.selectbox(
    "Select DMA Zone:",
    zones,
    format_func=lambda x: zone_names[x]
)

# Severity filter
severity_filter = st.sidebar.multiselect(
    "Filter by Severity:",
    ["Critical", "High", "Medium", "Low", "Normal"],
    default=["Critical", "High", "Medium"]
)

st.sidebar.divider()
st.sidebar.markdown("**Built by:** Siddharth Shekhar Singh")
st.sidebar.markdown("**Model:** Groq Llama 3.3 70B")
st.sidebar.markdown(
    "**GitHub:** [leakage-ai-detector]"
    "(https://github.com/Siddharth-Shekhar-Singh37/Leakage-AI-Detector)"
)

# ── KPI Metrics ──────────────────────────────────────────────────
st.subheader("📊 Network Overview")

col1, col2, col3, col4, col5 = st.columns(5)

total_zones    = df["zone_id"].nunique()
total_readings = len(df)
critical_count = len(df[df["severity"] == "Critical"])
high_count     = len(df[df["severity"] == "High"])
anomaly_count  = len(df[df["confidence_score"] >= 40])

col1.metric("🗺️ DMA Zones",       total_zones)
col2.metric("📋 Total Readings",   f"{total_readings:,}")
col3.metric("🔴 Critical Alerts",  critical_count)
col4.metric("🟠 High Alerts",      high_count)
col5.metric("⚠️ Total Anomalies",  anomaly_count)

st.divider()

# ── Zone Analysis ────────────────────────────────────────────────
zone_df = df[df["zone_id"] == selected_zone].copy()
zone_name = zone_names[selected_zone]

st.subheader(f"🔍 Zone Analysis — {zone_name}")

col_left, col_right = st.columns(2)

# MNF Chart
with col_left:
    st.markdown("**Minimum Night Flow (MNF) over 90 days**")

    anomaly_days = zone_df[zone_df["confidence_score"] >= 40]
    normal_days  = zone_df[zone_df["confidence_score"] < 40]

    fig_mnf = go.Figure()

    # Normal readings
    fig_mnf.add_trace(go.Scatter(
        x=normal_days["reading_date"],
        y=normal_days["mnf_ls"],
        mode="lines",
        name="Normal MNF",
        line=dict(color="#1E88E5", width=2)
    ))

    # Anomaly readings
    fig_mnf.add_trace(go.Scatter(
        x=anomaly_days["reading_date"],
        y=anomaly_days["mnf_ls"],
        mode="markers",
        name="⚠️ Anomaly",
        marker=dict(color="red", size=10, symbol="x")
    ))

    # Rolling average
    fig_mnf.add_trace(go.Scatter(
        x=zone_df["reading_date"],
        y=zone_df["mnf_rolling_avg"],
        mode="lines",
        name="7-day Rolling Avg",
        line=dict(color="orange", width=1.5, dash="dash")
    ))

    fig_mnf.update_layout(
        height=350,
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation="h", y=-0.2),
        xaxis_title="Date",
        yaxis_title="MNF (L/s)"
    )
    st.plotly_chart(fig_mnf, use_container_width=True)

# Pressure Chart
with col_right:
    st.markdown("**Network Pressure over 90 days**")

    pressure_anomalies = zone_df[zone_df["pressure_zscore"] < -2]

    fig_pressure = go.Figure()

    fig_pressure.add_trace(go.Scatter(
        x=zone_df["reading_date"],
        y=zone_df["pressure_m"],
        mode="lines",
        name="Pressure",
        line=dict(color="#43A047", width=2)
    ))

    fig_pressure.add_trace(go.Scatter(
        x=pressure_anomalies["reading_date"],
        y=pressure_anomalies["pressure_m"],
        mode="markers",
        name="⚠️ Pressure Drop",
        marker=dict(color="red", size=10, symbol="x")
    ))

    fig_pressure.update_layout(
        height=350,
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation="h", y=-0.2),
        xaxis_title="Date",
        yaxis_title="Pressure (m)"
    )
    st.plotly_chart(fig_pressure, use_container_width=True)

st.divider()

# ── Confidence Score Chart ───────────────────────────────────────
st.subheader(f"📈 Confidence Score Timeline — {zone_name}")

fig_score = px.bar(
    zone_df,
    x="reading_date",
    y="confidence_score",
    color="severity",
    color_discrete_map={
        "Critical": "#f44336",
        "High":     "#ff9800",
        "Medium":   "#ffeb3b",
        "Low":      "#8bc34a",
        "Normal":   "#e0e0e0"
    },
    labels={
        "reading_date":    "Date",
        "confidence_score": "Confidence Score",
        "severity":         "Severity"
    }
)
fig_score.update_layout(
    height=300,
    margin=dict(l=0, r=0, t=10, b=0)
)
st.plotly_chart(fig_score, use_container_width=True)

st.divider()

# ── All Zones Heatmap ────────────────────────────────────────────
st.subheader("🗺️ Network-Wide Anomaly Heatmap")

pivot = df.pivot_table(
    index="zone_id",
    columns=pd.Grouper(key="reading_date", freq="W"),
    values="confidence_score",
    aggfunc="max"
).fillna(0)

fig_heat = px.imshow(
    pivot,
    color_continuous_scale="RdYlGn_r",
    labels=dict(x="Week", y="Zone", color="Max Score"),
    aspect="auto"
)
fig_heat.update_layout(
    height=350,
    margin=dict(l=0, r=0, t=10, b=0)
)
st.plotly_chart(fig_heat, use_container_width=True)

st.divider()

# ── AI Report Viewer ─────────────────────────────────────────────
st.subheader("🤖 AI Generated Leakage Report")

report = load_report()

with st.expander("📄 View Full AI Report", expanded=False):
    st.text(report)

# Show critical alerts prominently
critical_zones = df[df["severity"] == "Critical"].drop_duplicates("zone_id")
if len(critical_zones) > 0:
    st.markdown("### 🔴 Critical Alerts Requiring Immediate Action")
    for _, row in critical_zones.iterrows():
        st.markdown(f"""
<div class="critical-alert">
<strong>🚨 {row['zone_id']} — {row['zone_name']}</strong><br>
MNF: {row['mnf_ls']} L/s | Pressure: {row['pressure_m']} m |
Confidence: {row['confidence_score']}/100
</div>
""", unsafe_allow_html=True)

st.divider()

# ── Raw Data Table ───────────────────────────────────────────────
st.subheader("📋 Anomaly Data Table")

filtered_df = df[df["severity"].isin(severity_filter)][[
    "reading_date", "zone_id", "zone_name",
    "mnf_ls", "pressure_m", "acoustic_alert",
    "confidence_score", "severity", "risk_level"
]].sort_values("confidence_score", ascending=False)

st.dataframe(
    filtered_df,
    use_container_width=True,
    height=400
)

st.caption(
    f"Showing {len(filtered_df)} records | "
    f"Last updated: {datetime.now().strftime('%d %B %Y %H:%M')}"
)