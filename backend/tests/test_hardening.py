from datetime import date,datetime,timedelta,timezone
import jwt
from sqlalchemy import select
from app.config import get_settings
from app.models import Alert,AuditEvent,HouseholdMember,User
from conftest import TestingSession,register

def test_registration_policy_duplicate_normalization_and_login(client):
    weak=client.post('/auth/register',json={'email':'weak@example.com','password':'alllowercase123','name':'Weak User','locale':'en'});assert weak.status_code==422
    token=register(client,'Mixed.Case@Example.com','Case User');assert token
    duplicate=client.post('/auth/register',json={'email':'mixed.case@example.com','password':'VeryStrong123!','name':'Other','locale':'en'});assert duplicate.status_code==409
    login=client.post('/auth/login',json={'email':'MIXED.CASE@example.com','password':'VeryStrong123!'});assert login.status_code==200

def test_ai_confirmation_wrong_user_expired_modified_reused_and_audited(client,headers):
    action={'type':'add_transaction','payload':{'kind':'expense','amount':'25.00','category':'Food','date':str(date.today()),'description':'Confirmed'}}
    prepared=client.post('/ai-actions/prepare',headers=headers,json={'action':action});assert prepared.status_code==200;token=prepared.json()['confirmation_token'];server_action=prepared.json()['action']
    other=register(client,'other-ai@example.com','Other User');other_headers={'Authorization':f'Bearer {other}'}
    wrong=client.post('/ai-actions/execute',headers=other_headers,json={'action':server_action,'confirmation_token':token});assert wrong.status_code==403
    modified={**server_action,'payload':{**server_action['payload'],'amount':'2500.00'}};assert client.post('/ai-actions/execute',headers=headers,json={'action':modified,'confirmation_token':token}).status_code==403
    settings=get_settings();claims=jwt.decode(token,settings.jwt_secret,algorithms=[settings.jwt_algorithm],options={'verify_aud':False});claims['exp']=datetime.now(timezone.utc)-timedelta(seconds=1);expired=jwt.encode(claims,settings.jwt_secret,algorithm=settings.jwt_algorithm);assert client.post('/ai-actions/execute',headers=headers,json={'action':server_action,'confirmation_token':expired}).status_code==401
    success=client.post('/ai-actions/execute',headers=headers,json={'action':server_action,'confirmation_token':token});assert success.status_code==200
    reused=client.post('/ai-actions/execute',headers=headers,json={'action':server_action,'confirmation_token':token});assert reused.status_code==409;assert reused.json()['error']['code']=='CONFIRMATION_ALREADY_USED'
    with TestingSession() as db:assert db.scalar(select(AuditEvent).where(AuditEvent.action=='execute_ai_action')) is not None

def test_cross_user_ownership_across_protected_resources(client,headers):
    today=date.today();account=client.get('/accounts',headers=headers).json()[0]
    goal=client.post('/goals',headers=headers,json={'name':'Private goal','target_amount':1000,'currency':'USD'}).json()
    liability=client.post('/liabilities',headers=headers,json={'name':'Private loan','kind':'loan','balance':100,'currency':'USD'}).json()
    portfolio=client.post('/portfolios',headers=headers,json={'name':'Private portfolio','currency':'USD'}).json()
    budget=client.post('/budgets',headers=headers,json={'year':today.year,'month':today.month,'currency':'USD','items':[{'category':'Food','limit_amount':100}]}).json()
    report=client.post('/reports',headers=headers,json={'kind':'health','locale':'en'}).json()
    client.post('/risk-assessments',headers=headers,json={'answers':{key:3 for key in ['loss_reaction','return_preference','experience','horizon','liquidity','income_stability']}})
    client.post('/scenarios/monte-carlo',headers=headers,json={'initial_capital':100,'monthly_contribution':10,'horizon_years':2,'expected_return':.05,'volatility':.1,'inflation':.02,'simulations':1000,'seed':1})
    client.post('/advisor/messages',headers=headers,json={'user':'private','assistant':'private response'})
    client.put('/notifications',headers=headers,json={'email':'private@example.com','frequency':'weekly','enabled':True,'locale':'en'})
    client.post('/recommendations/refresh',headers=headers);recommendations=client.get('/recommendations',headers=headers).json();recommendation=recommendations[0]
    with TestingSession() as db:
        user=db.scalar(select(User).where(User.email=='a@example.com'));hid=db.scalar(select(HouseholdMember.household_id).where(HouseholdMember.user_id==user.id));alert=Alert(household_id=hid,type='test',severity='info',title='Private',message='Private');db.add(alert);db.commit();alert_id=alert.id
    other=register(client,'isolation@example.com','Isolation User');h={'Authorization':f'Bearer {other}'}
    assert client.patch(f"/accounts/{account['id']}",headers=h,json={'balance':1}).status_code==404
    assert client.get(f"/goals/{goal['id']}",headers=h).status_code==404
    assert client.post(f"/goals/{goal['id']}/contributions",headers=h,json={'amount':1,'contributed_on':str(today)}).status_code==404
    assert client.patch(f"/liabilities/{liability['id']}",headers=h,json={'balance':1}).status_code==404
    assert client.post(f"/portfolios/{portfolio['id']}/positions",headers=h,json={'symbol':'X','asset_class':'Other','quantity':1,'cost_basis':1,'current_price':1,'currency':'USD'}).status_code==404
    assert client.delete(f"/budgets/{budget['id']}",headers=h).status_code==404
    assert client.get(f"/reports/{report['id']}",headers=h).status_code==404
    assert client.patch(f"/recommendations/{recommendation['id']}",headers=h,json={'status':'dismissed'}).status_code==404
    assert client.patch(f"/alerts/{alert_id}/read",headers=h).status_code==404
    assert client.get('/risk-assessments/latest',headers=h).status_code==404
    assert client.get('/scenarios',headers=h).json()==[]
    assert client.get('/advisor/messages',headers=h).json()==[]
    assert client.get('/notifications',headers=h).json()['configured'] is False
