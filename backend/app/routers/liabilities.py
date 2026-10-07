import uuid
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..auth import current_user,household_id
from ..database import get_db
from ..models import Liability,User
from ..schemas import LiabilityIn,LiabilityPatch
from ..services import audit,ensure_currency
router=APIRouter(prefix="/liabilities",tags=["Liabilities"])
def owned(db,hid,id):
 x=db.scalar(select(Liability).where(Liability.id==id,Liability.household_id==hid))
 if not x:raise HTTPException(404,detail={"code":"LIABILITY_NOT_FOUND","message":"Liability was not found"})
 return x
@router.post('',status_code=201)
def create(data:LiabilityIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
 hid=household_id(user,db);ensure_currency(data.currency,user);x=Liability(household_id=hid,**data.model_dump());db.add(x);db.flush();audit(db,user,hid,'create','liability',x.id);db.commit();db.refresh(x);return x
@router.get('')
def list_all(user:User=Depends(current_user),db:Session=Depends(get_db)):
 hid=household_id(user,db);items=db.scalars(select(Liability).where(Liability.household_id==hid).order_by(Liability.interest_rate.desc())).all();monthly=sum((x.monthly_payment for x in items),0);income=db.scalar(select(User).where(User.id==user.id));return {"items":items,"total_balance":sum((x.balance for x in items),0),"monthly_payments":monthly}
@router.patch('/{liability_id}')
def patch(liability_id:uuid.UUID,data:LiabilityPatch,user:User=Depends(current_user),db:Session=Depends(get_db)):
 hid=household_id(user,db);x=owned(db,hid,liability_id)
 for k,v in data.model_dump(exclude_unset=True).items():setattr(x,k,v)
 audit(db,user,hid,'patch','liability',x.id);db.commit();db.refresh(x);return x
@router.delete('/{liability_id}',status_code=204)
def delete(liability_id:uuid.UUID,user:User=Depends(current_user),db:Session=Depends(get_db)):
 hid=household_id(user,db);x=owned(db,hid,liability_id);audit(db,user,hid,'delete','liability',x.id);db.delete(x);db.commit();return None
