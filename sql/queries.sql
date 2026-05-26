-- ================================================================
-- Water Network Leakage Detection SQL Queries
-- Database: leakage.db | Table: raw_water_data
-- Author: Siddharth Shekhar Singh
-- ================================================================


-- ── Query 1: Daily MNF Summary per Zone ─────────────────────────
-- Shows average, min and max MNF for each zone across all 90 days
-- Used to understand baseline flow behaviour per zone

SELECT
    zone_id,
    zone_name,
    zone_size,
    ROUND(AVG(mnf_ls), 3)  AS avg_mnf,
    ROUND(MIN(mnf_ls), 3)  AS min_mnf,
    ROUND(MAX(mnf_ls), 3)  AS max_mnf
FROM raw_water_data
GROUP BY zone_id, zone_name, zone_size
ORDER BY avg_mnf DESC;


-- ── Query 2: Detect High MNF Days (Potential Leakage) ───────────
-- Flags any day where MNF is more than 50% above the zone average
-- This is a simple threshold-based anomaly detection in pure SQL

SELECT
    date,
    zone_id,
    zone_name,
    mnf_ls,
    pressure_m,
    acoustic_alert,
    CASE
        WHEN mnf_ls > (
            SELECT AVG(mnf_ls) * 1.5
            FROM raw_water_data r2
            WHERE r2.zone_id = r1.zone_id
        ) THEN 'HIGH LEAKAGE RISK'
        WHEN mnf_ls > (
            SELECT AVG(mnf_ls) * 1.2
            FROM raw_water_data r2
            WHERE r2.zone_id = r1.zone_id
        ) THEN 'ELEVATED RISK'
        ELSE 'NORMAL'
    END AS risk_level
FROM raw_water_data r1
WHERE risk_level != 'NORMAL'
ORDER BY mnf_ls DESC;


-- ── Query 3: Pressure Drop Detection ────────────────────────────
-- Finds days where pressure dropped significantly below zone average
-- Sudden pressure drops indicate potential pipe bursts

SELECT
    date,
    zone_id,
    zone_name,
    pressure_m,
    mnf_ls,
    acoustic_alert,
    ROUND(pressure_m - AVG(pressure_m) OVER (
        PARTITION BY zone_id
    ), 2) AS pressure_deviation
FROM raw_water_data
WHERE pressure_m < (
    SELECT AVG(pressure_m) - 10
    FROM raw_water_data r2
    WHERE r2.zone_id = raw_water_data.zone_id
)
ORDER BY pressure_deviation ASC;


-- ── Query 4: Combined Alert — High Confidence Leakage ───────────
-- The most powerful query — finds days where ALL THREE signals fire
-- MNF spike + pressure drop + acoustic alert = almost certain burst

SELECT
    date,
    zone_id,
    zone_name,
    mnf_ls,
    pressure_m,
    acoustic_alert,
    'CONFIRMED LEAKAGE EVENT' AS alert_status
FROM raw_water_data
WHERE
    acoustic_alert = 1
    AND mnf_ls > (
        SELECT AVG(mnf_ls) * 1.3
        FROM raw_water_data r2
        WHERE r2.zone_id = raw_water_data.zone_id
    )
    AND pressure_m < (
        SELECT AVG(pressure_m) - 5
        FROM raw_water_data r2
        WHERE r2.zone_id = raw_water_data.zone_id
    )
ORDER BY date;