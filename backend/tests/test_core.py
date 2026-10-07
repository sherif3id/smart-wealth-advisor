from datetime import date,timedelta
from conftest import register
PROFILE={'name':'Alice','locale':'en','country':'Egypt','currency':'EGP','age':30,'employment':'Employed','risk_preference':'Balanced','investment_horizon':10,'onboarding_complete':True}
def test_auth_profile_and_validation(client,headers):
 assert client.get('/auth/me',headers=headers).status_code==200
 r=client.put('/profile',headers=headers,json=PROFILE);assert r.status_code==200;r=client.post('/auth/login',json={'email':'a@example.com','password':'wrong-password'});assert r.status_code==401
 bad=client.post('/transactions',headers=headers,json={'kind':'expense','amount':0,'currency':'EGP','occurred_on':str(date.today())});assert bad.status_code==422;assert bad.json()['error']['code']=='VALIDATION_ERROR'
def test_transactions_crud_filters_pagination(client,headers):
 payload={'kind':'expense','amount':'150.50','currency':'USD','occurred_on':str(date.today()),'description':'Lunch','category':'Food','tags':['work']}
 r=client.post('/transactions',headers=headers,json=payload);assert r.status_code==201;rbody=r.json();tid=rbody['id'];assert rbody['category']=='Food'
 assert client.get(f'/transactions/{tid}',headers=headers).status_code==200
 r=client.patch(f'/transactions/{tid}',headers=headers,json={'amount':'180.75'});assert r.status_code==200;assert float(r.json()['amount'])==180.75
 r=client.get('/transactions?kind=expense&category=Food&page=1&page_size=10',headers=headers);assert r.status_code==200;assert r.json()['total']==1
 assert client.delete(f'/transactions/{tid}',headers=headers).status_code==204;assert client.get(f'/transactions/{tid}',headers=headers).status_code==404
def test_user_cannot_access_another_users_data(client,headers):
 r=client.post('/transactions',headers=headers,json={'kind':'expense','amount':100,'currency':'USD','occurred_on':str(date.today()),'description':'Private','category':'Other'});tid=r.json()['id'];other=register(client,'b@example.com','Bob');h2={'Authorization':f'Bearer {other}'}
 assert client.get(f'/transactions/{tid}',headers=h2).status_code==404;assert client.patch(f'/transactions/{tid}',headers=h2,json={'amount':1}).status_code==404;assert client.delete(f'/transactions/{tid}',headers=h2).status_code==404

def test_budget_goals_liabilities_and_summary(client,headers):
 client.put('/profile',headers=headers,json=PROFILE);today=date.today()
 client.post('/income',headers=headers,json={'kind':'income','amount':15000,'currency':'EGP','occurred_on':str(today),'description':'Salary','category':'Salary','recurring':True})
 client.post('/transactions',headers=headers,json={'kind':'expense','amount':3000,'currency':'EGP','occurred_on':str(today),'description':'Food','category':'Food'})
 budget={'year':today.year,'month':today.month,'currency':'EGP','savings_target':3000,'items':[{'category':'Food','limit_amount':4000,'essential':True},{'category':'Entertainment','limit_amount':1000,'essential':False}]}
 r=client.post('/budgets',headers=headers,json=budget);assert r.status_code==201;r=client.get(f'/budgets/{today.year}/{today.month}',headers=headers);assert float(r.json()['total_spent'])==3000;assert float(next(x for x in r.json()['items'] if x['category']=='Food')['spent'])==3000
 deadline=today+timedelta(days=365);r=client.post('/goals',headers=headers,json={'name':'Laptop','target_amount':60000,'current_amount':15000,'currency':'EGP','deadline':str(deadline),'priority':2});assert r.status_code==201;goal=r.json();assert float(goal['remaining_amount'])==45000;assert float(goal['required_monthly_saving'])>0
 r=client.post(f"/goals/{goal['id']}/contributions",headers=headers,json={'amount':5000,'contributed_on':str(today)});assert float(r.json()['current_amount'])==20000
 r=client.post('/liabilities',headers=headers,json={'name':'Car loan','kind':'loan','balance':50000,'monthly_payment':1000,'interest_rate':12,'currency':'EGP'});assert r.status_code==201
 s=client.get('/financial-summary',headers=headers);assert s.status_code==200;body=s.json();assert float(body['total_income'])==15000;assert float(body['total_expenses'])==3000;assert float(body['total_debt'])==50000

def test_risk_monte_carlo_reports_and_ai_confirmation(client,headers):
 client.put('/profile',headers=headers,json=PROFILE)
 answers={k:3 for k in ['loss_reaction','return_preference','experience','horizon','liquidity','income_stability']};r=client.post('/risk-assessments',headers=headers,json={'answers':answers});assert r.status_code==201;assert r.json()['category']=='Moderate'
 scenario={'initial_capital':10000,'monthly_contribution':500,'horizon_years':10,'expected_return':.07,'volatility':.12,'inflation':.03,'simulations':2000,'goal_amount':100000,'seed':7};r=client.post('/scenarios/monte-carlo',headers=headers,json=scenario);assert r.status_code==201;d=r.json();assert d['p10']<=d['p50']<=d['p90'];assert 0<=d['probability_of_goal']<=100
 assert client.post('/reports',headers=headers,json={'kind':'health','locale':'en'}).status_code==201
 action={'type':'add_transaction','payload':{'kind':'expense','amount':50,'category':'Food','date':str(date.today()),'description':'AI suggested'}};prep=client.post('/ai-actions/prepare',headers=headers,json={'action':action});assert prep.status_code==200
 modified={'type':'add_transaction','payload':{**action['payload'],'amount':5000}};assert client.post('/ai-actions/execute',headers=headers,json={'action':modified,'confirmation_token':prep.json()['confirmation_token']}).status_code==403
 done=client.post('/ai-actions/execute',headers=headers,json={'action':action,'confirmation_token':prep.json()['confirmation_token']});assert done.status_code==200
