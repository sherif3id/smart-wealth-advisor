# Smart Wealth Advisor — Engineering Hardening Report

**Final verification date:** 2026-10-06  
**Product:** Smart Wealth Advisor

## Executive outcome

The existing Next.js interface and product design were preserved while the financial, ML, recommendation, security, data-authority, and infrastructure layers were hardened in the required order.

The resulting architecture is:

```text
Browser
  → Next.js UI
  → same-origin /api/core BFF
      (HttpOnly SameSite=Lax access-token cookie; CSRF origin checks)
  → FastAPI Core
      → PostgreSQL, authoritative financial store
      → ML FastAPI, inference only
      → SMTP/Gmail when configured

AI advisor
  Browser → Next advisor BFF → authoritative Core context/history → Gemini
  Proposed mutation → typed Core prepare endpoint → exact confirmation token
  → explicit user approval → typed Core execute endpoint → database + audit event
```

**Evidence-based completion score: 91/100.** Core financial correctness, persistence boundaries, security controls, recommendation safety, ML contracts, report authority, notification scheduling logic, build, and automated tests are implemented. The deduction reflects the absence of a Docker/PostgreSQL runtime in the sandbox, intentionally absent real production ML artifacts, SMTP/scheduler operational dependencies, browser-print rather than native PDF generation, the monolithic frontend, prompt-based risk input, and remaining broad accessibility/localization testing.

## Final verification evidence

| Check | Result |
|---|---|
| Backend pytest | **19 passed in 9.77s** |
| ML pytest | **3 passed in 11.00s** |
| Playwright | **1 passed in 6.2s**; one end-to-end test exercises language gate, auth, onboarding, BFF persistence, authoritative summary, reload persistence, explicitly labeled synthetic-demo analytics, Monte Carlo, report snapshot/history, Arabic RTL, and logout revocation |
| Total automated test cases | **23 passed** (19 backend + 3 ML + 1 browser) |
| Next.js production build | **Passed**; `/`, `/api/advisor`, `/api/core/[...path]`, and `/api/cron/notifications` compiled |
| npm dependency audit | **0 vulnerabilities** (`npm audit --omit=dev`) |
| Alembic fresh upgrade | **Passed** against an empty isolated SQLite verification database |
| Alembic drift check | **Passed** — `No new upgrade operations detected.` |
| Migration schema | Explicit **24-table** `0001_initial` baseline |
| Live Core readiness | HTTP 200; actual DB `SELECT 1` ready; ML process and all three local demo artifacts ready with `production_eligible: false` |
| Live ML readiness | HTTP 200 with `ready: true`; every artifact explicitly classified `synthetic-demo` |
| Advisor configuration | Route and structured-output integration built; live status reports `configured: false` because no Gemini secret was supplied to this sandbox |
| Docker Compose runtime | **Not run** — Docker is unavailable in the sandbox |
| PostgreSQL migration/runtime | **Not run** — no PostgreSQL server is available; production is configured PostgreSQL-only |

SQLite was used only for isolated backend tests and migration verification. `DATABASE_URL` is now required, and production validation rejects SQLite, weak/default JWT secrets, and `AUTO_CREATE_TABLES=true`.

## Specific bugs and risks fixed

### Financial correctness

- Separated liquid account balances, emergency-eligible balances, goals, portfolios, and liabilities.
- Corrected net worth to active account balances plus user-priced positions minus outstanding liabilities.
- Corrected DTI to required monthly debt payments divided by gross monthly income.
- Corrected savings rate to monthly surplus divided by monthly income.
- Added essential/discretionary totals, normalized category totals, transaction count, budget utilization, goal progress, data date, and methodology to one authoritative summary.
- Enforced household base currency and rejected mixed-currency writes because FX conversion does not exist.
- Preserved exact decimal monetary persistence.

### ML correctness

- Unified training and inference under the versioned `monthly-financial-v2` feature contract.
- Removed category-name substring semantics from ML feature construction.
- Added explicit current-calendar-month inference metadata.
- Retained Linear Regression, Random Forest, and Gradient Boosting comparison with chronological train/validation/test and MAE/RMSE/R².
- Made four K-Means labels unique, deterministic, and persisted with artifacts.
- Removed false “confidence”; centroid distance is labeled as distance.
- Reframed anomaly results as unusual aggregate monthly spending patterns, explicitly not fraud.
- Split dependency-free liveness from artifact-load readiness; missing or corrupt artifacts return honest 503 responses.
- Added a deterministic, explicitly synthetic 12-user × 12-month generator for testing/demo only.

### Recommendation safety

- Added deterministic candidate validation, safety ordering, quantification, rank 1–4, type deduplication, active-record supersession, methodology versioning, and persistence.
- Prevented investment-readiness suggestions when critical debt/reserve conditions or a conservative profile conflict.
- Added tests for rank ordering, duplicate prevention, repeated refresh, and debt/reserve/cash-flow conflicts.

### Security and ownership

- Added password policy and normalized email uniqueness/login.
- Bound JWTs to expiry, type, issuer, audience, JTI, and revocation state; logout revokes tokens.
- Enforced the supported single-household invariant instead of selecting an arbitrary membership.
- Added cross-user tests across accounts, transactions, budgets, goals/contributions, liabilities, portfolios/positions, reports, recommendations, alerts, risk, scenarios, advisor history, and notifications.
- Added typed AI action payloads and user/exact-action-bound, expiring, consumed confirmation records. Tests cover wrong user, modified action, expired token, replay, success, and auditing.
- Hardened the BFF with body-size limits, narrow forwarded headers, HttpOnly cookies, SameSite=Lax, and unsafe-method CSRF checks.
- Fixed a real proxy-origin CSRF defect found by Playwright: valid same-origin browser registration was previously rejected when `req.nextUrl.origin` differed from forwarded host/protocol.
- Added request IDs, sanitized unhandled errors, security headers, proxy-aware throttling keys, and structured failure logging.

### Frontend authority and UX

- Removed the duplicate client financial engine (`lib/financial-engine.ts`).
- Hydrated dashboard values from the server summary and removed silent local financial/ML fallbacks.
- Reports now render persisted snapshots containing `data_as_of`, methodology, assumptions, normalized category totals, recommendations, and disclaimer text.
- Reworded PDF behavior accurately as browser Print/Save as PDF.
- Added an honest ML-not-trained/deployed state with retry.
- Labeled portfolio prices as user-entered and surfaced actual allocation/concentration.
- Made Monte Carlo output use the household currency rather than hard-coded dollars.
- Removed invented project “match” percentages and reframed the surface as an unvalidated educational idea library with illustrative—not forecast—income scenarios.
- Removed “local AI fallback” claims; failed advisor requests now say unavailable and explicitly state no substitute was generated.
- Fixed Arabic profile-plan text and set document `lang`/`dir` during instant language switching.
- Fixed the fixed sidebar so bottom controls, including logout, remain reachable on shorter browser viewports.

### Infrastructure

- Replaced dynamic migration behavior with an explicit full Alembic baseline.
- Added actual DB readiness via `SELECT 1` and separate ML artifact status.
- Restricted production to PostgreSQL and required non-default JWT/database configuration.
- Kept Compose to exactly four services with healthchecks and dependency ordering.
- Documented backend, BFF, PostgreSQL, SMTP, cron, and ML configuration in `.env.example` and project documentation.

## Database model and relationships

- `users` ↔ `households` through `household_members`; exactly one membership is supported per user.
- A household owns accounts, categories, transactions, budgets, goals, liabilities, portfolios, risk assessments, snapshots, recommendations, alerts, notifications, scenarios, reports, advisor messages, and audit events.
- `budget_items` belong to budgets.
- `goal_contributions` belong to goals.
- `positions` belong to portfolios.
- Transactions optionally reference household-owned accounts and categories.
- `revoked_tokens` persist JWT revocation; consumed AI confirmation records prevent replay.
- Database uniqueness and indexes include normalized email, household/category constraints, and notification dispatch lookup.

## Core endpoint groups

- Health: `GET /health/live`, `GET /health/ready`, `GET /health`
- Auth/profile: `/auth/register`, `/auth/login`, `/auth/me`, `/auth/logout`, `/profile`
- Accounts/transactions/income: `/accounts`, `/transactions`, `/income`
- Planning records: `/budgets`, `/goals`, `/liabilities`, `/financial-summary`
- Recommendations/reports/alerts: `/recommendations`, `/reports`, `/alerts`
- Risk/portfolio: `/risk-assessments`, `/portfolios`
- Simulation/ML: `/scenarios/monte-carlo`, `/scenarios`, `/ml/status`, `/ml/insights`
- Advisor/actions: `/advisor/context`, `/advisor/messages`, `/ai-actions/prepare`, `/ai-actions/execute`
- Notifications: `/notifications`, `/notifications/test`, `/notifications/dispatch`

OpenAPI remains the exact request/response contract reference.

## ML workflow and artifact status

1. Supply monthly user observations with `user_id`, `month`, income, seven normalized spending categories, monthly debt service, monthly surplus, and next-month expense target.
2. `feature_definitions.py` applies the same formulas and column order used at inference.
3. `train_models.py` performs chronological train/validation/test separation, compares three regressors, evaluates the selected model, trains Isolation Forest and four-cluster K-Means, and writes versioned artifacts/metadata.
4. `/health/ready` safely attempts required artifact loading and reports per-model state.
5. Core builds one explicit calendar-month vector from authoritative records and forwards it to ML.
6. UI displays model output only when the deployed artifact set is loadable.

**Current status:** no real production dataset or production-eligible artifacts are included. The local preview has a complete artifact set trained from the deterministic 12-user × 12-month synthetic demo solely to exercise integration. Health responses and UI identify `synthetic-demo` and `production_eligible: false`; the ML service rejects these artifacts whenever `APP_ENV=production`. Without reviewed real artifacts, production inference remains honestly unavailable.

## Hardening-relevant file changes

### Created

- `backend/app/financial_definitions.py`
- `backend/app/routers/accounts.py`
- `backend/migrations/script.py.mako`
- `backend/tests/test_financial_correctness.py`
- `backend/tests/test_hardening.py`
- `backend/tests/test_quality_expansion.py`
- `ml-service/feature_definitions.py`
- `ml-service/generate_synthetic_demo.py`
- `ml-service/README.md`
- `e2e/hardening.spec.ts`
- `playwright.config.ts`

### Replaced or materially modified

- `.env.example`
- `README.md`
- `docker-compose.yml`
- `package.json`
- `package-lock.json`
- `app/page.tsx`
- `app/globals.css`
- `app/api/core/[...path]/route.ts`
- `app/api/advisor/route.ts`
- `app/api/cron/notifications/route.ts`
- `lib/api.ts`
- `backend/app/auth.py`
- `backend/app/config.py`
- `backend/app/database.py`
- `backend/app/main.py`
- `backend/app/models.py`
- `backend/app/schemas.py`
- `backend/app/services.py`
- `backend/app/routers/__init__.py`
- `backend/app/routers/advisor.py`
- `backend/app/routers/ai_actions.py`
- `backend/app/routers/analytics.py`
- `backend/app/routers/auth.py`
- `backend/app/routers/budgets.py`
- `backend/app/routers/goals.py`
- `backend/app/routers/liabilities.py`
- `backend/app/routers/notifications.py`
- `backend/app/routers/planning.py`
- `backend/app/routers/risk_portfolio.py`
- `backend/app/routers/transactions.py`
- `backend/migrations/env.py`
- `backend/migrations/versions/0001_initial.py`
- `backend/tests/conftest.py`
- `backend/tests/test_core.py`
- `backend/tests/test_security_notifications.py`
- `ml-service/main.py`
- `ml-service/train_models.py`
- `ml-service/test_ml.py`
- `docs/implementation-matrix.md`
- `docs/productionization-report.md`

### Deleted

- `lib/financial-engine.ts` — no remaining imports; authoritative logic now resides in Core.

## Honest remaining limitations

1. Docker Compose and PostgreSQL were not runtime-tested because Docker and a PostgreSQL server are unavailable in the sandbox. Compose syntax and configuration were source-audited; the migration was executable only against isolated SQLite here.
2. Production ML requires a validated real dataset and deployed, version-compatible artifacts. None were fabricated.
3. SMTP/Gmail credentials and an external scheduler are required for real periodic delivery.
4. Portfolio prices are user-entered; there is no live market-data integration.
5. PDF delivery uses browser Print/Save as PDF; HTML and CSV are direct exports.
6. The original frontend remains a large `app/page.tsx`. Component decomposition, full WCAG testing, responsive-device coverage, and visual regression testing remain worthwhile follow-up work.
7. Risk assessment is functional and validated but currently uses browser prompts rather than a polished inline questionnaire.
8. Some server-generated recommendation prose is English even in Arabic mode; the main UI, reports, and tested Arabic journey are localized, but complete server-side bilingual content generation should be expanded.
9. The process-local rate limiter is correct only for the defined single-backend deployment. Horizontal scaling would require a shared limiter, intentionally not added here.
