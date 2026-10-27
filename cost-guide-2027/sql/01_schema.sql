-- cost-guide-2027: schema (SQLite)
DROP TABLE IF EXISTS electricity_tariffs;
DROP TABLE IF EXISTS electricity_fees;
DROP TABLE IF EXISTS water_tariffs;
DROP TABLE IF EXISTS cpi_monthly;
DROP TABLE IF EXISTS policy_events;
DROP TABLE IF EXISTS household_profiles;

CREATE TABLE electricity_tariffs (
    schedule      TEXT    NOT NULL,
    tier_from_kwh INTEGER NOT NULL CHECK (tier_from_kwh >= 0),
    tier_to_kwh   INTEGER,                       -- NULL = open-ended top tier
    rate_halala   REAL    NOT NULL CHECK (rate_halala > 0),
    PRIMARY KEY (schedule, tier_from_kwh)
);

CREATE TABLE electricity_fees (
    schedule       TEXT    NOT NULL,
    breaker_from_a INTEGER NOT NULL,
    breaker_to_a   INTEGER,
    fee_sar        REAL    NOT NULL CHECK (fee_sar >= 0),
    PRIMARY KEY (schedule, breaker_from_a)
);

CREATE TABLE water_tariffs (
    schedule     TEXT NOT NULL,
    tier_from_m3 REAL NOT NULL,
    tier_to_m3   REAL,
    water_sar    REAL NOT NULL,
    sewage_sar   REAL NOT NULL,
    PRIMARY KEY (schedule, tier_from_m3)
);

CREATE TABLE cpi_monthly (
    month       TEXT PRIMARY KEY,                -- YYYY-MM
    cpi_yoy_pct REAL NOT NULL
);

CREATE TABLE policy_events (
    date     TEXT NOT NULL,
    category TEXT NOT NULL,
    title_ar TEXT NOT NULL,
    title_en TEXT NOT NULL
);

CREATE TABLE household_profiles (
    id             TEXT PRIMARY KEY,
    name_ar        TEXT,
    kwh_month      REAL,
    water_m3       REAL,
    total_old_year REAL,
    total_new_year REAL
);
