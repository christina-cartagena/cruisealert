-- =============================================================================
-- CruiseAlert — canonical database schema (PostgreSQL 15)
-- =============================================================================
-- This file is the single source of truth for the database. The SQLAlchemy
-- models in app/models/ mirror it exactly. Apply with:
--     psql $DATABASE_URL -f cruisealert_schema.sql
-- =============================================================================

-- ----------------------------------------------------------------------------
-- Extensions
-- ----------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS citext;      -- case-insensitive email
CREATE EXTENSION IF NOT EXISTS pg_trgm;     -- trigram search on destination_region

-- ----------------------------------------------------------------------------
-- Enums
-- ----------------------------------------------------------------------------
DO $$ BEGIN
    CREATE TYPE cruise_line AS ENUM (
        'royal_caribbean',
        'carnival',
        'norwegian',
        'princess',
        'celebrity',
        'msc',
        'holland_america',
        'disney',
        'virgin_voyages'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE cabin_type AS ENUM ('interior', 'oceanview', 'balcony', 'suite');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE trigger_type AS ENUM ('price_drop', 'back_in_stock', 'availability_threshold');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE alert_status AS ENUM ('active', 'paused', 'fired', 'expired');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE user_tier AS ENUM ('free', 'pro');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE scrape_status AS ENUM ('success', 'failed');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE notification_channel AS ENUM ('email', 'sms');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ----------------------------------------------------------------------------
-- users
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email                       CITEXT NOT NULL UNIQUE,
    hashed_password             TEXT NOT NULL,
    tier                        user_tier NOT NULL DEFAULT 'free',
    is_email_verified           BOOLEAN NOT NULL DEFAULT FALSE,
    email_verification_token    TEXT,
    email_verification_sent_at  TIMESTAMP WITH TIME ZONE,
    stripe_customer_id          TEXT,
    stripe_subscription_id      TEXT,
    created_at                  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_users_email_verification_token
    ON users (email_verification_token);
CREATE INDEX IF NOT EXISTS ix_users_stripe_customer_id
    ON users (stripe_customer_id);

-- ----------------------------------------------------------------------------
-- notification_preferences  (1:1 with users)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS notification_preferences (
    user_id             UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    email_enabled       BOOLEAN NOT NULL DEFAULT TRUE,
    sms_enabled         BOOLEAN NOT NULL DEFAULT FALSE,
    phone_e164          TEXT,
    phone_verified      BOOLEAN NOT NULL DEFAULT FALSE,
    phone_verified_at   TIMESTAMP WITH TIME ZONE,
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- ----------------------------------------------------------------------------
-- user_poll_schedule  (1:1 with users) — controls per-user alert cadence
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_poll_schedule (
    user_id             UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    poll_interval_min   INTEGER NOT NULL DEFAULT 240,   -- free=240, pro=30
    last_checked_at     TIMESTAMP WITH TIME ZONE,
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- ----------------------------------------------------------------------------
-- sailings
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sailings (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cruise_line         cruise_line NOT NULL,
    external_id         TEXT NOT NULL,
    market              TEXT NOT NULL,
    ship_name           TEXT NOT NULL,
    destination_region  TEXT NOT NULL,
    departure_port      TEXT NOT NULL,
    departure_date      DATE NOT NULL,
    return_date         DATE,
    duration_nights     INTEGER NOT NULL,
    itinerary_ports     TEXT[] NOT NULL DEFAULT '{}',
    ship_image_url      TEXT,
    booking_url         TEXT,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    first_seen_at       TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    last_scraped_at     TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT uq_sailings_external_id_market UNIQUE (external_id, market)
);

CREATE INDEX IF NOT EXISTS ix_sailings_cruise_line       ON sailings (cruise_line);
CREATE INDEX IF NOT EXISTS ix_sailings_departure_date    ON sailings (departure_date);
CREATE INDEX IF NOT EXISTS ix_sailings_departure_port    ON sailings (departure_port);
CREATE INDEX IF NOT EXISTS ix_sailings_duration_nights   ON sailings (duration_nights);
CREATE INDEX IF NOT EXISTS ix_sailings_is_active         ON sailings (is_active);
CREATE INDEX IF NOT EXISTS ix_sailings_destination_trgm
    ON sailings USING gin (destination_region gin_trgm_ops);

-- ----------------------------------------------------------------------------
-- cabin_prices  (append-only price history; delta-gated by the scraper)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cabin_prices (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sailing_id          UUID NOT NULL REFERENCES sailings(id) ON DELETE CASCADE,
    cabin_type          cabin_type NOT NULL,
    price_usd           NUMERIC(10, 2) NOT NULL,
    price_local         NUMERIC(10, 2),
    currency_code       CHAR(3) NOT NULL DEFAULT 'USD',
    cabins_available    INTEGER,
    recorded_at         TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- The hot path: "latest N rows for (sailing, cabin) by recorded_at desc".
CREATE INDEX IF NOT EXISTS ix_cabin_prices_lookup
    ON cabin_prices (sailing_id, cabin_type, recorded_at DESC);
CREATE INDEX IF NOT EXISTS ix_cabin_prices_recorded_at
    ON cabin_prices (recorded_at);

-- ----------------------------------------------------------------------------
-- alerts
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS alerts (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    sailing_id          UUID NOT NULL REFERENCES sailings(id) ON DELETE CASCADE,
    cabin_type          cabin_type NOT NULL,
    trigger_type        trigger_type NOT NULL,
    threshold_pct       NUMERIC(5, 2),     -- price_drop: optional (NULL = any drop)
    threshold_count     INTEGER,           -- availability_threshold: required
    status              alert_status NOT NULL DEFAULT 'active',
    cooldown_minutes    INTEGER NOT NULL DEFAULT 1440,
    email_enabled       BOOLEAN NOT NULL DEFAULT TRUE,
    sms_enabled         BOOLEAN NOT NULL DEFAULT FALSE,
    last_checked_at     TIMESTAMP WITH TIME ZONE,
    last_fired_at       TIMESTAMP WITH TIME ZONE,
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    -- availability_threshold alerts must carry a count
    CONSTRAINT ck_alerts_availability_count CHECK (
        trigger_type <> 'availability_threshold' OR threshold_count IS NOT NULL
    ),
    -- threshold_pct only meaningful for price_drop
    CONSTRAINT ck_alerts_threshold_pct_range CHECK (
        threshold_pct IS NULL OR (threshold_pct > 0 AND threshold_pct <= 100)
    )
);

CREATE INDEX IF NOT EXISTS ix_alerts_user_id    ON alerts (user_id);
CREATE INDEX IF NOT EXISTS ix_alerts_sailing_id ON alerts (sailing_id);
CREATE INDEX IF NOT EXISTS ix_alerts_status     ON alerts (status);

-- ----------------------------------------------------------------------------
-- alert_events  (one row per notification dispatched; powers cooldown logic)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS alert_events (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id            UUID NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
    trigger_type        trigger_type NOT NULL,
    channel             notification_channel NOT NULL,
    old_price_usd       NUMERIC(10, 2),
    new_price_usd       NUMERIC(10, 2),
    cabins_available    INTEGER,
    payload             JSONB,
    delivered           BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_alert_events_alert_id_created
    ON alert_events (alert_id, created_at DESC);

-- ----------------------------------------------------------------------------
-- scrape_runs  (audit trail for every (cruise_line, market) poll)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS scrape_runs (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cruise_line             cruise_line NOT NULL,
    market                  TEXT NOT NULL,
    status                  scrape_status NOT NULL DEFAULT 'success',
    sailings_found          INTEGER NOT NULL DEFAULT 0,
    prices_inserted         INTEGER NOT NULL DEFAULT 0,
    prices_unchanged        INTEGER NOT NULL DEFAULT 0,
    sailings_deactivated    INTEGER NOT NULL DEFAULT 0,
    error_message           TEXT,
    error_traceback         TEXT,
    started_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    completed_at            TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS ix_scrape_runs_started_at
    ON scrape_runs (started_at DESC);
CREATE INDEX IF NOT EXISTS ix_scrape_runs_line_market
    ON scrape_runs (cruise_line, market);

-- ============================================================================
-- Functions and triggers
-- ============================================================================

-- Generic updated_at maintenance ---------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_users_updated_at ON users;
CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_alerts_updated_at ON alerts;
CREATE TRIGGER trg_alerts_updated_at BEFORE UPDATE ON alerts
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_notif_prefs_updated_at ON notification_preferences;
CREATE TRIGGER trg_notif_prefs_updated_at BEFORE UPDATE ON notification_preferences
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_poll_sched_updated_at ON user_poll_schedule;
CREATE TRIGGER trg_poll_sched_updated_at BEFORE UPDATE ON user_poll_schedule
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Auto-provision per-user prefs + poll schedule on user creation -------------
CREATE OR REPLACE FUNCTION provision_user_defaults() RETURNS trigger AS $$
BEGIN
    INSERT INTO notification_preferences (user_id) VALUES (NEW.id)
        ON CONFLICT (user_id) DO NOTHING;
    INSERT INTO user_poll_schedule (user_id, poll_interval_min)
        VALUES (NEW.id, CASE WHEN NEW.tier = 'pro' THEN 30 ELSE 240 END)
        ON CONFLICT (user_id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_users_provision_defaults ON users;
CREATE TRIGGER trg_users_provision_defaults AFTER INSERT ON users
    FOR EACH ROW EXECUTE FUNCTION provision_user_defaults();

-- Free-tier alert cap: max 3 live (active|fired) alerts ----------------------
-- Raises SQLSTATE P0001 (the default for RAISE EXCEPTION) which the API layer
-- catches and converts to HTTP 403 {code: "alert_limit_reached"}.
CREATE OR REPLACE FUNCTION enforce_alert_limit() RETURNS trigger AS $$
DECLARE
    v_tier user_tier;
    v_live_count INTEGER;
BEGIN
    SELECT tier INTO v_tier FROM users WHERE id = NEW.user_id;

    IF v_tier = 'free' AND NEW.status IN ('active', 'fired') THEN
        SELECT count(*) INTO v_live_count
        FROM alerts
        WHERE user_id = NEW.user_id
          AND status IN ('active', 'fired')
          AND (TG_OP = 'INSERT' OR id <> NEW.id);

        IF v_live_count >= 3 THEN
            RAISE EXCEPTION 'Free tier limit is 3 active alerts.'
                USING ERRCODE = 'P0001';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_alerts_enforce_limit ON alerts;
CREATE TRIGGER trg_alerts_enforce_limit
    BEFORE INSERT OR UPDATE OF status, user_id ON alerts
    FOR EACH ROW EXECUTE FUNCTION enforce_alert_limit();

-- Expire alerts whose sailing has already departed ---------------------------
-- Returns the number of alerts expired. Called by the alert worker as:
--     SELECT expire_past_alerts();
CREATE OR REPLACE FUNCTION expire_past_alerts() RETURNS integer AS $$
DECLARE
    v_count integer;
BEGIN
    WITH expired AS (
        UPDATE alerts a
        SET status = 'expired'
        FROM sailings s
        WHERE a.sailing_id = s.id
          AND a.status IN ('active', 'fired')
          AND s.departure_date < CURRENT_DATE
        RETURNING a.id
    )
    SELECT count(*) INTO v_count FROM expired;
    RETURN v_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Views
-- ============================================================================

-- Most-recent price row per (sailing, cabin_type) ----------------------------
CREATE OR REPLACE VIEW latest_cabin_prices AS
SELECT DISTINCT ON (cp.sailing_id, cp.cabin_type)
    cp.sailing_id,
    cp.cabin_type,
    cp.price_usd,
    cp.price_local,
    cp.currency_code,
    cp.cabins_available,
    cp.recorded_at
FROM cabin_prices cp
ORDER BY cp.sailing_id, cp.cabin_type, cp.recorded_at DESC;

-- Latest price + trend vs the immediately preceding row ----------------------
-- price_trend: 'down' | 'up' | 'stable' (stable when no prior row).
CREATE OR REPLACE VIEW cabin_price_trends AS
WITH ranked AS (
    SELECT
        cp.*,
        row_number() OVER (
            PARTITION BY cp.sailing_id, cp.cabin_type
            ORDER BY cp.recorded_at DESC
        ) AS rn
    FROM cabin_prices cp
)
SELECT
    cur.sailing_id,
    cur.cabin_type,
    cur.price_usd,
    cur.price_local,
    cur.currency_code,
    cur.cabins_available,
    cur.recorded_at,
    prev.price_usd AS previous_price_usd,
    CASE
        WHEN prev.price_usd IS NULL          THEN 'stable'
        WHEN cur.price_usd < prev.price_usd  THEN 'down'
        WHEN cur.price_usd > prev.price_usd  THEN 'up'
        ELSE 'stable'
    END AS price_trend
FROM ranked cur
LEFT JOIN ranked prev
    ON  prev.sailing_id = cur.sailing_id
    AND prev.cabin_type = cur.cabin_type
    AND prev.rn = 2
WHERE cur.rn = 1;

-- Active alerts enriched with current price + user prefs + poll schedule ------
CREATE OR REPLACE VIEW active_alerts_with_context AS
SELECT
    a.id                AS alert_id,
    a.user_id,
    a.sailing_id,
    a.cabin_type,
    a.trigger_type,
    a.threshold_pct,
    a.threshold_count,
    a.status,
    a.cooldown_minutes,
    a.email_enabled     AS alert_email_enabled,
    a.sms_enabled       AS alert_sms_enabled,
    a.last_checked_at,
    a.last_fired_at,
    u.email             AS user_email,
    u.tier              AS user_tier,
    np.email_enabled    AS pref_email_enabled,
    np.sms_enabled      AS pref_sms_enabled,
    np.phone_e164,
    np.phone_verified,
    ups.poll_interval_min,
    ups.last_checked_at AS user_last_checked_at,
    s.cruise_line,
    s.ship_name,
    s.destination_region,
    s.departure_port,
    s.departure_date,
    s.booking_url,
    s.market,
    lcp.price_usd           AS current_price_usd,
    lcp.cabins_available    AS current_cabins_available,
    lcp.recorded_at         AS current_recorded_at
FROM alerts a
JOIN users u                        ON u.id  = a.user_id
LEFT JOIN notification_preferences np ON np.user_id = a.user_id
LEFT JOIN user_poll_schedule ups      ON ups.user_id = a.user_id
JOIN sailings s                       ON s.id = a.sailing_id
LEFT JOIN latest_cabin_prices lcp
    ON  lcp.sailing_id = a.sailing_id
    AND lcp.cabin_type = a.cabin_type
WHERE a.status = 'active';
