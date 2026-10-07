from datetime import date
import httpx,numpy as np
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..auth import current_user,household_id
from ..config import get_settings
from ..database import get_db
from ..financial_definitions import ML_CATEGORY_CODES,ML_FEATURE_CONTRACT_VERSION
from ..models import Category,Scenario,Transaction,User
from ..schemas import MonteCarloIn
from ..services import audit,financial_summary,month_bounds

scenario_router=APIRouter(prefix="/scenarios",tags=["Scenarios"]);ml_router=APIRouter(prefix="/ml",tags=["ML integration"]);settings=get_settings()

@scenario_router.post('/monte-carlo',status_code=201)
def monte_carlo(data:MonteCarloIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    hid=household_id(user,db);rng=np.random.default_rng(data.seed);months=data.horizon_years*12;monthly_return=(1+data.expected_return)**(1/12)-1;monthly_vol=data.volatility/np.sqrt(12);inflation=(1+data.inflation)**data.horizon_years;values=np.full(data.simulations,data.initial_capital,dtype=float)
    for _ in range(months):values=np.maximum((values+data.monthly_contribution)*(1+rng.normal(monthly_return,monthly_vol,data.simulations)),0)
    real=values/inflation;p10,p50,p90=np.percentile(real,[10,50,90]);result={"p10":round(float(p10),2),"p50":round(float(p50),2),"p90":round(float(p90),2),"probability_of_goal":round(float(np.mean(real>=data.goal_amount))*100,2) if data.goal_amount is not None else None,"probability_of_shortfall":round(float(np.mean(real<data.goal_amount))*100,2) if data.goal_amount is not None else None,"simulations":data.simulations,"seed":data.seed,"assumptions":{"expected_return":data.expected_return,"volatility":data.volatility,"inflation":data.inflation,"returns_distribution":"independent normal monthly returns","values":"inflation-adjusted","classification":"Educational scenario simulation, not a guarantee or market forecast."}}
    scenario=Scenario(household_id=hid,name='Monte Carlo',inputs=data.model_dump(),results=result,seed=data.seed);db.add(scenario);db.flush();audit(db,user,hid,'create','scenario',scenario.id);db.commit();return {"id":scenario.id,**result}

@scenario_router.get('')
def scenarios(user:User=Depends(current_user),db:Session=Depends(get_db)):
    hid=household_id(user,db);return db.scalars(select(Scenario).where(Scenario.household_id==hid).order_by(Scenario.created_at.desc()).limit(50)).all()

def ml_vector(db:Session,hid,user:User,year:int|None=None,month:int|None=None):
    """Build exactly one current calendar-month observation from authoritative records."""
    today=date.today();year=year or today.year;month=month or today.month;start,end=month_bounds(year,month);summary=financial_summary(db,hid,user,year,month);categories={item.id:item.normalized_code for item in db.scalars(select(Category).where(Category.household_id==hid)).all()};transactions=db.scalars(select(Transaction).where(Transaction.household_id==hid,Transaction.kind=='expense',Transaction.occurred_on.between(start,end))).all();totals={key:0.0 for key in ML_CATEGORY_CODES}
    for transaction in transactions:
        code=categories.get(transaction.category_id,"other")
        if code in totals:totals[code]+=float(transaction.amount)
    return {"income":float(summary['total_income']),**totals,"monthly_debt_payments":float(summary['monthly_debt_payments']),"monthly_surplus":float(summary['monthly_surplus'])},{"year":year,"month":month,"period":"current calendar month","feature_contract_version":ML_FEATURE_CONTRACT_VERSION,"uncategorized_expenses_excluded_from_category_features":float(summary['total_expenses'])-sum(totals.values())}

def call_ml(path:str,payload:dict|None=None):
    try:
        response=httpx.request('POST' if payload is not None else 'GET',f"{settings.ml_service_url}{path}",json=payload,timeout=settings.request_timeout_seconds)
        if response.status_code>=400:raise HTTPException(503,detail={"code":"ML_UNAVAILABLE","message":"ML model is not trained/deployed or the service is unavailable","provider_status":response.status_code})
        return response.json()
    except httpx.HTTPError as exc:raise HTTPException(503,detail={"code":"ML_UNAVAILABLE","message":"ML service could not be reached"}) from exc

@ml_router.get('/status')
def ml_status(user:User=Depends(current_user)):return call_ml('/health/ready')
def collect_ml_insights(db:Session,hid,user:User,year:int|None=None,month:int|None=None):
    vector,metadata=ml_vector(db,hid,user,year,month);return {"prediction":call_ml('/predict-expenses',vector),"anomaly":call_ml('/check-expense',vector),"behavior":call_ml('/financial-profile',vector),"input":metadata}

@ml_router.get('/insights')
def insights(year:int|None=None,month:int|None=None,user:User=Depends(current_user),db:Session=Depends(get_db)):
    return collect_ml_insights(db,household_id(user,db),user,year,month)
