-- Analysis queries. Run after 01_schema.sql and 02_data.sql.
-- Each query answers one business question; results are summarised in ../README.md.


-- Q1. Headline numbers for the latest quarter.
SELECT
    year,
    quarter,
    SUM(total_employed)                                   AS total_employed,
    SUM(saudi_employed)                                   AS saudi_employed,
    SUM(non_saudi_employed)                               AS non_saudi_employed,
    ROUND(100.0 * SUM(saudi_employed) / SUM(total_employed), 1) AS saudization_pct
FROM v_employment
WHERE period = (SELECT MAX(period) FROM v_employment)
GROUP BY year, quarter;


-- Q2. Saudization by activity in the latest quarter, highest first.
SELECT
    name_ar,
    total_employed,
    saudi_employed,
    ROUND(100.0 * saudization_rate, 1)                    AS saudization_pct,
    ROUND(100.0 * total_employed / SUM(total_employed) OVER (), 1) AS share_of_employment_pct
FROM v_employment
WHERE period = (SELECT MAX(period) FROM v_employment)
ORDER BY saudization_rate DESC;


-- Q3. Top 5 and bottom 5 activities by Saudization
--     (activities with at least 50,000 workers, excluding "not specified").
WITH latest AS (
    SELECT *
    FROM v_employment
    WHERE period = (SELECT MAX(period) FROM v_employment)
      AND total_employed >= 50000
      AND activity_code <> 'NotSpecified'
),
ranked AS (
    SELECT
        name_ar,
        saudization_rate,
        saudi_employed,
        total_employed,
        RANK() OVER (ORDER BY saudization_rate DESC) AS rank_high,
        RANK() OVER (ORDER BY saudization_rate ASC)  AS rank_low
    FROM latest
)
SELECT
    CASE WHEN rank_high <= 5 THEN 'الأعلى' ELSE 'الأقل' END AS grp,
    name_ar,
    ROUND(100.0 * saudization_rate, 1) AS saudization_pct,
    saudi_employed,
    total_employed
FROM ranked
WHERE rank_high <= 5 OR rank_low <= 5
ORDER BY saudization_rate DESC;


-- Q4. Quarterly trend: total, Saudi, Saudization, and quarter-on-quarter growth in Saudi workers.
--     Note: Q3 2022 is missing in the source, so Q4 2022 growth compares with Q2 2022.
WITH by_quarter AS (
    SELECT
        period, year, quarter,
        SUM(total_employed)  AS total_employed,
        SUM(saudi_employed)  AS saudi_employed
    FROM v_employment
    GROUP BY period, year, quarter
)
SELECT
    year,
    quarter,
    total_employed,
    saudi_employed,
    ROUND(100.0 * saudi_employed / total_employed, 1) AS saudization_pct,
    ROUND(100.0 * (1.0 * saudi_employed / LAG(saudi_employed) OVER (ORDER BY period) - 1), 1)
                                                       AS saudi_growth_qoq_pct
FROM by_quarter
ORDER BY period;


-- Q5. Change per activity from the first to the latest quarter:
--     growth in Saudi workers and change in Saudization (percentage points).
WITH bounds AS (
    SELECT MIN(period) AS first_p, MAX(period) AS last_p FROM v_employment
),
first_q AS (
    SELECT activity_id, saudi_employed, saudization_rate
    FROM v_employment, bounds WHERE period = first_p
),
last_q AS (
    SELECT activity_id, name_ar, saudi_employed, saudization_rate
    FROM v_employment, bounds WHERE period = last_p
)
SELECT
    l.name_ar,
    f.saudi_employed                                              AS saudi_first,
    l.saudi_employed                                              AS saudi_latest,
    ROUND(100.0 * (1.0 * l.saudi_employed / NULLIF(f.saudi_employed, 0) - 1), 1) AS saudi_growth_pct,
    ROUND(100.0 * (l.saudization_rate - f.saudization_rate), 1)   AS saudization_change_pp
FROM last_q l
JOIN first_q f ON f.activity_id = l.activity_id
ORDER BY saudization_change_pp DESC;


-- Q6. Activities where the number of Saudis grew but the Saudization rate fell
--     (non-Saudi hiring outpaced Saudi hiring).
WITH bounds AS (
    SELECT MIN(period) AS first_p, MAX(period) AS last_p FROM v_employment
),
chg AS (
    SELECT
        l.name_ar,
        l.saudi_employed - f.saudi_employed                       AS saudi_added,
        l.non_saudi_employed - f.non_saudi_employed               AS non_saudi_added,
        l.saudization_rate - f.saudization_rate                   AS rate_change
    FROM v_employment l
    JOIN v_employment f ON f.activity_id = l.activity_id
    CROSS JOIN bounds b
    WHERE l.period = b.last_p AND f.period = b.first_p
)
SELECT
    name_ar,
    saudi_added,
    non_saudi_added,
    ROUND(100.0 * rate_change, 1) AS saudization_change_pp
FROM chg
WHERE saudi_added > 0 AND rate_change < 0
ORDER BY non_saudi_added DESC;
