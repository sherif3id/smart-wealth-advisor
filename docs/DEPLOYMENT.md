# Smart Wealth Advisor deployment

## Docker demo (local integration only)

The repository contains artifacts explicitly marked `synthetic-demo`. To exercise all analytics locally while retaining the warning banner:

```bash
cp .env.example .env
# Replace POSTGRES_PASSWORD, JWT_SECRET, CORS_ORIGINS, CRON_SECRET,
# and optionally GEMINI_API_KEY. Do not commit .env.
docker compose -f docker-compose.yml -f docker-compose.demo.yml up --build
```

The override sets `APP_ENV=development` and `ML_ALLOW_SYNTHETIC_DEMO=true` only for the ML container. The API and UI expose the dataset classification. These outputs are integration demonstrations, not production forecasts.

## Docker production

```bash
docker compose -f docker-compose.yml up --build
```

The base Compose file sets:

- PostgreSQL as the only production database;
- `AUTO_CREATE_TABLES=false` and runs Alembic;
- `APP_ENV=production` for ML;
- `ML_ALLOW_SYNTHETIC_DEMO=false`.

Therefore the included demo artifacts are rejected in production. Deploy a complete real-data artifact set generated without `--synthetic` before enabling production ML inference.

## Gemini advisor

Set these on the **frontend server/container**, never in browser code:

```env
GEMINI_API_KEY=your_server_side_key
GEMINI_MODELS=gemini-3.8-flash,gemini-3.5-flash-lite,gemini-2.5-flash
```

Restart the frontend after changing environment variables. Check configuration without exposing the key:

```bash
curl http://localhost:3000/api/advisor
```

`configured` must be `true`. The advisor still requires a signed-in user because its context and memory come from Core. Proposed mutations are not executed by Gemini; they pass through typed Core validation and explicit confirmation.

## Future cloud deployment

Deploy four logical workloads:

1. Managed PostgreSQL with backups, TLS, restricted network access, and migration execution.
2. Core FastAPI service with `DATABASE_URL`, `JWT_SECRET`, `CORS_ORIGINS`, `ML_SERVICE_URL`, and optional SMTP values.
3. ML FastAPI service with a read-only artifact volume/object download step and production demo blocking.
4. Next.js frontend with private `BACKEND_URL`, `GEMINI_API_KEY`, `GEMINI_MODELS`, and `COOKIE_SECURE=true`.

Browser code calls only the Next.js origin. `BACKEND_URL` and `ML_SERVICE_URL` must be server-reachable URLs; never use browser `localhost` for a remotely deployed service.

Recommended release gates:

- run backend and ML pytest suites;
- run `npm run build`, `npm audit --omit=dev`, and Playwright against staging;
- run `alembic upgrade head` as a one-off migration step;
- require `/health/ready` on Core and inspect ML artifact classification;
- verify `/api/advisor` reports configured before enabling the advisor entry point;
- test backup restoration, SMTP, cron authorization, logout revocation, and Arabic RTL in staging.
