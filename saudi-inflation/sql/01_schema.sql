-- Saudi inflation by spending category (CPI, base 2023 = 100)
-- Sources: SAMA Inflation Report Q1 2026 (Table 2) and GASTAT CPI bulletin June 2026.
-- Works in SQLite 3.25+ and PostgreSQL.

DROP TABLE IF EXISTS cpi_divisions;
DROP TABLE IF EXISTS cpi_headline_monthly;

-- code '00' is the published general index; '01'-'13' are the spending categories.
CREATE TABLE cpi_divisions (
    code          CHAR(2)       PRIMARY KEY,
    name_en       VARCHAR(80)   NOT NULL,
    name_ar       VARCHAR(80)   NOT NULL,
    weight_pct    NUMERIC(5, 1) NOT NULL CHECK (weight_pct > 0 AND weight_pct <= 100),
    cpi_q1_2025   NUMERIC(6, 1) NOT NULL,
    cpi_q4_2025   NUMERIC(6, 1) NOT NULL,
    cpi_q1_2026   NUMERIC(6, 1) NOT NULL,
    chg_2025_pct  NUMERIC(4, 1)
);

CREATE TABLE cpi_headline_monthly (
    month           CHAR(7)       PRIMARY KEY,   -- YYYY-MM
    mom_change_pct  NUMERIC(4, 1) NOT NULL,
    yoy_change_pct  NUMERIC(4, 1)                -- NULL before June 2025 (not in the source bulletin)
);
