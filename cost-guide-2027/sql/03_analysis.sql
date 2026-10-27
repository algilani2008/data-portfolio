-- cost-guide-2027: analysis queries (SQLite 3.25+ for window functions)

-- 1. Monthly electricity bill (before VAT) for 1,000 / 2,000 / 7,000 kWh under each schedule.
--    Progressive tiers: each rate applies only to the kWh inside its band.
WITH q(kwh) AS (VALUES (1000), (2000), (7000))
SELECT t.schedule, q.kwh,
       ROUND(SUM(MAX(0, MIN(q.kwh, COALESCE(t.tier_to_kwh, 1e9)) - t.tier_from_kwh) * t.rate_halala / 100.0), 2)
         AS energy_sar
FROM electricity_tariffs t CROSS JOIN q
GROUP BY t.schedule, q.kwh
ORDER BY q.kwh, t.schedule;

-- 2. Change in the first-tier rate between consecutive schedules (LAG).
WITH t AS (
  SELECT schedule, rate_halala,
         CASE schedule WHEN 'pre2016' THEN 2001 ELSE CAST(schedule AS INTEGER) END AS start_year
  FROM electricity_tariffs WHERE tier_from_kwh = 0)
SELECT schedule, rate_halala,
       LAG(rate_halala) OVER (ORDER BY start_year) AS previous_rate,
       ROUND(100.0 * (rate_halala - LAG(rate_halala) OVER (ORDER BY start_year))
             / LAG(rate_halala) OVER (ORDER BY start_year), 1) AS change_pct
FROM t
ORDER BY start_year;

-- 3. Fixed charge: old meter fee vs new 2027 fixed charge by breaker band.
SELECT n.breaker_from_a, o.fee_sar AS fee_2018, n.fee_sar AS fee_2027,
       n.fee_sar - o.fee_sar AS increase_sar
FROM electricity_fees n
JOIN electricity_fees o ON o.schedule = '2018' AND o.breaker_from_a = n.breaker_from_a
WHERE n.schedule = '2027';

-- 4. Monthly water + sewage bill at 15 / 30 / 45 / 60 m3, 2016 vs 2027 (before fixed fees and VAT).
WITH q(m3) AS (VALUES (15), (30), (45), (60))
SELECT t.schedule, q.m3,
       ROUND(SUM(MAX(0, MIN(q.m3, COALESCE(t.tier_to_m3, 1e9)) - t.tier_from_m3) * (t.water_sar + t.sewage_sar)), 2)
         AS volume_charge_sar
FROM water_tariffs t CROSS JOIN q
WHERE t.schedule IN ('2016', '2027')
GROUP BY t.schedule, q.m3
ORDER BY q.m3, t.schedule;

-- 5. Inflation around each reform: the jump in the reform month and the reversal 12 months later.
WITH x AS (
  SELECT month, cpi_yoy_pct,
         cpi_yoy_pct - LAG(cpi_yoy_pct) OVER (ORDER BY month) AS change_pp
  FROM cpi_monthly)
SELECT e.title_en, x.month, ROUND(x.change_pp, 2) AS jump_pp,
       (SELECT ROUND(y.change_pp, 2) FROM x y
         WHERE y.month = strftime('%Y-%m', date(x.month || '-01', '+12 months'))) AS reversal_pp
FROM policy_events e
JOIN x ON x.month = substr(e.date, 1, 7)
WHERE e.title_en IN ('First electricity tariff reform', 'Second electricity tariff reform', 'VAT raised to 15%');

-- 6. Annual average inflation and its rank (RANK) among years.
SELECT substr(month, 1, 4) AS year, ROUND(AVG(cpi_yoy_pct), 2) AS avg_yoy,
       RANK() OVER (ORDER BY AVG(cpi_yoy_pct) DESC) AS rank_high_to_low
FROM cpi_monthly
GROUP BY year
ORDER BY year;

-- 7. Household profiles: annual increase and whether a 6,000 SAR/year allowance covers it.
SELECT name_ar, kwh_month, total_old_year, total_new_year,
       total_new_year - total_old_year AS increase_year,
       ROUND(100.0 * (total_new_year - total_old_year) / total_old_year, 1) AS increase_pct,
       CASE WHEN 6000 >= total_new_year - total_old_year THEN 'yes' ELSE 'no' END AS allowance_covers
FROM household_profiles
ORDER BY kwh_month;
