"""
Synthetic Water Network Data Generator
Generates realistic MNF, Pressure, and Acoustic data for 10 DMA zones
over 90 days with injected anomalies for leakage detection testing.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

# ── Reproducibility ──────────────────────────────────────────────
np.random.seed(42)

# ── Configuration ────────────────────────────────────────────────
START_DATE = datetime(2025, 1, 1)
NUM_DAYS   = 90
NUM_ZONES  = 10

ZONES = [
    {"id": "DMA_01", "name": "Northfield",  "size": "Small",  "base_mnf": 2.5},
    {"id": "DMA_02", "name": "Riverside",   "size": "Medium", "base_mnf": 4.5},
    {"id": "DMA_03", "name": "Castleview",  "size": "Large",  "base_mnf": 7.0},
    {"id": "DMA_04", "name": "Moorside",    "size": "Small",  "base_mnf": 3.0},
    {"id": "DMA_05", "name": "Greenpark",   "size": "Medium", "base_mnf": 5.0},
    {"id": "DMA_06", "name": "Hillcrest",   "size": "Large",  "base_mnf": 6.5},
    {"id": "DMA_07", "name": "Lakeside",    "size": "Small",  "base_mnf": 2.8},
    {"id": "DMA_08", "name": "Westgate",    "size": "Medium", "base_mnf": 4.8},
    {"id": "DMA_09", "name": "Eastbrook",   "size": "Large",  "base_mnf": 7.2},
    {"id": "DMA_10", "name": "Southfield",  "size": "Small",  "base_mnf": 3.2},
]

# ── Anomalies to inject ──────────────────────────────────────────
ANOMALIES = [
    {"zone": "DMA_01", "type": "pipe_burst",          "start_day": 15, "duration": 1},
    {"zone": "DMA_03", "type": "background_leakage",  "start_day": 20, "duration": 14},
    {"zone": "DMA_05", "type": "pipe_burst",          "start_day": 40, "duration": 1},
    {"zone": "DMA_07", "type": "background_leakage",  "start_day": 55, "duration": 10},
    {"zone": "DMA_09", "type": "pressure_transient",  "start_day": 70, "duration": 3},
]


def generate_dates(start: datetime, num_days: int) -> list:
    return [start + timedelta(days=i) for i in range(num_days)]


def generate_mnf(base: float, num_days: int) -> np.ndarray:
    """Normal daily MNF with sensor noise."""
    noise = np.random.normal(0, 0.15, num_days)
    trend = np.linspace(0, 0.3, num_days)          # slight seasonal rise
    return np.round(base + trend + noise, 3)


def generate_pressure(num_days: int) -> np.ndarray:
    """Normal pressure around 55 m with daily variation."""
    base    = np.random.uniform(50, 60)
    noise   = np.random.normal(0, 1.2, num_days)
    return np.round(base + noise, 2)


def generate_acoustic(num_days: int) -> np.ndarray:
    """Acoustic loggers — mostly silent (0), rare random alert (1)."""
    alerts = np.random.choice([0, 1], size=num_days, p=[0.97, 0.03])
    return alerts


def inject_anomalies(
    mnf: np.ndarray,
    pressure: np.ndarray,
    acoustic: np.ndarray,
    zone_id: str,
) -> tuple:
    """Inject realistic anomaly signatures into the data arrays."""
    for anomaly in ANOMALIES:
        if anomaly["zone"] != zone_id:
            continue

        s = anomaly["start_day"]
        d = anomaly["duration"]
        e = min(s + d, len(mnf))

        if anomaly["type"] == "pipe_burst":
            mnf[s:e]      += np.random.uniform(3.0, 6.0, e - s)   # big spike
            pressure[s:e] -= np.random.uniform(8.0, 15.0, e - s)  # pressure drop
            acoustic[s:e]  = 1                                      # logger fires

        elif anomaly["type"] == "background_leakage":
            leak = np.linspace(0.5, 2.5, e - s)                    # gradual rise
            mnf[s:e]      += leak
            pressure[s:e] -= np.linspace(0.5, 3.0, e - s)         # slow drop

        elif anomaly["type"] == "pressure_transient":
            pressure[s:e] -= np.random.uniform(5.0, 10.0, e - s)  # pressure dip
            acoustic[s:e]  = 1                                      # logger fires

    return mnf, pressure, acoustic


def build_dataframe() -> pd.DataFrame:
    dates  = generate_dates(START_DATE, NUM_DAYS)
    frames = []

    for zone in ZONES:
        mnf      = generate_mnf(zone["base_mnf"], NUM_DAYS)
        pressure = generate_pressure(NUM_DAYS)
        acoustic = generate_acoustic(NUM_DAYS)

        mnf, pressure, acoustic = inject_anomalies(
            mnf, pressure, acoustic, zone["id"]
        )

        df = pd.DataFrame({
            "date":         dates,
            "zone_id":      zone["id"],
            "zone_name":    zone["name"],
            "zone_size":    zone["size"],
            "mnf_ls":       mnf,
            "pressure_m":   pressure,
            "acoustic_alert": acoustic,
        })
        frames.append(df)

    return pd.concat(frames, ignore_index=True)


def save_data(df: pd.DataFrame) -> None:
    out_dir = os.path.join(os.path.dirname(__file__))
    out_path = os.path.join(out_dir, "water_network_data.csv")
    df.to_csv(out_path, index=False)
    print(f"✅ Data saved to: {out_path}")
    print(f"   Rows: {len(df):,}  |  Zones: {df['zone_id'].nunique()}  |  Days: {NUM_DAYS}")
    print(f"\n📊 Sample (first 5 rows):")
    print(df.head())
    print(f"\n🚨 Anomaly summary:")
    for a in ANOMALIES:
        print(f"   {a['zone']} → {a['type']} starting day {a['start_day']}")


if __name__ == "__main__":
    print("🌊 Generating synthetic water network data...\n")
    df = build_dataframe()
    save_data(df)