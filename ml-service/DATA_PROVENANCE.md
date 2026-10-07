# ML data provenance and deployment policy

## Production rule

Smart Wealth Advisor does not treat an arbitrary internet dataset as production validation for a user's personal finances. Production artifacts must be trained from a reviewed dataset whose currency, population, time period, category mapping, consent/license, and monthly feature semantics match `monthly-financial-v2`.

Artifacts contain:

- `dataset_classification`: `real-user-provided` or `synthetic-demo`
- `production_eligible`: boolean
- feature-contract and model versions
- dataset hash and evaluation metadata in `metrics.json`

The ML service refuses `synthetic-demo` artifacts whenever `APP_ENV=production`. In development they are also refused unless `ML_ALLOW_SYNTHETIC_DEMO=true` is explicitly set.

## Public sources reviewed

- U.S. Bureau of Labor Statistics Consumer Expenditure public-use microdata: a credible public source for expenditure research, but its survey population, coding, reporting periods, and USD context are not automatically equivalent to Smart Wealth Advisor users or the seven application categories.
- PKDD'99 Czech financial dataset: real anonymized historical bank activity, but old CZK banking transaction codes do not provide the application's exact monthly category/debt-service/next-month-target contract, and redistribution/licensing must be verified before use.
- Public personal-finance datasets commonly found on Kaggle: many are explicitly synthetic. They can be useful for demonstrations but are not real-world validation.

No public source is silently downloaded or represented as a validated production model.

## Included demo dataset

`generate_synthetic_demo.py` deterministically creates 12 explicitly synthetic users across 12 months. It exists only to:

- verify the complete training/inference integration;
- exercise artifact compatibility and UI states;
- support reproducible tests and demonstrations.

Any UI response from those artifacts must show **Synthetic demo model** and must not be presented as a production forecast.

## Promoting real artifacts

1. Prepare one row per user-month with all fields documented in `feature_definitions.py`.
2. Confirm lawful processing, de-identification, currency consistency, category mapping, and at least eight chronological months.
3. Run data-quality checks and document population/time-period limitations.
4. Train without `--synthetic`.
5. Review chronological validation and untouched test MAE/RMSE/R², cluster stability, and unusual-pattern behavior.
6. Deploy the complete mutually compatible artifact set and `metrics.json`.
7. Keep monitoring drift and retrain under a new model version when the data distribution changes.
