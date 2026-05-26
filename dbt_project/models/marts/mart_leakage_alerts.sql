-- ================================================================
-- Mart Model: mart_leakage_alerts
-- Final analysis-ready table with anomaly flags and risk levels
-- Built on top of stg_water_data staging model
-- ================================================================

WITH staged AS (
    SELECT * FROM {{ ref('stg_water_data') }}
),

zone_baselines AS (
    -- Calculate baseline statistics per zone
    SELECT
        zone_id,
        ROUND(AVG(mnf_ls), 3)       AS avg_mnf,
        ROUND(AVG(pressure_m), 2)   AS avg_pressure,
        ROUND(MAX(mnf_ls), 3)       AS max_mnf,
        ROUND(MIN(pressure_m), 2)   AS min_pressure
    FROM staged
    GROUP BY zone_id
),

alerts AS (
    SELECT
        s.reading_date,
        s.zone_id,
        s.zone_name,
        s.zone_size,
        s.mnf_ls,
        s.pressure_m,
        s.acoustic_alert,
        b.avg_mnf,
        b.avg_pressure,

        -- MNF deviation from baseline
        ROUND(s.mnf_ls - b.avg_mnf, 3)         AS mnf_deviation,

        -- Pressure deviation from baseline
        ROUND(s.pressure_m - b.avg_pressure, 2) AS pressure_deviation,

        -- Risk classification
        CASE
            WHEN s.acoustic_alert = 1
                AND s.mnf_ls > b.avg_mnf * 1.3
                AND s.pressure_m < b.avg_pressure - 5
            THEN 'CONFIRMED LEAKAGE'

            WHEN s.mnf_ls > b.avg_mnf * 1.5
            THEN 'HIGH RISK'

            WHEN s.mnf_ls > b.avg_mnf * 1.2
            THEN 'ELEVATED RISK'

            WHEN s.pressure_m < b.avg_pressure - 8
            THEN 'PRESSURE ALERT'

            ELSE 'NORMAL'
        END AS risk_level,

        -- Single flag for easy filtering
        CASE
            WHEN s.acoustic_alert = 1
                AND s.mnf_ls > b.avg_mnf * 1.3
                AND s.pressure_m < b.avg_pressure - 5
            THEN 1
            ELSE 0
        END AS is_confirmed_leakage

    FROM staged s
    LEFT JOIN zone_baselines b
        ON s.zone_id = b.zone_id
)

SELECT * FROM alerts
ORDER BY reading_date, zone_id