-- Analysis queries. Run after 01_schema.sql and 02_data.sql.


-- Q1. Data check: category weights must sum to 100.
SELECT ROUND(SUM(weight_pct), 1) AS total_weight_pct
FROM cpi_divisions
WHERE code <> '00';


-- Q2. Annual and quarterly change per category, with approximate contribution to headline inflation
--     (weight x category index change / general index a year earlier), ranked by contribution.
WITH gen AS (
    SELECT cpi_q1_2025 AS gen_prev FROM cpi_divisions WHERE code = '00'
)
SELECT
    d.name_ar,
    d.weight_pct,
    ROUND(100.0 * (d.cpi_q1_2026 / d.cpi_q1_2025 - 1), 1)                       AS yoy_pct,
    ROUND(100.0 * (d.cpi_q1_2026 / d.cpi_q4_2025 - 1), 1)                       AS qoq_pct,
    ROUND(d.weight_pct * (d.cpi_q1_2026 - d.cpi_q1_2025) / g.gen_prev, 2)       AS contribution_pp,
    RANK() OVER (ORDER BY d.weight_pct * (d.cpi_q1_2026 - d.cpi_q1_2025) DESC)  AS contribution_rank
FROM cpi_divisions d
CROSS JOIN gen g
WHERE d.code <> '00'
ORDER BY contribution_rank;


-- Q3. Categories whose inflation is above the headline rate, and their combined weight in the basket.
WITH g AS (
    SELECT cpi_q1_2026 / cpi_q1_2025 - 1 AS headline FROM cpi_divisions WHERE code = '00'
),
above AS (
    SELECT d.name_ar, d.weight_pct, d.cpi_q1_2026 / d.cpi_q1_2025 - 1 AS yoy
    FROM cpi_divisions d, g
    WHERE d.code <> '00' AND d.cpi_q1_2026 / d.cpi_q1_2025 - 1 > g.headline
)
SELECT
    name_ar,
    ROUND(100.0 * yoy, 1)                         AS yoy_pct,
    weight_pct,
    ROUND(SUM(weight_pct) OVER (), 1)             AS combined_weight_pct
FROM above
ORDER BY yoy DESC;


-- Q4. Share of headline inflation explained by the top 3 contributors.
WITH c AS (
    SELECT name_ar, weight_pct * (cpi_q1_2026 - cpi_q1_2025) AS contrib
    FROM cpi_divisions WHERE code <> '00'
),
r AS (
    SELECT name_ar, contrib, ROW_NUMBER() OVER (ORDER BY contrib DESC) AS rn FROM c
)
SELECT
    ROUND(100.0 * SUM(CASE WHEN rn <= 3 THEN contrib END) / SUM(contrib), 1) AS top3_share_pct
FROM r;


-- Q5. Monthly trend: published annual rate, its change from the previous month,
--     and the 3-month moving average of monthly changes.
SELECT
    month,
    mom_change_pct,
    yoy_change_pct,
    ROUND(yoy_change_pct - LAG(yoy_change_pct) OVER (ORDER BY month), 1)               AS yoy_change_vs_prev_month,
    ROUND(AVG(mom_change_pct) OVER (ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) AS mom_3m_avg
FROM cpi_headline_monthly
ORDER BY month;


-- Q6. Peak and lowest annual inflation in the period.
SELECT 'الأعلى' AS which, month, yoy_change_pct
FROM cpi_headline_monthly
WHERE yoy_change_pct = (SELECT MAX(yoy_change_pct) FROM cpi_headline_monthly)
UNION ALL
SELECT 'الأدنى', month, yoy_change_pct
FROM cpi_headline_monthly
WHERE yoy_change_pct = (SELECT MIN(yoy_change_pct) FROM cpi_headline_monthly)
ORDER BY which, month;
