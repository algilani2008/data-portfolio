-- Saudi labour market: employment by economic activity and quarter
-- Source: GASTAT register-based labour market statistics (see ../README.md)
-- Works in SQLite 3.25+ and PostgreSQL.

DROP VIEW  IF EXISTS v_employment;
DROP TABLE IF EXISTS employment;
DROP TABLE IF EXISTS activities;

CREATE TABLE activities (
    activity_id    INTEGER PRIMARY KEY,
    activity_code  VARCHAR(30)  NOT NULL UNIQUE,
    name_en        VARCHAR(120) NOT NULL,
    name_ar        VARCHAR(120) NOT NULL
);

CREATE TABLE employment (
    activity_id         INTEGER NOT NULL REFERENCES activities (activity_id),
    year                INTEGER NOT NULL,
    quarter             INTEGER NOT NULL CHECK (quarter BETWEEN 1 AND 4),
    total_employed      INTEGER NOT NULL CHECK (total_employed >= 0),
    non_saudi_employed  INTEGER NOT NULL CHECK (non_saudi_employed >= 0),
    PRIMARY KEY (activity_id, year, quarter),
    CHECK (non_saudi_employed <= total_employed)
);

-- Derived measures in one place, so every query uses the same definitions.
CREATE VIEW v_employment AS
SELECT
    e.activity_id,
    a.activity_code,
    a.name_ar,
    a.name_en,
    e.year,
    e.quarter,
    e.year * 10 + e.quarter                              AS period,       -- e.g. 20251 = Q1 2025
    e.total_employed,
    e.non_saudi_employed,
    e.total_employed - e.non_saudi_employed              AS saudi_employed,
    CASE WHEN e.total_employed = 0 THEN 0
         ELSE 1.0 * (e.total_employed - e.non_saudi_employed) / e.total_employed
    END                                                  AS saudization_rate
FROM employment e
JOIN activities a ON a.activity_id = e.activity_id;
