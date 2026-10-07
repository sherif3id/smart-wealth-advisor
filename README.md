# Smart Wealth Advisor

A bilingual (English/Arabic) financial planning application with an existing Next.js interface, an authoritative FastAPI core, PostgreSQL persistence, and a separate scikit-learn inference service.

## Architecture

```text
Browser
  → Next.js UI + same-origin BFF (/api/core/*; HttpOnly JWT cookie)
    → FastAPI core API
      → PostgreSQL (authoritative financial store)
      → ML FastAPI service (only for inference)
      → SMTP/Gmail when configured
    → Gemini API (advisor only; context is fetched from the core API)
```

The browser may persist language, theme, and guidance checklist preferences. It does **not** persist authoritative transactions, budgets, goals, profiles, report history, notification settings, portfolios, scenarios, or AI mutation state.

## Local development

### Core API

```bash
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export JWT_SECRET='replace-with-at-least-32-random-characters'
export DATABASE_URL='postgresql+psycopg://wealth_app:replace-me@localhost:5432/smart_wealth'
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

`DATABASE_URL` is required. Use PostgreSQL for development and production. SQLite is used only by isolated automated tests and migration checks. API docs are at `http://localhost:8000/docs`.

### ML service

```bash
cd ml-service
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

Model-dependent calls return `503 MODEL_UNAVAILABLE` until compatible artifacts exist. Train production artifacts from a reviewed real CSV:

```bash
python train_models.py /path/to/reviewed_real_monthly_data.csv --out models
```

The included local integration artifacts are explicitly marked `synthetic-demo`, are shown with a warning in the UI, and are rejected whenever the ML service runs with `APP_ENV=production`. See `ml-service/DATA_PROVENANCE.md`.

Required dataset fields are documented in `ml-service/train_models.py`, including `user_id` and `month`. Validation uses a time-based holdout.

### Frontend

```bash
npm ci
BACKEND_URL=http://localhost:8000 npm run dev
```

Set `GEMINI_API_KEY` server-side to enable the advisor, then verify `GET /api/advisor` reports `configured: true`. Never expose it as `NEXT_PUBLIC_*`. Structured Gemini output is validated and every mutation remains Core-confirmation-gated.

## Docker Compose

Copy `.env.example` to `.env`, replace every secret, then:

```bash
docker compose up --build
```

For an explicitly labeled local synthetic-demo analytics run:

```bash
docker compose -f docker-compose.yml -f docker-compose.demo.yml up --build
```

Compose runs `frontend`, `backend`, `postgres`, and `ml-service`. The backend applies Alembic migrations before startup. ML artifacts are mounted read-only from `ml-service/models`.

## Main API groups

- System: `GET /health`
- Authentication/profile: `/auth/register`, `/auth/login`, `/auth/me`, `/auth/logout`, `/profile`
- Transactions/income: `/transactions`, `/income` (categories are normalized server-side during transaction writes)
- Planning: `/budgets`, `/goals`, `/liabilities`, `/financial-summary`
- Risk/portfolio: `/risk-assessments`, `/portfolios`
- Recommendations/reports/alerts: `/recommendations`, `/reports`, `/alerts`
- Simulations/ML: `/scenarios/monte-carlo`, `/ml/insights`
- Advisor: `/advisor/context`, `/advisor/messages`
- Confirmed AI actions: `/ai-actions/prepare`, `/ai-actions/execute`
- Notifications: `/notifications`, `/notifications/test`, `/notifications/dispatch`

OpenAPI contains the complete request and response contracts.

## Security controls

- Argon2id-compatible password hashing through `pwdlib`/Argon2.
- Short-lived signed JWT access tokens with JTI revocation on logout.
- HttpOnly, SameSite=Lax cookie at the Next.js BFF; JavaScript never receives the token.
- Ownership resolved from authenticated membership; client `user_id` is never trusted.
- Exact `NUMERIC`/`Decimal` monetary persistence.
- Pydantic validation and structured error envelopes.
- CORS allowlist, security response headers, environment-only secrets, and throttling on auth endpoints.
- AI actions are allowlisted, schema-checked, bound to the current user and exact payload by a short-lived signed confirmation token, then require explicit UI confirmation.
- AI context is assembled by the server from the database.

The built-in rate limiter is process-local and suitable for the defined single-backend Compose deployment; a multi-instance deployment would need a shared limiter.

## Notifications

Configure `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `NOTIFICATION_FROM`, and `CRON_SECRET`. Gmail generally requires an app password. An external scheduler should call:

```http
GET /api/cron/notifications
Authorization: Bearer <CRON_SECRET>
```

The core dispatcher respects each enabled user's daily, weekly, or monthly interval. Without SMTP configuration, delivery endpoints report an explicit 503 rather than pretending mail was sent.

## Verification

```bash
cd backend && pytest -q
cd ../ml-service && pytest -q
cd .. && npm run build
npx playwright test
npm audit --omit=dev
```

See `docs/implementation-matrix.md` for the audit-to-implementation mapping.

## Honest limitations

- No real training dataset or production-eligible model artifacts are included. Local demo inference is explicitly labeled synthetic and blocked in production; production inference reports unavailable until reviewed real artifacts are installed.
- No live market-data provider is included. Portfolio prices are user-entered and labeled accordingly.
- PDF output uses the browser's print/save-as-PDF flow; HTML and CSV download directly.
- SMTP credentials and an external scheduler are operational configuration, not committed code.
- The monolithic original `app/page.tsx` was preserved rather than replaced; further component decomposition would improve maintainability.
