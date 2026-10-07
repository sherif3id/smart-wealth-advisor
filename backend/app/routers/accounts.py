import uuid
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..auth import current_user,household_id
from ..database import get_db
from ..models import Account,User
from ..schemas import AccountIn,AccountPatch,AccountOut
from ..services import audit,ensure_currency

router=APIRouter(prefix="/accounts",tags=["Accounts"])

def owned(db:Session,hid:uuid.UUID,account_id:uuid.UUID)->Account:
    account=db.scalar(select(Account).where(Account.id==account_id,Account.household_id==hid))
    if not account:raise HTTPException(404,detail={"code":"ACCOUNT_NOT_FOUND","message":"Account was not found"})
    return account

@router.post('',response_model=AccountOut,status_code=201)
def create(data:AccountIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    hid=household_id(user,db);ensure_currency(data.currency,user)
    account=Account(household_id=hid,**data.model_dump());db.add(account);db.flush();audit(db,user,hid,'create','account',account.id);db.commit();db.refresh(account);return account

@router.get('',response_model=list[AccountOut])
def list_accounts(active_only:bool=True,user:User=Depends(current_user),db:Session=Depends(get_db)):
    hid=household_id(user,db);query=select(Account).where(Account.household_id==hid)
    if active_only:query=query.where(Account.active==True)
    return db.scalars(query.order_by(Account.created_at)).all()

@router.patch('/{account_id}',response_model=AccountOut)
def patch(account_id:uuid.UUID,data:AccountPatch,user:User=Depends(current_user),db:Session=Depends(get_db)):
    hid=household_id(user,db);account=owned(db,hid,account_id)
    for key,value in data.model_dump(exclude_unset=True).items():setattr(account,key,value)
    audit(db,user,hid,'patch','account',account.id,{"fields":list(data.model_dump(exclude_unset=True))});db.commit();db.refresh(account);return account

@router.delete('/{account_id}',status_code=204)
def deactivate(account_id:uuid.UUID,user:User=Depends(current_user),db:Session=Depends(get_db)):
    hid=household_id(user,db);account=owned(db,hid,account_id);account.active=False;audit(db,user,hid,'deactivate','account',account.id);db.commit()
