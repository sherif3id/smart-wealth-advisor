# Smart Wealth Advisor — Product & Technical Blueprint

**Version:** 1.0 · **Date:** 5 October 2026 · **Status:** Build-ready

> **Product boundary:** Smart Wealth Advisor provides educational decision support, projections, and planning tools. It does not guarantee outcomes or replace a licensed investment, tax, or legal professional. Every forecast must show assumptions, fees, uncertainty, and material risks.

---

## 1. Executive Summary

Smart Wealth Advisor is a bilingual (English/Arabic), AI-assisted wealth-management platform that turns a household’s fragmented financial information into an understandable, actionable plan. It unifies net worth, cash flow, debt, goals, investments, protection, and retirement in one experience, then offers explainable recommendations and scenario simulations.

The product is aimed initially at digitally fluent mass-affluent users in MENA and international markets. Its differentiators are: whole-financial-life analysis; transparent recommendations; localized currency/RTL support; interactive “what-if” planning; and a premium interface that makes complex analysis approachable.

**Primary outcomes**
- Give users a reliable, current view of financial health.
- Translate goals into required contributions and feasible timelines.
- Protect the downside before optimizing investment returns.
- Recommend diversified portfolio models aligned with capacity and tolerance for risk.
- Make every recommendation traceable to user data, assumptions, and rules.

**North-star metric:** percentage of funded users whose plan is “on track” for their top goal. Supporting metrics: onboarding completion, linked-account rate, monthly planning sessions, recommendation acceptance, 90-day retention, goal funding rate, projection comprehension, and support/regulatory complaint rate.

---

## 2. Product Vision

**Vision:** Make high-quality, understandable wealth planning available to anyone, in their language, without hiding uncertainty.

**Personas**
1. **Emerging investor:** 25–35, positive cash flow, little investing experience; needs emergency-fund and automated-investing guidance.
2. **Mass-affluent planner:** 35–50, multiple accounts and goals; needs tax-aware allocation, retirement planning, and household coordination.
3. **Pre-retiree:** 50–65; needs sequence-risk, withdrawal, healthcare, protection, and retirement-readiness analysis.
4. **Advisor/operations user:** reviews escalations, recommendation evidence, suitability, and data-quality issues under strict role controls.

**Principles**
- Safety before yield: liquidity, expensive debt, and protection precede risk assets.
- Explain before asking: rationale, assumptions, risk, and alternatives accompany each action.
- Plans, not predictions: use ranges and scenarios rather than false precision.
- Human control: users approve changes; AI never executes transactions without explicit consent.
- Local by design: locale, currency, tax caveats, Islamic-finance preference, and RTL are first-class.

---

## 3. Features List

### 3.1 Foundation
- Email/passkey/OAuth authentication, optional biometric platform authentication, TOTP/SMS 2FA, trusted devices, sessions, recovery codes.
- Household profile: age, dependents, residency, tax country, currency, income, expenses, assets, liabilities, insurance, preferences.
- Account aggregation through region-appropriate open-banking providers; manual entry and CSV import.
- Double-entry-style transaction classification, recurring transaction detection, budgets, rules, split transactions, merchant normalization.
- Net-worth history, monthly cash flow, savings rate, debt ratios, emergency runway, and wealth/financial-health scores.

### 3.2 Planning and advice
- Goals with amount, currency, date, priority, flexibility, inflation handling, funding accounts, and monthly plan.
- Emergency-fund target based on essential spend, income stability, dependents, insurance, and liquidity.
- Debt optimizer comparing avalanche, snowball, refinancing, and invest-versus-paydown scenarios.
- Retirement/FIRE engine with accumulation and decumulation, inflation, fees, taxes, pension/social-security estimates, and Monte Carlo ranges.
- Five model strategies: Conservative, Balanced, Growth, Aggressive, Ultra-Aggressive. Each shows allocation, expected return range, volatility, drawdown range, liquidity, diversification, fees, and suitability rationale.
- Rebalancing using tolerance bands, cash-flow-first trades, tax-lot awareness, and user-defined constraints.
- AI advisor with grounded access to the user’s computed plan, citations to plan facts, suggested prompts, voice input/output, and human escalation.

### 3.3 Investment universe
For stocks, ETFs, index funds, bonds, property, REITs, precious metals, commodities, savings, money-market funds, businesses/franchises/startups/private equity, crypto, dividend portfolios, rentals, digital businesses/e-commerce/SaaS, and P2P lending, the comparison view provides:
- Risk category and principal-loss modes
- Expected nominal/real return **range**, data date, and methodology
- Historical/forward-looking volatility and drawdown caveat
- Liquidity/lockup, minimum, fees, taxes caveat, complexity
- Advantages, disadvantages, suitable horizon, and concentration/correlation
- Recommended allocation range only when suitable; otherwise a reason for exclusion
- Base, optimistic, adverse, and liquidity-stress scenarios

### 3.4 Calculators and simulation
Compound interest, retirement, FIRE, mortgage, amortizing loan, portfolio growth, passive income, ROI, savings rate, net worth, and financial freedom. Scenario variables include starting capital, recurring investment, return/volatility, market shock, inflation, salary/expense growth, new debt, retirement date, withdrawal rate, and property purchase.

### 3.5 Reports, alerts, and exports
Financial Health, Wealth Analysis, Risk Assessment, Retirement Readiness, Investment Proposal, and Portfolio Analysis. Export accessible PDF, XLSX, CSV, and JSON. Reports contain snapshot date, data completeness, assumptions, conflicts, risk disclosures, and methodology version. Alerts cover goal drift, excess cash, large transaction, overspending, debt-rate change, allocation drift, concentration, data staleness, and upcoming obligations.

### 3.6 Settings and access
Language, region, currency, number/date format, theme, investment exclusions, ESG/Sharia preference, notification channels/quiet hours, consent and privacy controls, export/delete account, security activity, sessions, passkeys, and 2FA.

**Out of scope for v1:** discretionary trade execution, custody, lending decisions, definitive tax filing, legal advice, and unreviewed autonomous agents.

---

## 4. User Flows

### 4.1 First-run plan
1. Create account → verify contact → enable 2FA/passkey.
2. Select language, country, base currency, and regulatory consent.
3. Enter household and employment basics.
4. Link accounts or use guided manual entry; show data coverage.
5. Add goals and rank priorities.
6. Complete risk questionnaire: willingness, capacity, need, knowledge, loss reaction, horizon, liquidity.
7. Review normalized financial snapshot and correct classifications.
8. Engine computes foundation actions, goal feasibility, and suitable model strategies.
9. User sees a one-page plan: “protect, stabilize, grow,” with assumptions and alternatives.
10. User accepts, edits, dismisses, or asks the AI advisor; each decision is recorded.

### 4.2 Scenario flow
Dashboard → Simulator → choose baseline snapshot → modify variables → run deterministic projection immediately → request Monte Carlo run → compare baseline and scenario → inspect assumptions and percentile bands → save named scenario → attach to a goal/report.

### 4.3 Recommendation flow
Trigger/data change → rule engine checks eligibility and safety constraints → quant service evaluates impact → recommendation service ranks options → LLM creates plain-language explanation from structured facts → policy service validates language/disclosures → user reviews rationale, risk, cost, and alternatives → explicit action/dismissal → audit event.

### 4.4 Report flow
Reports → select report/date/household members → preview data coverage and assumptions → generate immutable snapshot asynchronously → notification → view accessible HTML → export PDF/XLSX → record download audit event.

### 4.5 Critical edge states
Stale feeds, missing income, conflicting currencies, negative cash flow, high-interest debt, inadequate liquidity, short horizon, extreme risk answers, unsupported jurisdiction, market-data outage, projection timeout, and suspected account takeover each produce a safe, actionable state—not a blank dashboard.

---

## 5. Database Design

PostgreSQL 16 is the system of record; UUIDv7 identifiers, `timestamptz`, numeric monetary values (never float), ISO-4217 currency, soft deletion only where legally appropriate, and row-level tenant boundaries.

**Core domains**
- Identity: `users`, `households`, `household_members`, `user_settings`, `consents`, `sessions`, `mfa_methods`.
- Finance: `institutions`, `connections`, `accounts`, `transactions`, `categories`, `assets`, `liabilities`, `valuations`, `exchange_rates`.
- Planning: `goals`, `goal_contributions`, `risk_assessments`, `financial_snapshots`, `budgets`, `budget_lines`.
- Investing: `securities`, `prices`, `portfolios`, `positions`, `tax_lots`, `model_portfolios`, `model_allocations`, `rebalancing_runs`.
- Advice: `recommendations`, `recommendation_evidence`, `scenarios`, `scenario_runs`, `ai_threads`, `ai_messages`, `alerts`.
- Governance: `reports`, `export_jobs`, `audit_events`, `data_access_events`, `deletion_requests`, `methodology_versions`.

**Key modeling rules**
- Transactions and valuations retain original and base-currency amounts plus FX-rate source/time.
- A `financial_snapshot` is immutable and references input versions; calculations are reproducible.
- Recommendations reference snapshot, methodology, evidence facts, assumptions, confidence, expiration, and user disposition.
- Sensitive PII fields use application-level envelope encryption; searchable blind indexes are separate.
- Large audit/event tables are monthly partitioned. Price histories use TimescaleDB or date partitions.
- Index every foreign key plus `(household_id, occurred_at)`, transaction deduplication keys, active recommendation status, and report job status.

A runnable schema is supplied in `docs/schema.sql`.

---

## 6. API Design

**Style:** REST/JSON for client operations, OpenAPI 3.1 contract, webhooks for providers, SSE for AI/report progress. Version at `/v1`; idempotency keys required for mutations/jobs; cursor pagination; RFC 9457 problem details.

**Representative endpoints**
- `POST /v1/auth/passkeys/register`, `POST /v1/auth/mfa/challenge`
- `GET/PATCH /v1/profile`, `GET/PATCH /v1/settings`, `POST /v1/consents`
- `POST /v1/connections`, `POST /v1/connections/{id}/sync`, `GET /v1/accounts`
- `GET/POST /v1/transactions`, `PATCH /v1/transactions/{id}`, `POST /v1/imports`
- `GET /v1/dashboard?asOf=`, `GET /v1/net-worth`, `GET /v1/cash-flow`
- `GET/POST/PATCH /v1/goals`, `POST /v1/goals/{id}/forecast`
- `POST /v1/risk-assessments`, `GET /v1/portfolio/models`, `POST /v1/portfolios/proposals`
- `POST /v1/scenarios`, `POST /v1/scenarios/{id}/runs`, `GET /v1/scenario-runs/{id}`
- `GET /v1/recommendations`, `POST /v1/recommendations/{id}/disposition`
- `POST /v1/advisor/threads`, `POST /v1/advisor/threads/{id}/messages`, `GET .../stream`
- `POST /v1/reports`, `GET /v1/reports/{id}`, `POST /v1/reports/{id}/exports`
- `GET/PATCH /v1/alerts`, `GET /v1/security/activity`, `POST /v1/privacy/export`, `DELETE /v1/profile`

**Example recommendation response**
```json
{
  "id": "rec_01…",
  "type": "MOVE_EXCESS_CASH",
  "status": "active",
  "title": "Put $18,000 of idle cash to work",
  "impact": {"annualInterestRange": [630, 810], "currency": "USD"},
  "rationale": ["Emergency fund remains at 6.8 months", "Account yield is 0.1%"],
  "assumptions": [{"key": "apy", "value": 0.045, "asOf": "2026-10-05"}],
  "risks": ["Rates can change", "Confirm deposit insurance limits"],
  "alternatives": ["Money-market fund", "Short Treasury ladder"],
  "methodologyVersion": "cash-v3.2",
  "disclaimer": "Educational estimate; not a guaranteed return."
}
```

**Controls:** JWT access tokens ≤10 minutes; rotated refresh session or Clerk/Auth.js session; household-scoped authorization; rate limits by risk; signed provider webhooks with replay prevention; `ETag` optimistic concurrency; no raw provider tokens returned to clients.

---

## 7. UI Design

### 7.1 Information architecture
Desktop sidebar: Dashboard, Portfolio, Goals, Simulator, Calculators, Reports; bottom: AI Advisor, Settings, Profile. Mobile uses bottom navigation for the top four tasks and an overflow sheet.

### 7.2 Visual system
- Calm, premium, evidence-led aesthetic; navy text, cobalt action, teal positive, amber warning, coral negative.
- 4/8px spacing system; 12–14px card radius; restrained shadows; generous white space.
- Typography: DM Sans/Inter for Latin and Noto Sans Arabic for Arabic; tabular numerals for finance.
- Never rely on red/green alone. Pair color with icon, label, and sign.
- Charts include accessible summaries, tooltips, benchmark labels, date range, and “data as of.”
- Dark/light/system themes use semantic tokens, not hard-coded component colors.

### 7.3 Responsive wireframes
**Desktop:** 246px persistent navigation; 66px utility bar; four KPI cards; 2/3 performance + 1/3 allocation; lower goals/insights/cash-flow row.

**Tablet:** collapsible rail; two KPI columns; main charts stack when needed.

**Mobile:** summary first, horizontally scrollable time controls, full-width cards, sticky primary action, bottom-sheet filters, 44px minimum targets.

### 7.4 Accessibility and localization
WCAG 2.2 AA; visible focus; keyboard-complete; semantic headings/landmarks; reduced motion; 200% zoom; screen-reader chart tables; no hover-only actions. `dir` switches at document level, icons with directionality mirror selectively, and user-entered content uses `dir=auto`. Format all numbers through `Intl`; preserve original instrument symbols; translate meaning rather than concatenate fragments.

The implemented prototype follows these guidelines in `app/`.

---

## 8. Full Architecture

```text
Next.js Web / Mobile PWA
        │ HTTPS / SSE
CloudFront/Front Door + WAF + API Gateway
        │
NestJS API (modular monolith initially)
 ├─ Identity & Household    ├─ Accounts & Transactions
 ├─ Goals & Budgets         ├─ Portfolio & Market Data
 ├─ Advice Orchestrator     ├─ Reports & Notifications
 └─ Audit & Privacy
        │ async commands/events
     SQS/Service Bus ── Worker fleet
        │                 ├─ Account sync/categorization
        │                 ├─ Quant/Monte Carlo service (Python)
        │                 ├─ Report renderer
        │                 └─ Alert evaluation
        ├─ PostgreSQL (HA + read replica)
        ├─ Redis (cache, locks, rate limits)
        ├─ Object storage (encrypted reports/imports)
        ├─ Search/vector index (approved knowledge only)
        └─ Observability (OpenTelemetry → logs/metrics/traces)
External: Open banking, market data, FX, email/SMS/push, KMS, LLM gateway
```

**Frontend structure**
```text
app/[locale]/(auth|onboarding|product)/...
features/{dashboard,portfolio,goals,simulator,calculators,reports,advisor}
components/{ui,charts,forms,disclosure}
lib/{api,auth,i18n,money,analytics}
```
Use React Server Components for read-heavy pages, client islands for charts/forms, TanStack Query where client caching is needed, Zod at boundaries, and generated API types.

**Backend structure**
```text
apps/api, apps/worker, services/quant
libs/{domain,db,events,security,observability,contracts}
```
NestJS modules expose application services; domain logic does not depend on controllers or ORM. Use an outbox table for reliable event publication. Start as a modular monolith; extract sync, quant, AI, and report workloads only when scaling data demonstrates need.

**Deployment:** Vercel for Next.js plus AWS (ECS Fargate, RDS PostgreSQL Multi-AZ, ElastiCache, S3, SQS, KMS, Secrets Manager, CloudFront/WAF) or equivalent Azure stack. Separate accounts/subscriptions for dev/stage/prod. Terraform, immutable containers, GitHub Actions with OIDC, migration job, canary/blue-green release, automated rollback. RPO ≤15 minutes, RTO ≤60 minutes; quarterly recovery test.

**Scaling:** CDN and RSC caching for safe public assets; Redis for dashboard aggregates; precomputed daily snapshots; asynchronous scenarios/reports; connection pools; partition high-volume tables; read replicas; queue backpressure and per-provider circuit breakers. SLO: 99.9% monthly API availability, dashboard p95 <1.5s warm, mutation p95 <500ms excluding jobs.

---

## 9. Security Design

- **Identity:** Auth.js or Clerk; OIDC/OAuth 2.1 with PKCE; WebAuthn/passkeys; optional TOTP; step-up auth for exports, bank linking, security changes, and deletion.
- **Authorization:** deny-by-default RBAC plus household/resource attributes. Separate end-user, support, compliance, advisor, and admin roles. Support access is time-boxed, reason-coded, and audited.
- **Encryption:** TLS 1.3 in transit; AES-256 at rest; per-environment KMS; envelope encryption for PII/provider credentials; key rotation; secrets in managed vault only.
- **Session:** Secure/HttpOnly/SameSite cookies, short access lifetime, rotation/reuse detection, device list, remote revocation, CSRF protection, strict CSP and Trusted Types.
- **Application:** OWASP ASVS L2 baseline; schema validation; parameterized SQL; output encoding; SSRF egress allowlist; malware scan imports; formula-injection-safe CSV/XLSX exports.
- **Data/privacy:** minimization, purpose-limited consent, retention schedule, DSAR export/delete, regional residency when required, field masking, no financial PII in analytics or LLM logs.
- **AI:** private model endpoint/zero-retention contract; prompt-injection isolation; tools use typed allowlists; retrieval only from approved sources; structured output validation; policy classifier; no autonomous transaction execution; full evidence/audit chain.
- **Operations:** SAST, dependency/container/IaC/secret scans; annual penetration test; SIEM alerts; anomaly detection; on-call incident plan; vendor reviews; backups are encrypted and restore-tested.
- **Compliance readiness:** GDPR/data protection, SOC 2 controls, PCI scope avoidance, financial-promotion/suitability review per launch jurisdiction. Legal counsel confirms whether product behavior constitutes regulated advice.

---

## 10. AI Recommendation Engine Logic

### 10.1 Hybrid design
The engine is not an unconstrained chatbot. Deterministic services compute facts and suitability; the LLM explains approved structured results.

```text
Ingest → normalize → quality score → immutable snapshot
→ safety gates → goal math → risk profile → candidate actions
→ constraint/suitability filter → quantify impact → rank
→ explanation generation → policy validation → user presentation
```

### 10.2 Priority waterfall
1. Resolve data-quality blockers and immediate negative cash flow.
2. Maintain near-term bill liquidity.
3. Establish emergency reserves (default 3–9 months, personalized).
4. Capture employer match or equivalent high-confidence benefit.
5. Address toxic/high-interest debt and arrears.
6. Close critical insurance/protection gaps.
7. Fund near-term goals in capital-preservation assets.
8. Allocate long-term surplus to a suitable diversified portfolio.
9. Improve tax efficiency where jurisdiction support is reviewed.
10. Rebalance/optimize costs and estate/asset-protection prompts.

### 10.3 Ranking
Each candidate receives normalized scores for expected goal impact, urgency, certainty, risk reduction, liquidity fit, reversibility, cost/tax burden, behavioral effort, and user preference. Hard constraints can veto any candidate. Store score decomposition so ranking is auditable.

### 10.4 Wealth and health scores
Scores are diagnostic—not credit scores. Example health weights: cash flow 20%, reserves 15%, debt 15%, goal funding 15%, retirement 15%, diversification 10%, protection 10%. Missing inputs reduce confidence rather than being silently treated as healthy. UI displays component score, trend, confidence, and “how to improve.”

### 10.5 LLM contract
Input contains only minimized structured facts, approved recommendation payloads, locale, and disclosure policy. Output schema: summary, rationale bullets, assumptions, risks, alternatives, next steps, citations to internal fact IDs, and disclaimer. Reject output containing guarantees, invented rates, unapproved products, or unsupported tax/legal directives.

---

## 11. Investment Analysis Logic

### 11.1 Capital-market assumptions
Versioned by currency/region and reviewed by an investment committee. For each asset class store arithmetic/geometric nominal return range, volatility, correlations, inflation sensitivity, fees, liquidity, and confidence. Show real and nominal values where useful. Never infer expected return solely from recent performance.

### 11.2 Risk profile
Compute four dimensions independently:
- **Tolerance:** psychological willingness to accept loss.
- **Capacity:** income stability, reserves, debt, dependents, insurance, and horizon.
- **Need:** return required to meet goals.
- **Knowledge/experience:** complexity suitability.

Final portfolio risk cannot exceed capacity, regardless of stated willingness. Short-horizon goal assets are bucketed separately.

### 11.3 Portfolio construction
- Strategic asset allocation uses constrained mean-variance or resampled optimization, anchored by robust model portfolios to reduce estimation error.
- Constraints: min/max by asset class, liquidity floor, concentration cap, currency exposure, user exclusions, complexity, jurisdiction, and product availability.
- Use low-cost diversified instruments as default implementation; alternative/illiquid/speculative assets receive strict caps.
- Score diversification from effective number of holdings, asset-class balance, factor/sector/country/currency concentration, and correlations—not holding count alone.

### 11.4 Projections and scenarios
- Deterministic calculator: monthly compounding, contributions at selected timing, fees and inflation explicitly included.
- Monte Carlo: correlated monthly returns, fat-tail option, salary/inflation paths, taxes/fees, retirement withdrawals, and sequence risk. At least 10,000 runs for reports; fixed seed stored for reproducibility.
- Output P10/P50/P90 paths and probability of sustaining each goal, never a single promised endpoint.
- Stress tests include equity −20%/−35%, rate +200 bps, inflation 6%, property decline, income interruption, FX shock, and combined scenarios.

### 11.5 Rebalancing
Trigger when an asset breaches absolute/relative bands or plan risk materially changes. Prefer new cash/dividends, then tax-efficient sales. Consider transaction cost, capital gains, wash-sale/local rules, minimum trades, and restricted assets. Recommend no action when expected benefit is below cost.

### 11.6 Scenario assumptions shown to user
Return basis/date, inflation, contribution timing, salary growth, fees, tax treatment, FX, volatility model, rebalance frequency, and excluded risks. Each investment card states that losses, including loss of principal, are possible.

---

## 12. Dashboard Design

**Top layer:** greeting/data freshness, primary “Ask advisor” action, net worth, monthly cash flow, investment return, Wealth Score.

**Analysis layer:** portfolio performance with baseline/benchmark and date range; asset-allocation donut with value and percentages; goal funding and forecast status.

**Action layer:** maximum three prioritized AI insights, each showing impact/rationale; cash-flow composition and savings rate; alerts and upcoming obligations.

**Interactions:** range filters; account/household filters; chart detail drawer; hide balances; drag-free consistent layout; quick add; PDF/Excel export. Every metric has definition, source, as-of time, and drill-down. Empty states explain the benefit and one next step. Stale/partial data is prominently labeled.

The included working prototype implements Dashboard, Portfolio, Goals, Simulator, Calculators, Reports, AI drawer, theme toggle, Arabic/RTL toggle, responsive layouts, and educational disclosures.

---

## 13. Complete Development Roadmap

### Phase 0 — Discovery and governance (Weeks 1–3)
Jurisdiction/legal classification, user research, data-provider evaluation, threat model, design system, analytics plan, capital-market-assumption governance. **Exit:** approved scope and regulatory/product risk register.

### Phase 1 — Foundation MVP (Weeks 4–10)
Identity, 2FA/passkeys, household profile, manual accounts/assets/debts, transaction import, localization/RTL, settings, net worth/cash flow, audit events, CI/CD/observability. **Exit:** internal alpha; ASVS baseline and accessibility review.

### Phase 2 — Planning MVP (Weeks 11–17)
Goals, budgets, risk assessment, emergency/debt logic, deterministic calculators, model portfolios, recommendation cards, dashboard, PDF health report. **Exit:** closed beta; calculation golden tests signed off.

### Phase 3 — Connected wealth (Weeks 18–24)
Open banking, categorization, market data/prices, positions, alerts, rebalancing analysis, full report suite, XLSX export. **Exit:** provider failover and reconciliation tests; penetration test.

### Phase 4 — Intelligent advisor (Weeks 25–30)
Grounded AI chat, bilingual explanations, voice, scenario jobs, Monte Carlo, evidence/policy validation, advisor escalation. **Exit:** red-team benchmark, hallucination/guarantee thresholds, model-risk approval.

### Phase 5 — Launch and scale (Weeks 31–36)
Billing, premium entitlements, support console, privacy automation, performance tuning, DR test, app-store/PWA polish, launch-market compliance. Gradual 1%→10%→50%→100% rollout.

**Team:** product lead, engineering manager/architect, 4 frontend, 5 backend, 2 data/quant, 1 ML, 2 product designers, 2 QA/SDET, DevSecOps, security/compliance, investment/financial-planning reviewer, Arabic localization QA.

**Testing strategy**
- Unit/property-based tests for money math, FX, amortization, allocation, and constraints.
- Golden datasets independently calculated in spreadsheets/R/Python.
- Contract tests against OpenAPI and provider sandboxes; migration and idempotency tests.
- Integration/E2E for onboarding, sync, goal, scenario, report, consent, deletion, and account takeover.
- Visual regression across themes, RTL, breakpoints; axe and manual screen-reader/keyboard tests.
- Load/soak/chaos, queue backpressure, restore/DR, security DAST/fuzzing/penetration.
- AI evaluation: factual grounding, citation accuracy, numerical consistency, refusal, fairness by language/persona, prompt injection, and prohibited guarantee language.

---

## 14. Monetization Strategy

**Free:** manual accounts, dashboard, budgets, basic goals/calculators, educational library, limited scenarios.

**Plus (individual):** connected accounts, unlimited goals/scenarios, smart alerts, portfolio analysis, AI advisor quota, PDF/XLSX exports.

**Premium (household):** multi-member planning, advanced retirement/Monte Carlo, tax-aware insights where supported, voice advisor, priority support, report history.

**B2B2C:** white-label employer/benefits, bank, broker, and registered-advisor editions with tenant branding, SSO, advisor console, policy controls, and per-seat/active-household pricing.

Avoid incentives that bias recommendations. If referral revenue is ever introduced, label compensation clearly, include non-paid alternatives, separate commercial ranking from suitability, and obtain compliance approval. Track contribution margin after provider, market-data, AI, support, and report-rendering costs.

---

## 15. Future Enhancements

- Licensed-advisor collaboration, secure document vault, household permissions, and e-signature.
- Region-reviewed tax-lot harvesting, pension/benefit optimization, charitable giving, estate-planning checklists.
- Sharia-screened universes and zakat calculator reviewed by qualified boards.
- Small-business cash-flow and founder equity planning.
- Multi-currency goal hedging and expatriate planning.
- Consent-based brokerage execution with dual confirmation and best-execution controls.
- On-device receipt extraction and privacy-preserving categorization.
- Personalized behavioral coaching experiments with opt-out and fairness monitoring.
- Model marketplace only after governance, benchmark, fee, and conflict standards are established.

---

### Product disclaimer
All recommendations and projections are educational and depend on the accuracy of user data and stated assumptions. Markets, rates, inflation, taxes, fees, and personal circumstances can change. Investment values can fall as well as rise, and users may lose principal. The product must never present an estimate as guaranteed performance.
