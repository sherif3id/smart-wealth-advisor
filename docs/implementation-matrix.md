# Smart Wealth Advisor — Final Correctness Matrix

**Audit date:** 2026-10-06  
**Architecture preserved:** Browser → Next.js → same-origin BFF → FastAPI Core → PostgreSQL; Core → ML FastAPI for inference.

Status meanings: **Complete** = implemented and exercised; **Implemented / operational dependency** = code is complete but requires external data or credentials; **Defined / not runtime-verified** = configuration exists but the sandbox could not execute it.

| Area | Correctness requirement | Evidence in repository | Verification | Status / limitation |
|---|---|---|---|---|
| Financial authority | One server summary for income, expenses, surplus, savings rate, liquidity, emergency coverage, debt service/DTI, investments, assets, net worth, budgets, and goals | `backend/app/services.py`, `GET /financial-summary` | Backend financial tests and browser API assertion | Complete |
| Liquid savings | Active liquid account balances only; goals excluded | `financial_summary()` in `backend/app/services.py` | `test_authoritative_summary_separates_cash_goals_investments_and_debt` | Complete |
| Emergency coverage | Emergency-eligible liquid balances ÷ classified essential expenses; explicit classification method | `backend/app/services.py`, `backend/app/financial_definitions.py` | Financial summary and recommendation tests | Complete; returns unavailable when the denominator is absent rather than inventing a value |
| Net worth | Actual account assets + user-priced portfolio positions − liabilities | `backend/app/services.py` | Financial correctness test | Complete |
| Savings rate / DTI | Surplus ÷ gross income; required monthly debt service ÷ gross income | `backend/app/services.py` | Exact-value assertions | Complete |
| Currency | Household base currency enforced; no implicit FX | `ensure_currency()`, transaction/account/goal/liability/portfolio routes | Mixed-currency rejection test | Complete; FX conversion intentionally absent |
| Exact money | SQL `NUMERIC` and Python `Decimal` | `backend/app/models.py`, migration `0001_initial.py` | Migration/schema inspection and tests | Complete |
| Categories | Stable normalized codes and exact aliases; no ML substring matching | `backend/app/financial_definitions.py`, transaction routing, `analytics.ml_vector()` | Feature and summary tests | Complete |
| Accounts / transactions | Authenticated household-scoped CRUD, filters, pagination, persistence | `backend/app/routers/accounts.py`, `transactions.py` | Backend CRUD/isolation tests and Playwright persistence across reload | Complete |
| Budgets | Persisted category limits and actual spending utilization | `backend/app/routers/budgets.py`, `budget_view()` | Backend budget test | Complete |
| Goals | Persisted goals/contributions/progress; never treated as cash assets | `backend/app/routers/goals.py`, `goal_view()` | Backend summary and cross-user tests | Complete |
| Liabilities | Persisted balance and required payment; debt principal not used as DTI numerator | `backend/app/routers/liabilities.py` | Financial correctness test | Complete |
| Portfolio | User-entered prices, actual value, asset-class allocation, concentration, gain/loss | `backend/app/routers/risk_portfolio.py`, Portfolio UI | Backend summary/isolation tests and browser screen audit | Complete; no live market feed by design |
| Risk | Exactly six 1–5 answers; deterministic willingness/capacity cap and versioned educational result | `backend/app/routers/risk_portfolio.py` | Boundary, invalid-input, and capacity-cap tests | Complete; UI currently uses browser prompts rather than an inline form |
| Monte Carlo | Bounded inputs, fixed seed, ordered percentiles, bounded probabilities, assumptions/disclaimer | `backend/app/routers/analytics.py`, Simulator UI | Determinism/boundary backend test and Playwright currency/UI check | Complete |
| Recommendation pipeline | Authoritative inputs, safety-first conflicts, ranks 1–4, quantification, deduplication, persistence | `generate_recommendations()` and `/recommendations` | Ranking, conflict, repeat-refresh, and dedup tests | Complete; deterministic educational rules, not regulated advice |
| ML feature contract | Shared names, units, formulas, categories, monthly period, version | `backend/app/financial_definitions.py`, `ml-service/feature_definitions.py` | Training/inference frame equality test | Complete |
| Expense model | Linear/RF/GB comparison, chronological train/validation/test, MAE/RMSE/R², version/dataset metadata | `ml-service/train_models.py` | Synthetic training test | Complete methodology; no real production dataset/artifacts supplied |
| K-Means | Exactly four unique deterministic labels; distance not confidence | ML training/inference files | Repeat-training deterministic mapping test | Complete |
| Unusual-pattern detection | Aggregate monthly pattern, boolean/score/context; explicitly not fraud | `ml-service/main.py` | ML endpoint test | Complete |
| ML readiness | Process liveness separate from safely loadable artifacts | ML `/health/live`, `/health/ready`; Core readiness | Missing/unloadable/ready, contract, and synthetic-production-block tests | Complete; local demo artifacts ready, production eligibility false |
| Synthetic dataset | Deterministic, explicitly synthetic, multiple users, ≥6 months | `ml-service/generate_synthetic_demo.py`, artifact metadata, `DATA_PROVENANCE.md` | 12 users × 12 months; UI/health identify demo; production-block test | Complete; local integration only and never presented as real validation |
| Authentication | Password policy, normalized email, Argon2, issuer/audience/type/expiry JWT, JTI revocation | `backend/app/auth.py`, schemas/models | Auth, duplicate normalization, logout tests | Complete |
| Household invariant | Exactly one membership accepted; no arbitrary selection | `household_id()` in `backend/app/auth.py` | Auth/ownership suite | Complete for the supported single-household model |
| Ownership | Protected records scoped to authenticated household | All core routers | Broad cross-user account/transaction/budget/goal/liability/portfolio/report/recommendation/alert/risk/scenario/advisor/notification tests | Complete for exposed entity operations |
| AI mutations | Typed allowlist, validation, authorization, exact-action/user binding, expiry, single use, audit | `backend/app/schemas.py`, `routers/ai_actions.py` | Wrong-user, modified, expired, reused, success, and audit tests | Complete |
| BFF / CSRF | HttpOnly cookie, SameSite=Lax, same-origin unsafe-method check, proxy-aware origin handling, size cap | `app/api/core/[...path]/route.ts` | Real browser registration exposed and then verified the proxy-origin fix | Complete for same-origin deployment |
| Rate limiting | Proxy-aware identity key; no token logging | `backend/app/main.py` | Source audit and backend suite | Complete for one backend process only; intentionally no Redis |
| Errors/logging | Request IDs, structured failures, sanitized 500, no silent data fallback | `backend/app/main.py`, UI API states | Backend and Playwright checks | Complete for tested flows |
| Reports | Persisted authoritative immutable snapshots, `data_as_of`, methodology, assumptions, recommendations, disclaimer, localized HTML/CSV/print | Planning router and Reports UI | Snapshot immutability test and Playwright history check | Complete; PDF means browser Print/Save as PDF and is labeled honestly |
| Notifications | Settings vs delivery availability, ownership, SMTP dispatch, due frequency, duplicate prevention, cron secret | `backend/app/routers/notifications.py`, Next cron route | Dispatch secret/due/dedup tests and unconfigured SMTP test | Implemented / operational dependency: SMTP and scheduler required |
| Frontend authority | API financial screens use backend records; no local financial store or duplicate engine | `app/page.tsx`, `lib/api.ts`; `lib/financial-engine.ts` deleted | Source grep, build, and Playwright persistence/API assertions | Complete for authoritative screens |
| Frontend failure states | Honest ML/API failures; no fake fallback predictions or AI answers | Insights, advisor, report, portfolio, simulator UIs | Playwright verifies explicit ML-unavailable state | Substantially complete; a broader accessibility matrix remains future work |
| Language / RTL | First-launch choice, instant English/Arabic, document direction/language, localized currency/numbers/reports | `app/page.tsx`, report renderer | Playwright checks gate, RTL, Arabic navigation/profile, and EGP simulation | Complete for tested journey; some dynamic backend-generated English recommendation text is not server-translated |
| Educational project tools | No invented ranking/confidence | Projects UI | Final source/browser audit | Fake “match” percentages removed; now an explicitly unvalidated educational idea library with illustrative scenarios |
| Infrastructure config | PostgreSQL required, production secret validation, no production `create_all` | `backend/app/config.py`, `main.py`, Compose | Production config tests | Complete |
| Migration | Explicit complete 24-table baseline, no model-driven production migration | `backend/migrations/versions/0001_initial.py` | Fresh SQLite upgrade + `alembic check` | Complete definition; PostgreSQL execution not verified in this sandbox |
| Compose | Exactly postgres/backend/ml-service/frontend; healthchecks and readiness ordering | `docker-compose.yml` | Static audit | Defined / not runtime-verified because Docker is unavailable |
| Tests/build | Backend, ML, browser, migration, build, dependency audit | Test directories and scripts | 19 backend + 3 ML + 1 Playwright; build green; npm audit 0 | Complete for documented scope |

## Final audit conclusions

- No authoritative financial values are persisted in `localStorage` or `sessionStorage`. Only language and guidance-checklist preference remain local.
- `lib/financial-engine.ts` was removed after all imports were eliminated.
- Local integration artifacts are explicitly classified `synthetic-demo`, visibly labeled in the UI, and blocked in production. Missing or incompatible production artifacts remain an honest unavailable state.
- The remaining client calculators are clearly illustrative presentation tools. They do not replace the server summary, ML service, reports, portfolio, or simulation records.
- Docker and PostgreSQL runtime claims are intentionally withheld because this environment provides neither Docker nor a PostgreSQL server.
