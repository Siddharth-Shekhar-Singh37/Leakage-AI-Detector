"""
AI Report Generator — LangChain Version
Uses LangChain + Groq (Llama 3.3 70B) to generate plain-English
leakage reports from anomaly detection results.

LangChain Components Used:
- ChatPromptTemplate: Separates prompt logic from business logic
- ChatGroq: LangChain wrapper around Groq API
- StrOutputParser: Parses LLM output into clean string
- Chain (|): Connects components into a pipeline
"""

import os
import sqlite3
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime

# ── LangChain Imports ─────────────────────────────────────────────
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# ── Setup ─────────────────────────────────────────────────────────
load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, "data", "db", "leakage.db")

# ── LangChain Components ──────────────────────────────────────────

# 1. Language Model — Groq via LangChain wrapper
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.3,
    max_tokens=400
)

# 2. Prompt Template — separates prompt from code
prompt_template = ChatPromptTemplate.from_template("""
You are a senior water network analyst at a UK water utility company.
Analyse the following leakage detection data and write a professional
operational report for the field team.

ZONE INFORMATION:
- Zone ID: {zone_id}
- Zone Name: {zone_name}
- Zone Size: {zone_size}
- Date: {reading_date}

SENSOR READINGS:
- Minimum Night Flow (MNF): {mnf_ls} L/s
- Network Pressure: {pressure_m} metres
- Acoustic Logger Alert: {acoustic_alert}

STATISTICAL ANALYSIS:
- MNF Z-Score: {mnf_zscore} (above 2.5 = anomalous)
- Pressure Z-Score: {pressure_zscore}
- Rolling Average MNF: {mnf_rolling_avg} L/s
- Confidence Score: {confidence_score}/100
- Severity: {severity}
- Risk Level: {risk_level}

Write a concise professional report (150-200 words) that includes:
1. A clear alert headline
2. What the data shows in plain English
3. What type of leakage event this likely is
4. Recommended immediate action for the field team
5. Priority level

Use professional water industry language but keep it clear and actionable.
""")

# 3. Output Parser — extracts clean text from LLM response
output_parser = StrOutputParser()

# 4. Chain — connects prompt | llm | parser into one pipeline
report_chain = prompt_template | llm | output_parser


def load_anomalies() -> pd.DataFrame:
    """Load anomaly results from database."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        """
        SELECT *
        FROM anomaly_results
        WHERE confidence_score >= 40
        ORDER BY confidence_score DESC
        """,
        conn
    )
    conn.close()
    print(f"✅ Loaded {len(df)} anomalies for reporting")
    return df


def generate_zone_report(zone_data: pd.Series) -> str:
    """
    Generate a plain-English report for a single anomaly
    using LangChain chain: prompt_template | llm | output_parser
    """
    # Invoke the LangChain chain with zone data
    report = report_chain.invoke({
        "zone_id":          zone_data["zone_id"],
        "zone_name":        zone_data["zone_name"],
        "zone_size":        zone_data["zone_size"],
        "reading_date":     str(zone_data["reading_date"])[:10],
        "mnf_ls":           zone_data["mnf_ls"],
        "pressure_m":       zone_data["pressure_m"],
        "acoustic_alert":   "YES" if zone_data["acoustic_alert"] == 1 else "NO",
        "mnf_zscore":       round(zone_data["mnf_zscore"], 2),
        "pressure_zscore":  round(zone_data["pressure_zscore"], 2),
        "mnf_rolling_avg":  zone_data["mnf_rolling_avg"],
        "confidence_score": zone_data["confidence_score"],
        "severity":         zone_data["severity"],
        "risk_level":       zone_data["risk_level"],
    })
    return report


def generate_full_report(df: pd.DataFrame) -> str:
    """Generate a complete report for all anomalies."""
    print("\n🤖 Generating AI reports using LangChain + Groq...\n")
    print("   Chain: ChatPromptTemplate | ChatGroq | StrOutputParser\n")

    report_date = datetime.now().strftime("%d %B %Y")
    full_report = f"""
{'='*65}
WATER NETWORK LEAKAGE DETECTION REPORT
Generated: {report_date}
System: AI-Powered Leakage Detector v1.0
AI Engine: LangChain + Groq Llama 3.3 70B
{'='*65}

EXECUTIVE SUMMARY
─────────────────
Total anomalies detected: {len(df)}
Critical events: {len(df[df['severity'] == 'Critical'])}
High severity: {len(df[df['severity'] == 'High'])}
Medium severity: {len(df[df['severity'] == 'Medium'])}

{'='*65}
DETAILED ZONE REPORTS
{'='*65}
"""

    for i, (_, row) in enumerate(df.iterrows()):
        print(f"   Generating report {i+1}/{len(df)}: "
              f"{row['zone_id']} {row['zone_name']}...")
        zone_report = generate_zone_report(row)
        full_report += f"""
{'─'*65}
ZONE: {row['zone_id']} — {row['zone_name']} | Score: {row['confidence_score']}/100
{'─'*65}
{zone_report}
"""

    full_report += f"""
{'='*65}
END OF REPORT
Generated by Leakage AI Detector
AI Engine: LangChain + Groq Llama 3.3 70B
Author: Siddharth Shekhar Singh
{'='*65}
"""
    return full_report


def save_report(report: str) -> str:
    """Save the report to the docs folder."""
    report_date = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(
        BASE_DIR, "docs", f"leakage_report_{report_date}.txt"
    )
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n✅ Report saved to: {report_path}")
    return report_path


def main():
    print("🌊 AI Leakage Report Generator — LangChain Edition\n")
    print("="*65)
    print("🔗 LangChain Chain Architecture:")
    print("   ChatPromptTemplate → ChatGroq → StrOutputParser")
    print("="*65 + "\n")

    df       = load_anomalies()
    report   = generate_full_report(df)
    filepath = save_report(report)

    print("\n" + "="*65)
    print("📄 REPORT PREVIEW (first 1500 chars):")
    print("="*65)
    print(report[:1500])
    print("\n🎉 LangChain report generation complete!")
    print(f"   Full report saved to: {filepath}")


if __name__ == "__main__":
    main()