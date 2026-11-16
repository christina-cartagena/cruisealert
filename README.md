# CruiseAlert

Track cruise pricing across 9 cruise lines (via the RapidAPI Cruise Pricing
API), store price history, and notify users by **email + SMS** when prices drop,
cabins come back in stock, or availability falls below a threshold.

- **Backend** — Python 3.12, FastAPI, SQLAlchemy 2.x (async), Alembic, Celery 5
- **Database** — PostgreSQL 15 · **Broker/cache** — Redis 7
- **Frontend** — React 18 + TypeScript + Vite + Tailwind + shadcn/ui, TanStack Query, Zustand
- **Integrations** — SendGrid (email), Twilio (SMS + Verify), Stripe (billing)

```
cruisealert/
├── backend/          FastAPI app, Celery workers, Alembic, tests
│   ├── app/          config, database, models, schemas, routers, services, workers
│   ├── alembic/      migrations (0001 applies cruisealert_schema.sql)
│   ├── tests/        pytest suite (alert engine, scraper delta-check, auth)
│   └── cruisealert_schema.sql   canonical DB schema (source of truth)
├── frontend/         React SPA
├── docker-compose.yml   local Postgres + Redis
└── .env.example
```

---

## Quick start (local dev)

> **Prerequisites:** Docker Desktop (for Postgres + Redis), Python 3.12 (managed
> here via [`uv`](https://docs.astral.sh/uv/)), and Node 18+.

### 1. Infrastructure

```bash
cp .env.example .env        # then fill in real API keys
docker compose up -d        # starts postgres:5432 and redis:6379
```

### 2. Backend

```bash
cd backend
uv venv --python 3.12
uv pip install -e ".[dev]"

# Apply the schema. Either of these works (the Alembic migration runs the same
# idempotent SQL, so there is zero drift between them):
psql "$DATABASE_URL" -f cruisealert_schema.sql       # option A: raw SQL
alembic upgrade head                                  # option B: migration

# Run the API
uvicorn app.main:app --reload
# -> http://localhost:8000/health  ->  {"status":"ok"}
# -> http://localhost:8000/docs    (OpenAPI)
```

### 3. Workers (separate terminals)

```bash
cd backend
celery -A app.workers.celery_app worker --loglevel=info --concurrency=4
celery -A app.workers.celery_app beat   --loglevel=info
```

Trigger a scrape manually:

```bash
celery -A app.workers.celery_app call app.workers.scraper_tasks.poll_all_cruise_lines
```

### 4. Frontend

```bash
cd frontend
npm install
cp .env.example .env        # VITE_API_URL=http://localhost:8000
npm run dev                 # -> http://localhost:5173
```

---

## Tests

```bash
cd backend
JWT_SECRET=test pytest -q
```

- **Always run** (no DB needed): the alert-engine predicates, the scraper
  delta-check (`should_insert_price` / `price_or_availability_changed`), the
  normalizers, and the auth crypto/JWT round-trips.
- **DB-backed** tests use the `db_session` fixture and are **skipped** if no test
  database is reachable. Point `TEST_DATABASE_URL` at a disposable database
  (e.g. a `cruisealert_test` DB on the local Docker Postgres) to enable them.

The current suite (36 tests) passes without a database.

---

## Key design notes

- **RapidAPI usage gate** — every outbound call is reserved against a Redis
  counter (`rapidapi:usage:YYYY-MM`, cap 95/month, self-expiring) so the plan's
  hard 100-call limit can never be exceeded. When capped, the run is logged and
  a `scrape_runs` row is recorded instead of calling the API.
- **Delta-checked price history** — `cabin_prices` is append-only; a new row is
  written only when price *or* availability changed (`should_insert_price`),
  keeping history compact. This is the most-tested piece of the scraper.
- **Alert engine** — three pure predicates (`should_fire_price_drop`,
  `should_fire_back_in_stock`, `should_fire_availability_threshold`) with 100%
  branch coverage; all I/O lives in the Celery task that calls them.
- **Tiers** — the free-tier 3-alert cap is enforced by a Postgres trigger that
  raises `P0001`; the API converts that to HTTP 403 `alert_limit_reached`.
  Free users get 7 days of price history; Pro gets 90. Poll cadence is 240 min
  (free) / 30 min (pro), stored in `user_poll_schedule`.
- **Auth** — JWT HS256. Access token (15 min) is returned in the body and held
  in memory (Zustand) on the client; the refresh token (7 days) lives only in an
  httpOnly `refresh_token` cookie and is rotated on every refresh.
- **Schema is the source of truth** — `cruisealert_schema.sql` owns the enums,
  tables, indexes, the `set_updated_at` / `provision_user_defaults` /
  `enforce_alert_limit` / `expire_past_alerts` functions, and the
  `latest_cabin_prices` / `cabin_price_trends` / `active_alerts_with_context`
  views. The ORM models mirror it; migration `0001` applies it verbatim.

---

## Deployment

**Backend (Railway)** — four services from `backend/`, all sharing env vars:

| Service  | Command |
|----------|---------|
| `api`    | `uvicorn app.main:app --host 0.0.0.0 --port 8000` |
| `worker` | `celery -A app.workers.celery_app worker --loglevel=info --concurrency=4` |
| `beat`   | `celery -A app.workers.celery_app beat --loglevel=info` |
| postgres | Railway Postgres plugin → sets `DATABASE_URL` |
| redis    | Railway Redis plugin → sets `REDIS_URL` |

After first deploy: `alembic upgrade head`, hit `/health`, register a user,
trigger a scrape, confirm `scrape_runs` + `sailings` populate, create an alert,
run `check_all_alerts`, confirm an `alert_events` row + email.

**Frontend (Vercel)** — set `VITE_API_URL` to the Railway API URL.
`frontend/vercel.json` provides the SPA rewrite.

---

## ⚠️ Before going live — confirm against the live RapidAPI docs

The exact RapidAPI **endpoint paths** (`CRUISE_LINE_CONFIGS`) and **response
field names** (the per-line normalizers in `app/services/rapidapi.py`) are
modeled on the documented `cruise-prices.p.rapidapi.com` surface but **must be
verified against the current provider docs** for each of the 9 lines. The
normalizers are deliberately defensive: unknown/missing fields cause a sailing
to be skipped with a warning rather than crashing a scrape — so schema drift
degrades gracefully, but real data won't flow until the paths/field maps match.

### Local environment caveats observed during build
This repo was scaffolded on a machine where **Docker Desktop and `psql` were not
running/installed**, so the live Postgres/Redis stack and end-to-end scrape were
**not exercised locally**. Everything that doesn't need those services is
verified: all backend modules import, the 36-test suite passes, and the frontend
type-checks and builds. Start Docker (`docker compose up -d`) and run
`alembic upgrade head` to bring up the full stack.
