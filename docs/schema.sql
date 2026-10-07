-- Smart Wealth Advisor — PostgreSQL 16 reference schema (abridged but runnable)
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE TYPE member_role AS ENUM ('owner','member','advisor_viewer');
CREATE TYPE account_kind AS ENUM ('checking','savings','brokerage','retirement','property','crypto','other');
CREATE TYPE recommendation_status AS ENUM ('draft','active','accepted','dismissed','expired','superseded');
CREATE TYPE job_status AS ENUM ('queued','running','completed','failed','cancelled');

CREATE TABLE users (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), auth_subject text NOT NULL UNIQUE,
 email_ciphertext bytea, email_blind_index bytea UNIQUE, display_name_ciphertext bytea,
 locale varchar(10) NOT NULL DEFAULT 'en', created_at timestamptz NOT NULL DEFAULT now(),
 last_login_at timestamptz, deleted_at timestamptz
);
CREATE TABLE households (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), name text NOT NULL, base_currency char(3) NOT NULL,
 country_code char(2) NOT NULL, timezone text NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE household_members (
 household_id uuid REFERENCES households ON DELETE CASCADE, user_id uuid REFERENCES users ON DELETE CASCADE,
 role member_role NOT NULL, joined_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY(household_id,user_id)
);
CREATE TABLE user_settings (
 user_id uuid PRIMARY KEY REFERENCES users ON DELETE CASCADE, theme text NOT NULL DEFAULT 'system',
 preferences jsonb NOT NULL DEFAULT '{}', notification_preferences jsonb NOT NULL DEFAULT '{}',
 privacy_controls jsonb NOT NULL DEFAULT '{}', updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE consents (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid NOT NULL REFERENCES users,
 purpose text NOT NULL, policy_version text NOT NULL, granted boolean NOT NULL,
 occurred_at timestamptz NOT NULL DEFAULT now(), ip_hash bytea
);
CREATE TABLE institutions (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), provider_key text UNIQUE, name text NOT NULL, country_code char(2));
CREATE TABLE connections (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), household_id uuid NOT NULL REFERENCES households,
 institution_id uuid REFERENCES institutions, provider_item_ref_ciphertext bytea, status text NOT NULL,
 consent_expires_at timestamptz, last_synced_at timestamptz, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE accounts (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), household_id uuid NOT NULL REFERENCES households,
 connection_id uuid REFERENCES connections, kind account_kind NOT NULL, name text NOT NULL,
 currency char(3) NOT NULL, provider_account_ref_ciphertext bytea, balance numeric(20,6),
 balance_as_of timestamptz, included boolean NOT NULL DEFAULT true, metadata jsonb NOT NULL DEFAULT '{}',
 created_at timestamptz NOT NULL DEFAULT now(), archived_at timestamptz
);
CREATE INDEX accounts_household_idx ON accounts(household_id) WHERE archived_at IS NULL;
CREATE TABLE categories (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), household_id uuid REFERENCES households, parent_id uuid REFERENCES categories, name text NOT NULL, kind text NOT NULL);
CREATE TABLE transactions (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), household_id uuid NOT NULL REFERENCES households,
 account_id uuid NOT NULL REFERENCES accounts, provider_transaction_ref text, occurred_at timestamptz NOT NULL,
 posted_at timestamptz, description text NOT NULL, amount numeric(20,6) NOT NULL, currency char(3) NOT NULL,
 base_amount numeric(20,6) NOT NULL, base_currency char(3) NOT NULL, fx_rate numeric(20,10),
 category_id uuid REFERENCES categories, pending boolean NOT NULL DEFAULT false, metadata jsonb NOT NULL DEFAULT '{}',
 created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(account_id,provider_transaction_ref)
);
CREATE INDEX transactions_household_date_idx ON transactions(household_id,occurred_at DESC);
CREATE TABLE assets (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), household_id uuid NOT NULL REFERENCES households,
 type text NOT NULL, name text NOT NULL, currency char(3) NOT NULL, metadata jsonb NOT NULL DEFAULT '{}', created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE liabilities (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), household_id uuid NOT NULL REFERENCES households,
 type text NOT NULL, name text NOT NULL, currency char(3) NOT NULL, balance numeric(20,6) NOT NULL,
 interest_rate numeric(9,6), minimum_payment numeric(20,6), maturity_date date, metadata jsonb NOT NULL DEFAULT '{}'
);
CREATE TABLE valuations (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), household_id uuid NOT NULL REFERENCES households,
 subject_type text NOT NULL, subject_id uuid NOT NULL, value numeric(20,6) NOT NULL, currency char(3) NOT NULL,
 base_value numeric(20,6) NOT NULL, valued_at timestamptz NOT NULL, source text NOT NULL
);
CREATE INDEX valuations_subject_date_idx ON valuations(subject_type,subject_id,valued_at DESC);
CREATE TABLE goals (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), household_id uuid NOT NULL REFERENCES households,
 name text NOT NULL, type text NOT NULL, target_amount numeric(20,6) NOT NULL, currency char(3) NOT NULL,
 target_date date, priority smallint NOT NULL CHECK(priority BETWEEN 1 AND 5), flexibility jsonb NOT NULL DEFAULT '{}',
 status text NOT NULL DEFAULT 'active', created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE risk_assessments (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), household_id uuid NOT NULL REFERENCES households,
 tolerance numeric(5,2) NOT NULL, capacity numeric(5,2) NOT NULL, need numeric(5,2) NOT NULL,
 knowledge numeric(5,2) NOT NULL, resulting_risk numeric(5,2) NOT NULL, answers jsonb NOT NULL,
 methodology_version text NOT NULL, completed_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE financial_snapshots (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), household_id uuid NOT NULL REFERENCES households,
 as_of timestamptz NOT NULL, input_hash bytea NOT NULL, data_completeness numeric(5,2) NOT NULL,
 net_worth numeric(20,6), monthly_income numeric(20,6), monthly_expenses numeric(20,6),
 metrics jsonb NOT NULL, methodology_versions jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(household_id,as_of,input_hash)
);
CREATE TABLE portfolios (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), household_id uuid NOT NULL REFERENCES households, name text NOT NULL, strategy text, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE securities (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), isin text, symbol text, name text NOT NULL, asset_class text NOT NULL, currency char(3), metadata jsonb NOT NULL DEFAULT '{}');
CREATE TABLE positions (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), portfolio_id uuid NOT NULL REFERENCES portfolios,
 account_id uuid REFERENCES accounts, security_id uuid REFERENCES securities, quantity numeric(30,12) NOT NULL,
 market_value numeric(20,6), currency char(3) NOT NULL, as_of timestamptz NOT NULL
);
CREATE INDEX positions_portfolio_idx ON positions(portfolio_id,as_of DESC);
CREATE TABLE model_portfolios (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), name text NOT NULL, risk_level smallint NOT NULL CHECK(risk_level BETWEEN 1 AND 10),
 country_code char(2), currency char(3), expected_return_low numeric(9,6), expected_return_high numeric(9,6),
 expected_volatility numeric(9,6), methodology_version text NOT NULL, active boolean NOT NULL DEFAULT true
);
CREATE TABLE model_allocations (model_id uuid REFERENCES model_portfolios ON DELETE CASCADE, asset_class text NOT NULL, target_weight numeric(9,6) NOT NULL, min_weight numeric(9,6), max_weight numeric(9,6), PRIMARY KEY(model_id,asset_class));
CREATE TABLE scenarios (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), household_id uuid NOT NULL REFERENCES households,
 name text NOT NULL, baseline_snapshot_id uuid NOT NULL REFERENCES financial_snapshots,
 inputs jsonb NOT NULL, created_by uuid NOT NULL REFERENCES users, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE scenario_runs (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), scenario_id uuid NOT NULL REFERENCES scenarios,
 status job_status NOT NULL DEFAULT 'queued', engine_version text NOT NULL, random_seed bigint,
 assumptions jsonb NOT NULL, results jsonb, error_code text, started_at timestamptz, completed_at timestamptz
);
CREATE TABLE recommendations (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), household_id uuid NOT NULL REFERENCES households,
 snapshot_id uuid NOT NULL REFERENCES financial_snapshots, type text NOT NULL, status recommendation_status NOT NULL,
 priority numeric(8,4) NOT NULL, title text NOT NULL, structured_payload jsonb NOT NULL,
 methodology_version text NOT NULL, expires_at timestamptz, created_at timestamptz NOT NULL DEFAULT now(), decided_at timestamptz
);
CREATE INDEX recommendations_active_idx ON recommendations(household_id,priority DESC) WHERE status='active';
CREATE TABLE recommendation_evidence (recommendation_id uuid REFERENCES recommendations ON DELETE CASCADE, fact_key text NOT NULL, fact_value jsonb NOT NULL, source_ref text NOT NULL, PRIMARY KEY(recommendation_id,fact_key));
CREATE TABLE reports (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), household_id uuid NOT NULL REFERENCES households,
 snapshot_id uuid NOT NULL REFERENCES financial_snapshots, type text NOT NULL, status job_status NOT NULL DEFAULT 'queued',
 locale varchar(10) NOT NULL, assumptions jsonb NOT NULL, object_key text, content_hash bytea,
 created_by uuid NOT NULL REFERENCES users, created_at timestamptz NOT NULL DEFAULT now(), completed_at timestamptz
);
CREATE TABLE alerts (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), household_id uuid NOT NULL REFERENCES households, type text NOT NULL, severity text NOT NULL, payload jsonb NOT NULL, read_at timestamptz, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE audit_events (
 id uuid NOT NULL DEFAULT gen_random_uuid(), household_id uuid, actor_user_id uuid,
 action text NOT NULL, resource_type text NOT NULL, resource_id uuid, metadata jsonb NOT NULL DEFAULT '{}',
 occurred_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY(id,occurred_at)
) PARTITION BY RANGE (occurred_at);
CREATE TABLE audit_events_2026_q4 PARTITION OF audit_events FOR VALUES FROM ('2026-10-01') TO ('2027-01-01');

-- Enable and define household isolation in production after setting app.household_id per transaction.
ALTER TABLE accounts ENABLE ROW LEVEL SECURITY;
CREATE POLICY accounts_household_isolation ON accounts USING (household_id = current_setting('app.household_id', true)::uuid);
