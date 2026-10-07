import uuid
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..auth import current_user,household_id
from ..database import get_db
from ..models import Budget,BudgetItem,User
from ..schemas import BudgetIn
from ..services import audit,budget_view,ensure_currency
router=APIRouter(prefix="/budgets",tags=["Budgets"])
@router.post('',status_code=201)
def upsert(data:BudgetIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
 hid=household_id(user,db);ensure_currency(data.currency,user);budget=db.scalar(select(Budget).where(Budget.household_id==hid,Budget.year==data.year,Budget.month==data.month))
 if not budget:budget=Budget(household_id=hid,year=data.year,month=data.month,currency=data.currency,savings_target=data.savings_target);db.add(budget);db.flush()
 else:budget.currency=data.currency;budget.savings_target=data.savings_target;db.query(BudgetItem).filter(BudgetItem.budget_id==budget.id).delete()
 for x in data.items:db.add(BudgetItem(budget_id=budget.id,**x.model_dump()))
 audit(db,user,hid,'upsert','budget',budget.id,{"year":data.year,"month":data.month});db.commit();return budget_view(db,budget,hid)
@router.get('/{year}/{month}')
def get_budget(year:int,month:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
 hid=household_id(user,db);budget=db.scalar(select(Budget).where(Budget.household_id==hid,Budget.year==year,Budget.month==month))
 if not budget:raise HTTPException(404,detail={"code":"BUDGET_NOT_FOUND","message":"No budget exists for this month"})
 return budget_view(db,budget,hid)
@router.delete('/{budget_id}',status_code=204)
def delete_budget(budget_id:uuid.UUID,user:User=Depends(current_user),db:Session=Depends(get_db)):
 hid=household_id(user,db);b=db.scalar(select(Budget).where(Budget.id==budget_id,Budget.household_id==hid))
 if not b:raise HTTPException(404,detail={"code":"BUDGET_NOT_FOUND","message":"Budget not found"})
 audit(db,user,hid,'delete','budget',b.id);db.delete(b);db.commit();return None
