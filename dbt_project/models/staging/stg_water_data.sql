-- ================================================================
-- Staging Model: stg_water_data
-- Cleans and standardises raw water network sensor data
-- Source: raw_water_data table in leakage.db
-- ================================================================

WITH source AS (
    SELECT * FROM main.raw_water_data
),

cleaned AS (
    SELECT
        -- Date
        DATE(date)                          AS reading_date,

        -- Zone identifiers
        zone_id,
        zone_name,
        zone_size,

        -- Cleaned sensor readings
        ROUND(CAST(mnf_ls AS FLOAT), 3)     AS mnf_ls,
        ROUND(CAST(pressure_m AS FLOAT), 2) AS pressure_m,
        CAST(acoustic_alert AS INTEGER)     AS acoustic_alert,

        -- Derived helper columns
        CASE zone_size
            WHEN 'Small'  THEN 1
            WHEN 'Medium' THEN 2
            WHEN 'Large'  THEN 3
        END                                 AS zone_size_rank

    FROM source
)

SELECT * FROM cleaned