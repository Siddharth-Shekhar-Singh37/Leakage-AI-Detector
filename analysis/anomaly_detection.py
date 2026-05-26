"""
Anomaly Detection Engine
Detects water leakage anomalies using:
- Z-score statistical method
- Rolling average method
- Combined confidence scoring
Source: mart_leakage_alerts table from dbt transformation
"""

import pandas as pd
import numpy as np
import sqlite3
import os

# ── Paths ────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, "data", "db", "leakage.db")

# ── Thresholds ───────────────────────────────────────────────────
ZSCORE_THRESHOLD   = 2.5
ROLLING_WINDOW     = 7
ROLLING_MULTIPLIER = 1.3


def load_data(conn: sqlite3.Connection) -> pd.DataFrame:
    """Load cleaned data from dbt mart model."""
    query = """
        SELECT
            reading_date,
            zone_id,
            zone_name,
            zone_size,
            mnf_ls,
            pressure_m,
            acoustic_alert,
            avg_mnf,
            avg_pressure,
            mnf_deviation,
            pressure_deviation,
            risk_level,
            is_confirmed_leakage
        FROM mart_leakage_alerts
        ORDER BY zone_id, reading_date
    """
    df = pd.read_sql_query(query, conn, parse_dates=["reading_date"])
    print(f"✅ Loaded {len(df):,} rows from mart_leakage_alerts")
    return df


def calculate_zscore(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate Z-score for MNF and pressure per zone.
    Z-score = (value - mean) / standard deviation
    """
    df = df.copy()
    df["mnf_zscore"]      = 0.0
    df["pressure_zscore"] = 0.0

    for zone in df["zone_id"].unique():
        mask    = df["zone_id"] == zone
        zone_df = df.loc[mask]

        mean_mnf = zone_df["mnf_ls"].mean()
        std_mnf  = zone_df["mnf_ls"].std()
        df.loc[mask, "mnf_zscore"] = (
            (zone_df["mnf_ls"] - mean_mnf) / std_mnf
            if std_mnf > 0 else 0.0
        )

        mean_p = zone_df["pressure_m"].mean()
        std_p  = zone_df["pressure_m"].std()
        df.loc[mask, "pressure_zscore"] = (
            (zone_df["pressure_m"] - mean_p) / std_p
            if std_p > 0 else 0.0
        )

    print("✅ Z-scores calculated for all zones")
    return df


def calculate_rolling_average(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate 7-day rolling average MNF per zone.
    Flags when current value exceeds rolling average by 30%.
    """
    df = df.copy()
    df["mnf_rolling_avg"] = 0.0
    df["rolling_anomaly"] = 0

    for zone in df["zone_id"].unique():
        mask    = df["zone_id"] == zone
        zone_df = df.loc[mask].sort_values("reading_date")

        rolling = (
            zone_df["mnf_ls"]
            .rolling(window=ROLLING_WINDOW, min_periods=3)
            .mean()
            .round(3)
        )
        df.loc[zone_df.index, "mnf_rolling_avg"] = rolling
        df.loc[zone_df.index, "rolling_anomaly"] = (
            zone_df["mnf_ls"] > rolling * ROLLING_MULTIPLIER
        ).astype(int)

    print("✅ Rolling averages calculated for all zones")
    return df


def calculate_confidence_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Combine all signals into a single confidence score (0-100).
    Higher score = higher confidence it is a real leak.
    """
    df = df.copy()

    # Component 1: MNF Z-score contribution (0-40 points)
    mnf_score = (
        df["mnf_zscore"].clip(0, 4) / 4 * 40
    ).round(1)

    # Component 2: Pressure drop contribution (0-30 points)
    pressure_score = (
        (-df["pressure_zscore"]).clip(0, 3) / 3 * 30
    ).round(1)

    # Component 3: Acoustic alert (0 or 20 points)
    acoustic_score = df["acoustic_alert"] * 20

    # Component 4: Rolling anomaly (0 or 10 points)
    rolling_score = df["rolling_anomaly"] * 10

    # Combined score
    df["confidence_score"] = (
        mnf_score + pressure_score + acoustic_score + rolling_score
    ).clip(0, 100).round(1)

    # Severity label
    df["severity"] = pd.cut(
        df["confidence_score"],
        bins=[-1, 20, 40, 60, 80, 100],
        labels=["Normal", "Low", "Medium", "High", "Critical"]
    )

    print("✅ Confidence scores calculated for all readings")
    return df


def get_anomaly_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Extract only the anomalous readings."""
    anomalies = df[df["confidence_score"] >= 40].copy()
    anomalies = anomalies.sort_values("confidence_score", ascending=False)
    return anomalies


def display_results(df: pd.DataFrame, anomalies: pd.DataFrame) -> None:
    """Print a clean summary of detection results."""
    print("\n" + "="*65)
    print("📊 ANOMALY DETECTION RESULTS SUMMARY")
    print("="*65)

    print(f"\n🔢 Total readings analysed: {len(df):,}")
    print(f"🚨 Anomalies detected: {len(anomalies)}")
    print(f"✅ Normal readings: {len(df) - len(anomalies):,}")

    print(f"\n{'─'*65}")
    print("🚨 TOP ANOMALIES BY CONFIDENCE SCORE:")
    print(f"{'─'*65}")

    cols = [
        "reading_date", "zone_id", "zone_name",
        "mnf_ls", "pressure_m", "acoustic_alert",
        "confidence_score", "severity"
    ]

    top = anomalies[cols].head(10)
    print(f"\n  {'Date':<12} {'Zone':<8} {'Name':<12} "
          f"{'MNF':>6} {'Press':>7} {'Acou':>5} "
          f"{'Score':>6} {'Severity':<10}")
    print(f"  {'─'*75}")

    for _, row in top.iterrows():
        print(
            f"  {str(row['reading_date'])[:10]:<12} "
            f"{row['zone_id']:<8} "
            f"{row['zone_name']:<12} "
            f"{row['mnf_ls']:>6} "
            f"{row['pressure_m']:>7} "
            f"{int(row['acoustic_alert']):>5} "
            f"{row['confidence_score']:>6} "
            f"{str(row['severity']):<10}"
        )

    print(f"\n{'─'*65}")
    print("📍 ANOMALIES BY ZONE:")
    print(f"{'─'*65}")

    zone_summary = (
        anomalies.groupby(["zone_id", "zone_name"])
        .agg(
            anomaly_days=("confidence_score", "count"),
            max_score=("confidence_score", "max"),
            max_mnf=("mnf_ls", "max")
        )
        .reset_index()
        .sort_values("max_score", ascending=False)
    )

    for _, row in zone_summary.iterrows():
        print(
            f"  {row['zone_id']} {row['zone_name']:<12} → "
            f"{int(row['anomaly_days'])} anomaly days | "
            f"Max score: {row['max_score']} | "
            f"Max MNF: {row['max_mnf']}"
        )


def save_results(df: pd.DataFrame) -> None:
    """Save full results with anomaly scores back to SQLite."""
    conn = sqlite3.connect(DB_PATH)
    df_save = df[[
        "reading_date", "zone_id", "zone_name", "zone_size",
        "mnf_ls", "pressure_m", "acoustic_alert",
        "mnf_zscore", "pressure_zscore",
        "mnf_rolling_avg", "rolling_anomaly",
        "confidence_score", "severity", "risk_level"
    ]].copy()
    df_save["severity"] = df_save["severity"].astype(str)
    df_save.to_sql(
        "anomaly_results",
        conn,
        if_exists="replace",
        index=False
    )
    conn.close()
    print(f"\n✅ Results saved to anomaly_results table in database")


def main():
    print("🌊 Running Leakage Anomaly Detection Engine...\n")
    conn = sqlite3.connect(DB_PATH)
    df   = load_data(conn)
    conn.close()

    df = calculate_zscore(df)
    df = calculate_rolling_average(df)
    df = calculate_confidence_score(df)

    anomalies = get_anomaly_summary(df)
    display_results(df, anomalies)
    save_results(df)

    print("\n🎉 Anomaly detection complete!")
    return df, anomalies


if __name__ == "__main__":
    df, anomalies = main()