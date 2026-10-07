from datetime import datetime,timezone
from fastapi import APIRouter,Depends,HTTPException,status
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..auth import cleanup_revoked_tokens,create_token,current_token_claims,current_user,hash_password,verify_password
from ..database import get_db
from ..models import Account,Household,HouseholdMember,RevokedToken,User
from ..schemas import LoginIn,ProfileIn,ProfileOut,RegisterIn,TokenOut

router=APIRouter(prefix="/auth",tags=["Authentication"])
@router.post('/register',response_model=TokenOut,status_code=201)
def register(data:RegisterIn,db:Session=Depends(get_db)):
    if db.scalar(select(User).where(User.email==str(data.email))):raise HTTPException(409,detail={"code":"EMAIL_EXISTS","message":"An account already exists for this email"})
    cleanup_revoked_tokens(db);user=User(email=str(data.email),password_hash=hash_password(data.password),name=data.name.strip(),locale=data.locale);db.add(user);db.flush();household=Household(name=f"{data.name.strip()}'s household",base_currency='USD');db.add(household);db.flush();db.add(HouseholdMember(household_id=household.id,user_id=user.id,role='owner'));db.add(Account(household_id=household.id,name='Primary cash',kind='checking',currency='USD',balance=0,is_liquid=True,emergency_eligible=True));db.commit();token,ttl=create_token(user.id);return TokenOut(access_token=token,expires_in=ttl)
@router.post('/login',response_model=TokenOut)
def login(data:LoginIn,db:Session=Depends(get_db)):
    user=db.scalar(select(User).where(User.email==str(data.email)))
    if not user or not verify_password(data.password,user.password_hash):raise HTTPException(status.HTTP_401_UNAUTHORIZED,detail={"code":"INVALID_CREDENTIALS","message":"Email or password is incorrect"})
    cleanup_revoked_tokens(db);db.commit();token,ttl=create_token(user.id);return TokenOut(access_token=token,expires_in=ttl)
@router.get('/me')
def me(user:User=Depends(current_user)):
    return {"id":user.id,"email":user.email,"name":user.name,"locale":user.locale,"country":user.country,"currency":user.currency,"age":user.age,"employment":user.employment,"risk_preference":user.risk_preference,"investment_horizon":user.investment_horizon,"onboarding_complete":user.onboarding_complete}
@router.post('/logout',status_code=204)
def logout(claims:dict=Depends(current_token_claims),user:User=Depends(current_user),db:Session=Depends(get_db)):
    # Revoke only the bearer token used for this authenticated request.
    if claims['sub']!=str(user.id):raise HTTPException(403,detail={"code":"TOKEN_SUBJECT_MISMATCH","message":"Token subject mismatch"})
    cleanup_revoked_tokens(db);db.merge(RevokedToken(jti=claims['jti'],expires_at=datetime.fromtimestamp(claims['exp'],timezone.utc)));db.commit()

profile_router=APIRouter(prefix="/profile",tags=["Profile"])
@profile_router.get('',response_model=ProfileOut)
def get_profile(user:User=Depends(current_user)):return user
@profile_router.put('',response_model=ProfileOut)
def update_profile(data:ProfileIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    for key,value in data.model_dump().items():setattr(user,key,value)
    memberships=db.scalars(select(HouseholdMember).where(HouseholdMember.user_id==user.id)).all()
    if len(memberships)!=1:raise HTTPException(409,detail={"code":"HOUSEHOLD_CONTEXT_AMBIGUOUS","message":"Exactly one household is required"})
    household=db.get(Household,memberships[0].household_id);household.base_currency=data.currency
    for account in db.scalars(select(Account).where(Account.household_id==household.id)).all():account.currency=data.currency
    db.commit();db.refresh(user);return user
