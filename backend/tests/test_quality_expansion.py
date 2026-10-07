from datetime import date

from app.routers import notifications


def test_risk_boundaries_and_capacity_cap(client, headers):
    keys = ['loss_reaction', 'return_preference', 'experience', 'horizon', 'liquidity', 'income_stability']

    low = client.post('/risk-assessments', headers=headers, json={'answers': {key: 1 for key in keys}})
    assert low.status_code == 201
    assert low.json()['score'] == 0
    assert low.json()['category'] == 'Conservative'

    capped_answers = {key: 5 for key in keys}
    for key in keys[3:]:
        capped_answers[key] = 1
    capped = client.post('/risk-assessments', headers=headers, json={'answers': capped_answers})
    assert capped.status_code == 201
    assert capped.json()['score'] == 0
    assert capped.json()['category'] == 'Conservative'

    high = client.post('/risk-assessments', headers=headers, json={'answers': {key: 5 for key in keys}})
    assert high.status_code == 201
    assert high.json()['score'] == 100
    assert high.json()['category'] == 'Aggressive'

    invalid = client.post('/risk-assessments', headers=headers, json={'answers': {key: 3 for key in keys[:-1]}})
    assert invalid.status_code == 422
    assert invalid.json()['error']['code'] == 'INVALID_RISK_ANSWERS'


def test_recommendations_are_ranked_deduplicated_and_safety_first(client, headers):
    today = str(date.today())
    assert client.post('/transactions', headers=headers, json={
        'kind': 'income', 'amount': 1000, 'currency': 'USD', 'occurred_on': today,
        'description': 'Income', 'category': 'Salary'
    }).status_code == 201
    assert client.post('/transactions', headers=headers, json={
        'kind': 'expense', 'amount': 950, 'currency': 'USD', 'occurred_on': today,
        'description': 'Food', 'category': 'Food'
    }).status_code == 201
    assert client.post('/liabilities', headers=headers, json={
        'name': 'High service loan', 'kind': 'loan', 'balance': 5000,
        'monthly_payment': 500, 'interest_rate': 10, 'currency': 'USD'
    }).status_code == 201

    first = client.post('/recommendations/refresh', headers=headers)
    assert first.status_code == 200
    items = first.json()
    assert items
    assert [item['priority'] for item in items] == sorted(item['priority'] for item in items)
    types = [item['type'] for item in items]
    assert len(types) == len(set(types))
    assert 'debt' in types and 'reserves' in types and 'cash_flow' in types
    assert 'investment_readiness' not in types
    assert all(1 <= item['priority'] <= 4 for item in items)
    assert all(item['methodology_version'] == 'recommendations-v2' for item in items)

    second = client.post('/recommendations/refresh', headers=headers)
    assert second.status_code == 200
    active = client.get('/recommendations', headers=headers).json()
    assert len(active) == len(second.json())
    assert len({item['type'] for item in active}) == len(active)


def test_reports_are_authoritative_immutable_snapshots(client, headers):
    today = str(date.today())
    assert client.post('/transactions', headers=headers, json={
        'kind': 'income', 'amount': 5000, 'currency': 'USD', 'occurred_on': today,
        'description': 'Salary', 'category': 'Salary'
    }).status_code == 201
    assert client.post('/recommendations/refresh', headers=headers).status_code == 200
    created = client.post('/reports', headers=headers, json={'kind': 'monthly', 'locale': 'en'})
    assert created.status_code == 201
    report = created.json()
    assert report['data']['summary']['total_income'] == '5000.00'
    assert report['data']['data_as_of']
    assert report['data']['methodology']['version']
    assert report['data']['assumptions']

    assert client.post('/transactions', headers=headers, json={
        'kind': 'income', 'amount': 1000, 'currency': 'USD', 'occurred_on': today,
        'description': 'Later income', 'category': 'Salary'
    }).status_code == 201
    current = client.get('/financial-summary', headers=headers).json()
    assert float(current['total_income']) == 6000.00
    persisted = client.get(f"/reports/{report['id']}", headers=headers).json()
    assert persisted['snapshot']['summary']['total_income'] == '5000.00'


def test_monte_carlo_is_deterministic_ordered_and_bounded(client, headers):
    payload = {
        'initial_capital': 10000, 'monthly_contribution': 500, 'horizon_years': 10,
        'expected_return': 0.06, 'volatility': 0.12, 'inflation': 0.025,
        'simulations': 1000, 'seed': 73, 'goal_amount': 100000
    }
    first = client.post('/scenarios/monte-carlo', headers=headers, json=payload)
    second = client.post('/scenarios/monte-carlo', headers=headers, json=payload)
    assert first.status_code == second.status_code == 201
    for key in ('p10', 'p50', 'p90', 'probability_of_goal', 'probability_of_shortfall'):
        assert first.json()[key] == second.json()[key]
    result = first.json()
    assert 0 <= result['p10'] <= result['p50'] <= result['p90']
    assert 0 <= result['probability_of_goal'] <= 100
    assert 0 <= result['probability_of_shortfall'] <= 100
    assert round(result['probability_of_goal'] + result['probability_of_shortfall'], 8) == 100
    assert 'not a guarantee' in result['assumptions']['classification'].lower()

    invalid = client.post('/scenarios/monte-carlo', headers=headers, json={**payload, 'simulations': 10})
    assert invalid.status_code == 422


def test_notification_dispatch_secret_frequency_and_duplicate_prevention(client, headers, monkeypatch):
    assert client.put('/notifications', headers=headers, json={
        'email': 'alerts@example.com', 'frequency': 'daily', 'enabled': True, 'locale': 'en'
    }).status_code == 200
    assert client.post('/notifications/dispatch', headers={'x-cron-secret': 'wrong'}).status_code == 401

    delivered = []
    monkeypatch.setattr(notifications.settings, 'cron_secret', 'cron-test-secret')
    monkeypatch.setattr(notifications, 'deliver', lambda to, locale, summary: delivered.append((to, locale)))
    first = client.post('/notifications/dispatch', headers={'x-cron-secret': 'cron-test-secret'})
    assert first.status_code == 200
    assert first.json()['sent'] == 1 and first.json()['delivered'] is True
    assert delivered == [('alerts@example.com', 'en')]

    second = client.post('/notifications/dispatch', headers={'x-cron-secret': 'cron-test-secret'})
    assert second.status_code == 200
    assert second.json()['sent'] == 0
    assert second.json()['skipped_not_due'] == 1
    assert len(delivered) == 1


def test_production_configuration_rejects_sqlite_weak_secrets_and_create_all():
    import pytest
    from pydantic import ValidationError
    from app.config import Settings

    with pytest.raises(ValidationError):
        Settings(app_env='production', database_url='sqlite:///unsafe.db', jwt_secret='x' * 40)
    with pytest.raises(ValidationError):
        Settings(app_env='production', database_url='postgresql+psycopg://u:p@db/app', jwt_secret='weak')
    with pytest.raises(ValidationError):
        Settings(app_env='production', database_url='postgresql+psycopg://u:p@db/app', jwt_secret='x' * 40, auto_create_tables=True)


def test_liveness_and_readiness_contract(client, monkeypatch):
    from app import main

    live = client.get('/health/live')
    assert live.status_code == 200
    assert live.json()['service'] is True

    class MLResponse:
        status_code = 200
        @staticmethod
        def json():
            return {'ready': False, 'models': {'expense': False}}

    monkeypatch.setattr(main.httpx, 'get', lambda *args, **kwargs: MLResponse())
    ready = client.get('/health/ready')
    assert ready.status_code == 200
    body = ready.json()
    assert body['database']['ready'] is True
    assert body['ml']['service'] is True
    assert body['ml']['models_ready'] is False
