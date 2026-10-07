import math,uuid
from datetime import date
from fastapi import APIRouter,Depends,HTTPException,Query,status
from sqlalchemy import asc,desc,func,select
from sqlalchemy.orm import Session
from ..auth import current_user,household_id
from ..database import get_db
from ..financial_definitions import normalize_category
from ..models import Account,Category,Transaction,User
from ..schemas import TransactionIn,TransactionPatch
from ..services import audit,ensure_currency
router=APIRouter(prefix="/transactions",tags=["Transactions"])
income_router=APIRouter(prefix="/income",tags=["Income"])

def category(db,hid,name,kind):
 if not name:return None
 normalized,essential=normalize_category(name,kind)
 c=db.scalar(select(Category).where(Category.household_id==hid,func.lower(Category.name)==name.strip().lower(),Category.kind==kind))
 if not c:c=Category(household_id=hid,name=name.strip(),kind=kind,normalized_code=normalized,essential=essential);db.add(c);db.flush()
 elif c.normalized_code!=normalized or c.essential!=essential:c.normalized_code=normalized;c.essential=essential
 return c

def out(db,t):
 c=db.get(Category,t.category_id) if t.category_id else None
 return {"id":t.id,"kind":t.kind,"amount":t.amount,"currency":t.currency,"occurred_on":t.occurred_on,"description":t.description,"category":c.name if c else None,"category_code":c.normalized_code if c else None,"essential":bool(c.essential) if c else False,"account_id":t.account_id,"tags":t.tags,"recurring":t.recurring,"created_at":t.created_at,"updated_at":t.updated_at}
def owned(db,hid,tid):
 t=db.scalar(select(Transaction).where(Transaction.id==tid,Transaction.household_id==hid))
 if not t:raise HTTPException(404,detail={"code":"TRANSACTION_NOT_FOUND","message":"Transaction was not found"})
 return t
def validate_account(db,hid,aid):
 if aid and not db.scalar(select(Account.id).where(Account.id==aid,Account.household_id==hid)):raise HTTPException(400,detail={"code":"INVALID_ACCOUNT","message":"Account does not belong to this household"})

def create_tx(data,db,user,forced_kind=None):
 hid=household_id(user,db);kind=forced_kind or data.kind;ensure_currency(data.currency,user);validate_account(db,hid,data.account_id);c=category(db,hid,data.category,'income' if kind=='income' else 'expense');t=Transaction(household_id=hid,account_id=data.account_id,category_id=c.id if c else None,kind=kind,amount=data.amount,currency=data.currency,occurred_on=data.occurred_on,description=data.description,tags=data.tags,recurring=data.recurring);db.add(t);db.flush();audit(db,user,hid,'create','transaction',t.id,{"kind":kind,"amount":str(data.amount)});db.commit();db.refresh(t);return out(db,t)
@router.post('',status_code=201)
def create(data:TransactionIn,user:User=Depends(current_user),db:Session=Depends(get_db)):return create_tx(data,db,user)
@router.get('')
def list_transactions(page:int=Query(1,ge=1),page_size:int=Query(25,ge=1,le=100),kind:str|None=None,category_name:str|None=Query(None,alias='category'),start_date:date|None=None,end_date:date|None=None,sort:str='date_desc',user:User=Depends(current_user),db:Session=Depends(get_db)):
 hid=household_id(user,db);q=select(Transaction).where(Transaction.household_id==hid);count=select(func.count()).select_from(Transaction).where(Transaction.household_id==hid)
 filters=[]
 if kind:filters.append(Transaction.kind==kind)
 if start_date:filters.append(Transaction.occurred_on>=start_date)
 if end_date:filters.append(Transaction.occurred_on<=end_date)
 if category_name:
  cid=select(Category.id).where(Category.household_id==hid,func.lower(Category.name)==category_name.lower());filters.append(Transaction.category_id.in_(cid))
 q=q.where(*filters);count=count.where(*filters);order={"date_asc":asc(Transaction.occurred_on),"amount_asc":asc(Transaction.amount),"amount_desc":desc(Transaction.amount)}.get(sort,desc(Transaction.occurred_on));total=db.scalar(count) or 0;rows=db.scalars(q.order_by(order,desc(Transaction.created_at)).offset((page-1)*page_size).limit(page_size)).all();return {"items":[out(db,x) for x in rows],"page":page,"page_size":page_size,"total":total,"pages":math.ceil(total/page_size) if total else 0}
@router.get('/{transaction_id}')
def get_one(transaction_id:uuid.UUID,user:User=Depends(current_user),db:Session=Depends(get_db)):return out(db,owned(db,household_id(user,db),transaction_id))
@router.put('/{transaction_id}')
def replace(transaction_id:uuid.UUID,data:TransactionIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
 hid=household_id(user,db);t=owned(db,hid,transaction_id);ensure_currency(data.currency,user);validate_account(db,hid,data.account_id);c=category(db,hid,data.category,'income' if data.kind=='income' else 'expense');
 for k,v in data.model_dump(exclude={'category'}).items():setattr(t,k,v)
 t.category_id=c.id if c else None;audit(db,user,hid,'replace','transaction',t.id);db.commit();db.refresh(t);return out(db,t)
@router.patch('/{transaction_id}')
def patch(transaction_id:uuid.UUID,data:TransactionPatch,user:User=Depends(current_user),db:Session=Depends(get_db)):
 hid=household_id(user,db);t=owned(db,hid,transaction_id);changes=data.model_dump(exclude_unset=True);cat=changes.pop('category',None)
 if 'currency' in changes and changes['currency'] is not None:ensure_currency(changes['currency'],user)
 if 'account_id' in changes:validate_account(db,hid,changes['account_id'])
 for k,v in changes.items():setattr(t,k,v)
 if cat is not None:
  c=category(db,hid,cat,'income' if t.kind=='income' else 'expense');t.category_id=c.id if c else None
 audit(db,user,hid,'patch','transaction',t.id,{"fields":list(changes)});db.commit();db.refresh(t);return out(db,t)
@router.delete('/{transaction_id}',status_code=204)
def delete(transaction_id:uuid.UUID,user:User=Depends(current_user),db:Session=Depends(get_db)):
 hid=household_id(user,db);t=owned(db,hid,transaction_id);audit(db,user,hid,'delete','transaction',t.id);db.delete(t);db.commit();return None

@income_router.post('',status_code=201)
def add_income(data:TransactionIn,user:User=Depends(current_user),db:Session=Depends(get_db)):return create_tx(data,db,user,'income')
@income_router.get('')
def get_income(page:int=1,page_size:int=25,user:User=Depends(current_user),db:Session=Depends(get_db)):
 hid=household_id(user,db);q=select(Transaction).where(Transaction.household_id==hid,Transaction.kind=='income').order_by(desc(Transaction.occurred_on));rows=db.scalars(q.offset((page-1)*page_size).limit(min(page_size,100))).all();return [out(db,x) for x in rows]
@income_router.put('/{income_id}')
def update_income(income_id:uuid.UUID,data:TransactionIn,user:User=Depends(current_user),db:Session=Depends(get_db)):data.kind='income';return replace(income_id,data,user,db)
@income_router.delete('/{income_id}',status_code=204)
def delete_income(income_id:uuid.UUID,user:User=Depends(current_user),db:Session=Depends(get_db)):return delete(income_id,user,db)
