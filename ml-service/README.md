# Smart Wealth Advisor ML Service

This service performs actual model inference for the core backend. It never supplies a statistical or canned fallback when artifacts are absent.

## Monthly feature contract v2

Each CSV row is one user-month. Required columns:

- identity/time: `user_id`, `month`
- monthly amounts in one household currency: `income`, `food`, `transport`, `shopping`, `bills`, `housing`, `health`, `entertainment`, `monthly_debt_payments`, `monthly_surplus`
- target: `total_expenses_next_month`

`feature_definitions.py` is imported by both training and inference and defines feature names, units, formulas, category columns, ratios, and contract version. The core backend sends one explicit current-calendar-month snapshot using normalized category codes. Outstanding debt and liquid account balances are not substituted for monthly debt payments or monthly surplus.

Engineered features:

- expense ratio = modeled category expenses / monthly income
- saving ratio = monthly surplus / monthly income
- debt-service ratio = required monthly debt payments / monthly income
- discretionary ratio = shopping + entertainment / monthly income

## Training

```bash
pip install -r requirements.txt
python train_models.py /path/to/real_monthly.csv --out models
```

The chronological split is approximately 60% train, 20% validation, and 20% final test by month. Linear Regression, Random Forest, and Gradient Boosting are selected using validation MAE only. The selected estimator is fitted on train + validation and evaluated once on the chronologically later test period. Metrics include MAE, RMSE, R², dataset hash/range/row/user counts, runtime versions, model version, contract version, and partition dates.

Artifacts:

- `expense_model.joblib`
- `anomaly_model.joblib`
- `behavior_model.joblib`
- `metrics.json`

The K-Means interpretation assigns four unique labels deterministically: Debt-heavy, Saver, High Spender, and Balanced. Distance to centroid is returned as distance—not confidence.

Isolation Forest operates on monthly category aggregates. Its output is labeled an **unusual monthly category-level spending pattern**, never fraud detection.

## Clearly labeled synthetic demonstration data

```bash
python generate_synthetic_demo.py --out synthetic_demo_monthly.csv --seed 42
python train_models.py synthetic_demo_monthly.csv --out demo-models --synthetic
```

The generator is deterministic, uses 12 synthetic users across 12 months, and contains no real personal information. Metrics from this data are demo/test metrics and must not be represented as real-world validation or production performance.

## Runtime and readiness

```bash
uvicorn main:app --host 0.0.0.0 --port 8001
```

- `GET /health/live`: process liveness
- `GET /health/ready`: attempts to load every artifact and validates its feature contract
- `POST /predict-expenses`
- `POST /check-expense`
- `POST /financial-profile`

Missing, corrupt, or contract-incompatible artifacts return HTTP 503. Runtime versions are pinned in `requirements.txt` and recorded in `metrics.json`.
