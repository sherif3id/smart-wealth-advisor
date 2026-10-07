import uuid
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..auth import current_user,household_id
from ..database import get_db
from ..models import Goal,GoalContribution,User
from ..schemas import ContributionIn,GoalIn,GoalPatch
from ..services import audit,goal_view,ensure_currency
router=APIRouter(prefix="/goals",tags=["Goals"])
def owned(db,hid,gid):
 g=db.scalar(select(Goal).where(Goal.id==gid,Goal.household_id==hid))
 if not g:raise HTTPException(404,detail={"code":"GOAL_NOT_FOUND","message":"Goal was not found"})
 return g
@router.post('',status_code=201)
def create(data:GoalIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
 hid=household_id(user,db);ensure_currency(data.currency,user);g=Goal(household_id=hid,**data.model_dump());db.add(g);db.flush();audit(db,user,hid,'create','goal',g.id);db.commit();db.refresh(g);return goal_view(g)
@router.get('')
def list_goals(status:str|None=None,user:User=Depends(current_user),db:Session=Depends(get_db)):
 hid=household_id(user,db);q=select(Goal).where(Goal.household_id==hid)
 if status:q=q.where(Goal.status==status)
 return [goal_view(x) for x in db.scalars(q.order_by(Goal.priority,Goal.deadline)).all()]
@router.get('/{goal_id}')
def get(goal_id:uuid.UUID,user:User=Depends(current_user),db:Session=Depends(get_db)):return goal_view(owned(db,household_id(user,db),goal_id))
@router.patch('/{goal_id}')
def patch(goal_id:uuid.UUID,data:GoalPatch,user:User=Depends(current_user),db:Session=Depends(get_db)):
 hid=household_id(user,db);g=owned(db,hid,goal_id)
 for k,v in data.model_dump(exclude_unset=True).items():setattr(g,k,v)
 audit(db,user,hid,'patch','goal',g.id);db.commit();db.refresh(g);return goal_view(g)
@router.delete('/{goal_id}',status_code=204)
def delete(goal_id:uuid.UUID,user:User=Depends(current_user),db:Session=Depends(get_db)):
 hid=household_id(user,db);g=owned(db,hid,goal_id);audit(db,user,hid,'delete','goal',g.id);db.delete(g);db.commit();return None
@router.post('/{goal_id}/contributions',status_code=201)
def contribute(goal_id:uuid.UUID,data:ContributionIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
 hid=household_id(user,db);g=owned(db,hid,goal_id);c=GoalContribution(goal_id=g.id,**data.model_dump());g.current_amount+=data.amount
 if g.current_amount>=g.target_amount:g.status='completed'
 db.add(c);audit(db,user,hid,'contribute','goal',g.id,{"amount":str(data.amount)});db.commit();return goal_view(g)
