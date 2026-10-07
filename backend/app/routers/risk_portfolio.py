import uuid
from decimal import Decimal
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..auth import current_user,household_id
from ..database import get_db
from ..models import Portfolio,Position,RiskAssessment,User
from ..schemas import PortfolioIn,PositionIn,RiskIn
from ..services import audit,ensure_currency
risk_router=APIRouter(prefix="/risk-assessments",tags=["Risk assessment"])
portfolio_router=APIRouter(prefix="/portfolios",tags=["Portfolios"])
# Methodology v1: six 1..5 answers. Capacity (horizon, liquidity, stability) is capped separately;
# final score is the lower of willingness average and capacity average, converted to 0..100.
@risk_router.post('',status_code=201)
def assess(data:RiskIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
 required=['loss_reaction','return_preference','experience','horizon','liquidity','income_stability']
 if set(data.answers)!=set(required) or any(type(data.answers[k]) is not int or not 1<=data.answers[k]<=5 for k in required):raise HTTPException(422,detail={"code":"INVALID_RISK_ANSWERS","message":"All six answers must be integers from 1 to 5"})
 willingness=sum(data.answers[k] for k in required[:3])/3;capacity=sum(data.answers[k] for k in required[3:])/3;raw=min(willingness,capacity);score=round((raw-1)/4*100,2);category='Conservative' if score<40 else 'Moderate' if score<70 else 'Aggressive';hid=household_id(user,db);x=RiskAssessment(household_id=hid,answers=data.answers,score=score,category=category);db.add(x);user.risk_preference=category;audit(db,user,hid,'create','risk_assessment');db.commit();db.refresh(x);return x
@risk_router.get('/latest')
def latest(user:User=Depends(current_user),db:Session=Depends(get_db)):
 hid=household_id(user,db);x=db.scalar(select(RiskAssessment).where(RiskAssessment.household_id==hid).order_by(RiskAssessment.created_at.desc()))
 if not x:raise HTTPException(404,detail={"code":"RISK_NOT_FOUND","message":"No risk assessment exists"})
 return x
@portfolio_router.post('',status_code=201)
def create_portfolio(data:PortfolioIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
 hid=household_id(user,db);ensure_currency(data.currency,user);p=Portfolio(household_id=hid,**data.model_dump());db.add(p);db.flush();audit(db,user,hid,'create','portfolio',p.id);db.commit();return p
@portfolio_router.get('')
def portfolios(user:User=Depends(current_user),db:Session=Depends(get_db)):
 hid=household_id(user,db);result=[]
 for p in db.scalars(select(Portfolio).where(Portfolio.household_id==hid)).all():
  positions=db.scalars(select(Position).where(Position.portfolio_id==p.id)).all();values=[x.quantity*x.current_price for x in positions];total=sum(values,Decimal(0));classes={}
  for x,v in zip(positions,values):classes[x.asset_class]=classes.get(x.asset_class,Decimal(0))+v
  allocation={k:round(float(v/total*100),2) if total else 0 for k,v in classes.items()};largest=max(allocation.values(),default=0);effective=1/sum((float(v/total)**2 for v in classes.values())) if total and classes else 0
  result.append({"id":p.id,"name":p.name,"currency":p.currency,"value":total,"prices_source":"user-provided; not live market data","gain_loss_methodology":"market value minus total cost basis","allocation":allocation,"largest_asset_weight":largest,"effective_asset_classes":round(effective,2),"positions":[{"id":x.id,"symbol":x.symbol,"asset_class":x.asset_class,"quantity":x.quantity,"cost_basis":x.cost_basis,"current_price":x.current_price,"market_value":x.quantity*x.current_price,"gain_loss":x.quantity*x.current_price-x.cost_basis} for x in positions]})
 return result
@portfolio_router.post('/{portfolio_id}/positions',status_code=201)
def add_position(portfolio_id:uuid.UUID,data:PositionIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
 hid=household_id(user,db);ensure_currency(data.currency,user);p=db.scalar(select(Portfolio).where(Portfolio.id==portfolio_id,Portfolio.household_id==hid))
 if not p:raise HTTPException(404,detail={"code":"PORTFOLIO_NOT_FOUND","message":"Portfolio was not found"})
 x=Position(portfolio_id=p.id,**data.model_dump());db.add(x);audit(db,user,hid,'create','position');db.commit();db.refresh(x);return x
