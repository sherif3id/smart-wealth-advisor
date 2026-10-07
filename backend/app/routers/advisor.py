from fastapi import APIRouter,Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..auth import current_user,household_id
from ..database import get_db
from ..models import AdvisorMessage,Budget,Goal,Transaction,User
from ..schemas import AdvisorMessageIn
from ..services import budget_view,financial_summary
router=APIRouter(prefix='/advisor',tags=['AI advisor'])
@router.get('/context')
def context(user:User=Depends(current_user),db:Session=Depends(get_db)):
 hid=household_id(user,db);tx=db.scalars(select(Transaction).where(Transaction.household_id==hid).order_by(Transaction.occurred_on.desc()).limit(40)).all();goals=db.scalars(select(Goal).where(Goal.household_id==hid).order_by(Goal.created_at.desc()).limit(20)).all();budget=db.scalar(select(Budget).where(Budget.household_id==hid).order_by(Budget.year.desc(),Budget.month.desc()))
 return {'profile':{'name':user.name,'age':user.age,'country':user.country,'currency':user.currency,'employment':user.employment,'risk_preference':user.risk_preference,'investment_horizon':user.investment_horizon},'summary':financial_summary(db,hid,user),'recent_transactions':[{'kind':x.kind,'amount':x.amount,'date':x.occurred_on,'description':x.description} for x in tx],'goals':[{'name':x.name,'target_amount':x.target_amount,'current_amount':x.current_amount,'deadline':x.deadline} for x in goals],'budget':budget_view(db,budget,hid) if budget else None}
@router.get('/messages')
def messages(user:User=Depends(current_user),db:Session=Depends(get_db)):
 hid=household_id(user,db);rows=db.scalars(select(AdvisorMessage).where(AdvisorMessage.household_id==hid).order_by(AdvisorMessage.created_at.desc()).limit(20)).all();return [{'role':x.role,'content':x.content} for x in reversed(rows)]
@router.post('/messages',status_code=201)
def save(body:AdvisorMessageIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
 hid=household_id(user,db);user_text=body.user;assistant=body.assistant
 if user_text:db.add(AdvisorMessage(household_id=hid,role='user',content=user_text))
 if assistant:db.add(AdvisorMessage(household_id=hid,role='assistant',content=assistant))
 db.commit();return {'saved':True}
