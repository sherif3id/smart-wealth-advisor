from __future__ import annotations
import calendar,json,uuid
from datetime import date,datetime,timezone
from decimal import Decimal,ROUND_HALF_UP
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from .financial_definitions import SUMMARY_METHODOLOGY_VERSION
from .models import Account,AuditEvent,Budget,BudgetItem,Category,FinancialSnapshot,Goal,Liability,Portfolio,Position,Recommendation,RiskAssessment,Transaction,User
D=Decimal

def q(value)->Decimal:return D(str(value or 0)).quantize(D('0.01'),rounding=ROUND_HALF_UP)
def ensure_currency(currency:str,user:User):
    if currency!=user.currency:raise HTTPException(422,detail={"code":"CURRENCY_MISMATCH","message":f"Currency must match household base currency {user.currency}; FX conversion is not implemented"})
def month_bounds(year:int,month:int):return date(year,month,1),date(year,month,calendar.monthrange(year,month)[1])
def audit(db:Session,user:User,household_id:uuid.UUID,action:str,resource_type:str,resource_id=None,metadata=None):
    db.add(AuditEvent(household_id=household_id,user_id=user.id,action=action,resource_type=resource_type,resource_id=str(resource_id) if resource_id else None,metadata_json=metadata or {}))

def goal_view(goal:Goal):
    remaining=max(D(0),goal.target_amount-goal.current_amount);progress=float(min(D(100),goal.current_amount/goal.target_amount*100)) if goal.target_amount else 0;monthly=None
    if goal.deadline:
        today=date.today();months=max(0,(goal.deadline.year-today.year)*12+goal.deadline.month-today.month)
        monthly=q(remaining/months) if months>0 else remaining
    return {"id":goal.id,"name":goal.name,"target_amount":goal.target_amount,"current_amount":goal.current_amount,"currency":goal.currency,"deadline":goal.deadline,"priority":goal.priority,"status":goal.status,"created_at":goal.created_at,"remaining_amount":q(remaining),"progress_percent":round(progress,2),"required_monthly_saving":monthly,"projected_completion_date":None}

def budget_view(db:Session,budget:Budget,household_id:uuid.UUID):
    start,end=month_bounds(budget.year,budget.month);items=db.scalars(select(BudgetItem).where(BudgetItem.budget_id==budget.id).order_by(BudgetItem.category)).all();transactions=db.scalars(select(Transaction).where(Transaction.household_id==household_id,Transaction.kind=='expense',Transaction.occurred_on.between(start,end))).all();spent={}
    categories={c.id:c.name for c in db.scalars(select(Category).where(Category.household_id==household_id)).all()}
    for tx in transactions:
        name=categories.get(tx.category_id,'Other');spent[name]=spent.get(name,D(0))+tx.amount
    total_spent=sum((tx.amount for tx in transactions),D(0));days=calendar.monthrange(budget.year,budget.month)[1];elapsed=max(1,min(date.today().day,days));projected=q(total_spent/elapsed*days) if (budget.year,budget.month)==(date.today().year,date.today().month) else q(total_spent)
    result=[]
    for item in items:
        used=q(spent.get(item.category,D(0)));remaining=q(item.limit_amount-used);util=float(used/item.limit_amount*100) if item.limit_amount else (100.0 if used else 0)
        result.append({"category":item.category,"limit_amount":item.limit_amount,"essential":item.essential,"spent":used,"remaining":remaining,"utilization":round(util,2),"over_budget":used>item.limit_amount})
    total_limit=sum((item.limit_amount for item in items),D(0));utilization=float(total_spent/total_limit*100) if total_limit else 0
    return {"id":budget.id,"year":budget.year,"month":budget.month,"currency":budget.currency,"savings_target":budget.savings_target,"total_limit":q(total_limit),"total_spent":q(total_spent),"remaining":q(total_limit-total_spent),"utilization":round(utilization,2),"projected_spending":projected,"items":result}

def portfolio_value(db:Session,household_id:uuid.UUID)->Decimal:
    portfolio_ids=select(Portfolio.id).where(Portfolio.household_id==household_id)
    positions=db.scalars(select(Position).where(Position.portfolio_id.in_(portfolio_ids))).all()
    return sum((position.quantity*position.current_price for position in positions),D(0))

def financial_summary(db:Session,household_id:uuid.UUID,user:User,year:int|None=None,month:int|None=None,save_snapshot:bool=False):
    today=date.today();year=year or today.year;month=month or today.month;start,end=month_bounds(year,month)
    transactions=db.scalars(select(Transaction).where(Transaction.household_id==household_id,Transaction.occurred_on.between(start,end))).all()
    categories={c.id:c for c in db.scalars(select(Category).where(Category.household_id==household_id)).all()}
    budget=db.scalar(select(Budget).where(Budget.household_id==household_id,Budget.year==year,Budget.month==month));budget_data=budget_view(db,budget,household_id) if budget else None
    essential_budget_names={item.category.casefold() for item in db.scalars(select(BudgetItem).where(BudgetItem.budget_id==budget.id,BudgetItem.essential==True)).all()} if budget else set()
    income=sum((tx.amount for tx in transactions if tx.kind=='income'),D(0));expense_transactions=[tx for tx in transactions if tx.kind=='expense'];expenses=sum((tx.amount for tx in expense_transactions),D(0))
    essential_expenses=D(0);expense_by_category={}
    for tx in expense_transactions:
        category=categories.get(tx.category_id);code=category.normalized_code if category else 'other';expense_by_category[code]=expense_by_category.get(code,D(0))+tx.amount;is_essential=bool(category and (category.essential or category.name.casefold() in essential_budget_names))
        if is_essential:essential_expenses+=tx.amount
    discretionary_expenses=expenses-essential_expenses
    accounts=db.scalars(select(Account).where(Account.household_id==household_id,Account.active==True)).all();account_assets=sum((account.balance for account in accounts),D(0));liquid_savings=sum((account.balance for account in accounts if account.is_liquid),D(0));emergency_assets=sum((account.balance for account in accounts if account.is_liquid and account.emergency_eligible),D(0))
    liabilities=db.scalars(select(Liability).where(Liability.household_id==household_id)).all();outstanding_debt=sum((item.balance for item in liabilities),D(0));monthly_debt=sum((item.monthly_payment for item in liabilities),D(0));investments=portfolio_value(db,household_id);total_assets=account_assets+investments
    goals=db.scalars(select(Goal).where(Goal.household_id==household_id,Goal.status.in_(['active','completed']))).all();surplus=income-expenses;savings_rate=float(surplus/income*100) if income else None;dti=float(monthly_debt/income*100) if income else None;emergency_months=float(emergency_assets/essential_expenses) if essential_expenses else None
    methodology={"version":SUMMARY_METHODOLOGY_VERSION,"period":"calendar_month","savings_rate":"(monthly income - monthly expenses) / monthly income","liquid_savings":"sum of active account balances marked liquid","emergency_fund":"liquid emergency-eligible account balances / essential monthly expenses","essential_expenses":"normalized essential category or current budget item explicitly marked essential; uncategorized expenses are discretionary","debt_to_income":"required monthly liability payments / monthly gross income","total_assets":"active account balances + user-priced portfolio positions","net_worth":"total assets - outstanding liabilities","currency_rule":"all included records must match the household base currency; FX conversion is not implemented","goal_allocations":"reported separately and never counted as liquid savings or additional assets"}
    data={"period":{"year":year,"month":month},"transaction_count":len(transactions),"currency":user.currency,"total_income":q(income),"total_expenses":q(expenses),"essential_expenses":q(essential_expenses),"discretionary_expenses":q(discretionary_expenses),"expense_by_category":{key:q(value) for key,value in sorted(expense_by_category.items())},"monthly_surplus":q(surplus),"savings_rate":round(savings_rate,2) if savings_rate is not None else None,"liquid_savings":q(liquid_savings),"current_savings":q(liquid_savings),"emergency_eligible_assets":q(emergency_assets),"emergency_fund_months":round(emergency_months,2) if emergency_months is not None else None,"outstanding_debt":q(outstanding_debt),"total_debt":q(outstanding_debt),"monthly_debt_payments":q(monthly_debt),"debt_to_income_ratio":round(dti,2) if dti is not None else None,"portfolio_value":q(investments),"account_assets":q(account_assets),"total_assets":q(total_assets),"net_worth":q(total_assets-outstanding_debt),"budget":budget_data,"budget_utilization":budget_data['utilization'] if budget_data else None,"goals":[goal_view(goal) for goal in goals],"data_as_of":datetime.now(timezone.utc).isoformat(),"methodology":methodology,"methodology_version":SUMMARY_METHODOLOGY_VERSION}
    if save_snapshot:db.add(FinancialSnapshot(household_id=household_id,data=json.loads(json.dumps(data,default=str)),methodology_version=SUMMARY_METHODOLOGY_VERSION))
    return data

def generate_recommendations(db:Session,household_id:uuid.UUID,user:User,ml:dict|None=None):
    """Deterministic safety-first recommendation pipeline. ML is optional and never fabricated."""
    summary=financial_summary(db,household_id,user);latest_risk=db.scalar(select(RiskAssessment).where(RiskAssessment.household_id==household_id).order_by(RiskAssessment.created_at.desc()));candidates=[]
    if summary['total_income']==0:candidates.append((1,'data_quality','Add current income data','A reliable plan needs current gross-income records.','No income transactions exist for the selected month.',None,None,None))
    if summary['total_expenses']>0 and summary['essential_expenses']==0:candidates.append((2,'classification','Classify essential expenses','Emergency coverage requires essential-expense classification. Uncategorized expenses are treated as discretionary, not silently assumed essential.','No recorded expense is mapped to an essential normalized category or essential budget item.',None,'category',None))
    if summary['debt_to_income_ratio'] is not None and summary['debt_to_income_ratio']>35:candidates.append((1,'debt','Reduce required debt payments','Monthly required debt payments exceed 35% of gross monthly income. Address this before increasing investment risk.','Debt-service-to-income is above the safety threshold.',None,'liability',None))
    if summary['emergency_fund_months'] is not None and summary['emergency_fund_months']<3:candidates.append((1,'reserves','Build liquid emergency reserves','Build emergency-eligible liquid balances toward three months of essential expenses.','Liquid emergency coverage is below three months.',q(summary['essential_expenses']*3-summary['emergency_eligible_assets']),'account',None))
    if summary['savings_rate'] is not None and summary['savings_rate']<10:candidates.append((3,'cash_flow','Improve the monthly surplus','Recorded monthly surplus is below 10% of gross income. Review discretionary spending before adding investment risk.','Savings rate is below the planning baseline.',q(summary['total_income']*D('.10')-summary['monthly_surplus']),None,None))
    if summary.get('budget') and summary['budget']['projected_spending']>summary['budget']['total_limit']:candidates.append((2,'budget','Address the projected budget overrun','Current spending pace projects above the recorded monthly limits.','Projected spending exceeds total budget limits.',q(summary['budget']['projected_spending']-summary['budget']['total_limit']),'budget',summary['budget']['id']))
    for goal in summary['goals']:
        required=goal.get('required_monthly_saving')
        if goal['status']=='active' and required is not None and required>max(summary['monthly_surplus'],D(0)):
            candidates.append((2,'goal_gap',f"Review the funding plan for {goal['name']}","The required monthly contribution is above the currently recorded monthly surplus. Adjust the deadline, target, or spending plan.","Required goal saving exceeds available monthly surplus.",q(required-max(summary['monthly_surplus'],D(0))),'goal',goal['id']))
    if ml and ml.get('prediction'):
        predicted=D(str(ml['prediction'].get('predicted_expense',0)))
        if predicted>summary['total_expenses']*D('1.10') and summary['total_expenses']>0:candidates.append((2,'ml_spending','Review the modeled spending increase','The deployed expense model projects next-month expenses more than 10% above this month. This is an educational projection, not a guarantee.','Model projection exceeds the current recorded month.',q(predicted-summary['total_expenses']),None,None))
    if ml and ml.get('anomaly',{}).get('is_anomaly'):candidates.append((2,'unusual_pattern','Review the unusual spending pattern','The aggregate category pattern differs from the model training distribution. Review categories; this is not fraud detection.','Isolation Forest flagged the monthly aggregate snapshot.',None,None,None))
    critical=any(item[0]==1 for item in candidates);risk_low=bool(latest_risk and latest_risk.category=='Conservative')
    if not critical and not risk_low and summary['monthly_surplus']>0 and summary['emergency_fund_months'] is not None and summary['emergency_fund_months']>=3:candidates.append((4,'investment_readiness','Consider goal-aligned investing','After maintaining liquid reserves and required debt payments, evaluate diversified investments aligned with your horizon and educational risk profile.','No critical reserve or debt condition is currently detected.',None,None,None))
    # Deterministic deduplication by type, then priority and title.
    unique={}
    for item in sorted(candidates,key=lambda x:(x[0],x[2])):unique.setdefault(item[1],item)
    db.query(Recommendation).filter(Recommendation.household_id==household_id,Recommendation.status=='active').update({"status":"superseded"});out=[]
    for priority,kind,title,explanation,reason,impact,related_type,related_id in unique.values():
        recommendation=Recommendation(household_id=household_id,type=kind,title=title,explanation=explanation,reason=reason,estimated_impact=impact,priority=priority,related_entity_type=related_type,related_entity_id=related_id,methodology_version="recommendations-v2");db.add(recommendation);db.flush();out.append(recommendation)
    return sorted(out,key=lambda item:(item.priority,item.created_at or datetime.now(timezone.utc)))
