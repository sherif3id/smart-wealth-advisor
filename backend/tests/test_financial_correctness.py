from datetime import date

def test_authoritative_summary_separates_cash_goals_investments_and_debt(client,headers):
    account=client.get('/accounts',headers=headers).json()[0]
    assert client.patch(f"/accounts/{account['id']}",headers=headers,json={'balance':10000,'is_liquid':True,'emergency_eligible':True}).status_code==200
    today=str(date.today())
    for payload in [
        {'kind':'income','amount':20000,'currency':'USD','occurred_on':today,'description':'Salary','category':'Salary'},
        {'kind':'expense','amount':4000,'currency':'USD','occurred_on':today,'description':'Groceries','category':'Food'},
        {'kind':'expense','amount':1000,'currency':'USD','occurred_on':today,'description':'Cinema','category':'Entertainment'},
    ]:assert client.post('/transactions',headers=headers,json=payload).status_code==201
    goal=client.post('/goals',headers=headers,json={'name':'Home','target_amount':100000,'current_amount':8000,'currency':'USD'});assert goal.status_code==201
    liability=client.post('/liabilities',headers=headers,json={'name':'Loan','kind':'loan','balance':50000,'monthly_payment':2000,'interest_rate':8,'currency':'USD'});assert liability.status_code==201
    portfolio=client.post('/portfolios',headers=headers,json={'name':'Investments','currency':'USD'}).json()
    assert client.post(f"/portfolios/{portfolio['id']}/positions",headers=headers,json={'symbol':'USER','asset_class':'Equity','quantity':2,'cost_basis':150,'current_price':100,'currency':'USD'}).status_code==201
    summary=client.get('/financial-summary',headers=headers).json()
    assert float(summary['liquid_savings'])==10000
    assert float(summary['essential_expenses'])==4000
    assert float(summary['discretionary_expenses'])==1000
    assert summary['emergency_fund_months']==2.5
    assert summary['savings_rate']==75.0
    assert float(summary['outstanding_debt'])==50000
    assert float(summary['monthly_debt_payments'])==2000
    assert summary['debt_to_income_ratio']==10.0
    assert float(summary['portfolio_value'])==200
    assert float(summary['total_assets'])==10200
    assert float(summary['net_worth'])==-39800
    assert float(summary['goals'][0]['current_amount'])==8000
    assert summary['methodology']['goal_allocations'].startswith('reported separately')

def test_currency_mismatch_is_rejected_without_fx(client,headers):
    response=client.post('/transactions',headers=headers,json={'kind':'expense','amount':10,'currency':'EGP','occurred_on':str(date.today()),'category':'Food'})
    assert response.status_code==422
    assert response.json()['error']['code']=='CURRENCY_MISMATCH'
