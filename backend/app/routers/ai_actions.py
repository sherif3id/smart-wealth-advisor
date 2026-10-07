import hashlib,json,uuid
from datetime import date,datetime,timedelta,timezone
import jwt
from fastapi import APIRouter,Depends,HTTPException
from jwt import InvalidTokenError
from sqlalchemy import delete,select
from sqlalchemy.orm import Session
from ..auth import current_user,household_id
from ..config import get_settings
from ..database import get_db
from ..financial_definitions import normalize_category
from ..models import Budget,BudgetItem,Category,Goal,Notification,Transaction,UsedConfirmationToken,User
from ..schemas import AIAction,AIActionExecuteIn,AIActionPrepareIn
from ..services import audit

router=APIRouter(prefix="/ai-actions",tags=["AI actions"]);settings=get_settings();CONFIRMATION_ISSUER="smart-wealth-ai-actions";CONFIRMATION_AUDIENCE="smart-wealth-confirmation"
def action_dict(action:AIAction):return action.model_dump(mode='json',exclude_none=True)
def canonical(action:AIAction):return json.dumps(action_dict(action),sort_keys=True,separators=(',',':'))
def cleanup(db:Session):db.execute(delete(UsedConfirmationToken).where(UsedConfirmationToken.expires_at<datetime.now(timezone.utc)))

@router.post('/prepare')
def prepare(data:AIActionPrepareIn,user:User=Depends(current_user)):
    action=action_dict(data.action);digest=hashlib.sha256(canonical(data.action).encode()).hexdigest();now=datetime.now(timezone.utc);jti=uuid.uuid4().hex;token=jwt.encode({'sub':str(user.id),'jti':jti,'action_hash':digest,'iat':now,'nbf':now,'exp':now+timedelta(minutes=10),'iss':CONFIRMATION_ISSUER,'aud':CONFIRMATION_AUDIENCE,'typ':'ai_confirmation'},settings.jwt_secret,algorithm=settings.jwt_algorithm);return {'confirmation_token':token,'expires_in':600,'action':action}

@router.post('/execute')
def execute(data:AIActionExecuteIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    try:
        claims=jwt.decode(data.confirmation_token,settings.jwt_secret,algorithms=[settings.jwt_algorithm],issuer=CONFIRMATION_ISSUER,audience=CONFIRMATION_AUDIENCE,options={'require':['sub','jti','action_hash','iat','nbf','exp','iss','aud','typ']})
        if claims.get('typ')!='ai_confirmation':raise InvalidTokenError('wrong type')
    except InvalidTokenError as exc:raise HTTPException(401,detail={"code":"INVALID_CONFIRMATION","message":"Confirmation expired or invalid"}) from exc
    if claims['sub']!=str(user.id) or claims['action_hash']!=hashlib.sha256(canonical(data.action).encode()).hexdigest():raise HTTPException(403,detail={"code":"ACTION_MISMATCH","message":"Confirmed action does not match user or requested action"})
    cleanup(db)
    if db.get(UsedConfirmationToken,claims['jti']):raise HTTPException(409,detail={"code":"CONFIRMATION_ALREADY_USED","message":"Confirmation token has already been used"})
    expires=datetime.fromtimestamp(claims['exp'],timezone.utc);db.add(UsedConfirmationToken(jti=claims['jti'],user_id=user.id,expires_at=expires));hid=household_id(user,db);action=data.action;payload=action.payload;result={}
    if action.type=='update_profile':
        changes=payload.model_dump(exclude_none=True)
        for key,value in changes.items():setattr(user,key,value)
        result={'profile_updated':list(changes)}
    elif action.type=='add_transaction':
        code,essential=normalize_category(payload.category,payload.kind);category=db.scalar(select(Category).where(Category.household_id==hid,Category.kind==payload.kind,Category.name==payload.category))
        if not category:category=Category(household_id=hid,name=payload.category,kind=payload.kind,normalized_code=code,essential=essential);db.add(category);db.flush()
        transaction=Transaction(household_id=hid,kind=payload.kind,amount=payload.amount,currency=user.currency,occurred_on=payload.date,description=payload.description,category_id=category.id);db.add(transaction);db.flush();result={'transaction_id':str(transaction.id)}
    elif action.type=='update_budget':
        today=date.today();budget=db.scalar(select(Budget).where(Budget.household_id==hid,Budget.year==today.year,Budget.month==today.month))
        if not budget:budget=Budget(household_id=hid,year=today.year,month=today.month,currency=user.currency);db.add(budget);db.flush()
        item=db.scalar(select(BudgetItem).where(BudgetItem.budget_id==budget.id,BudgetItem.category==payload.category))
        if not item:item=BudgetItem(budget_id=budget.id,category=payload.category,limit_amount=0);db.add(item)
        item.limit_amount=payload.limit;result={'budget_id':str(budget.id)}
    elif action.type=='save_goal':
        goal=Goal(household_id=hid,name=payload.name,target_amount=payload.target_amount,current_amount=payload.current_amount,currency=user.currency,deadline=payload.deadline);db.add(goal);db.flush();result={'goal_id':str(goal.id)}
    elif action.type=='set_alert':
        destination=str(payload.destination);notification=db.scalar(select(Notification).where(Notification.household_id==hid,Notification.channel=='email'))
        if not notification:notification=Notification(household_id=hid,channel='email',frequency=payload.frequency,destination=destination,locale=user.locale);db.add(notification)
        notification.frequency=payload.frequency;notification.destination=destination;notification.enabled=True;db.flush();result={'notification_id':str(notification.id)}
    audit(db,user,hid,'execute_ai_action',action.type,metadata={"confirmation_jti":claims['jti'],"fields":list(payload.model_dump(exclude_none=True))});db.commit();return {'ok':True,'type':action.type,'result':result}
