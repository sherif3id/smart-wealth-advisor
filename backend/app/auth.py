import uuid
from datetime import datetime,timedelta,timezone
import jwt
from fastapi import Depends,HTTPException,status
from fastapi.security import HTTPAuthorizationCredentials,HTTPBearer
from jwt import InvalidTokenError
from pwdlib import PasswordHash
from sqlalchemy import delete,select
from sqlalchemy.orm import Session
from .config import get_settings
from .database import get_db
from .models import HouseholdMember,RevokedToken,User

password_hash=PasswordHash.recommended();bearer=HTTPBearer(auto_error=False);settings=get_settings()
def hash_password(password:str)->str:return password_hash.hash(password)
def verify_password(password:str,hashed:str)->bool:
    try:return password_hash.verify(password,hashed)
    except Exception:return False

def cleanup_revoked_tokens(db:Session):db.execute(delete(RevokedToken).where(RevokedToken.expires_at<datetime.now(timezone.utc)))
def create_token(user_id:uuid.UUID)->tuple[str,int]:
    minutes=settings.access_token_minutes;now=datetime.now(timezone.utc);payload={"sub":str(user_id),"jti":uuid.uuid4().hex,"iat":now,"nbf":now,"exp":now+timedelta(minutes=minutes),"iss":settings.jwt_issuer,"aud":settings.jwt_audience,"typ":"access"};return jwt.encode(payload,settings.jwt_secret,algorithm=settings.jwt_algorithm),minutes*60
def decode_token(token:str)->dict:
    try:
        data=jwt.decode(token,settings.jwt_secret,algorithms=[settings.jwt_algorithm],issuer=settings.jwt_issuer,audience=settings.jwt_audience,options={"require":["sub","jti","iat","nbf","exp","iss","aud","typ"]})
        if data.get("typ")!="access":raise InvalidTokenError("wrong token type")
        uuid.UUID(data["sub"]);return data
    except (InvalidTokenError,ValueError,KeyError) as exc:raise HTTPException(status.HTTP_401_UNAUTHORIZED,detail={"code":"INVALID_TOKEN","message":"Authentication token is invalid or expired"}) from exc

def current_token_claims(credentials:HTTPAuthorizationCredentials|None=Depends(bearer))->dict:
    if not credentials or credentials.scheme.lower()!='bearer':raise HTTPException(status.HTTP_401_UNAUTHORIZED,detail={"code":"AUTH_REQUIRED","message":"Authentication is required"})
    return decode_token(credentials.credentials)
def current_user(claims:dict=Depends(current_token_claims),db:Session=Depends(get_db))->User:
    revoked=db.get(RevokedToken,claims["jti"])
    if revoked:raise HTTPException(status.HTTP_401_UNAUTHORIZED,detail={"code":"TOKEN_REVOKED","message":"Session has been logged out"})
    user=db.get(User,uuid.UUID(claims["sub"]))
    if not user:raise HTTPException(status.HTTP_401_UNAUTHORIZED,detail={"code":"USER_NOT_FOUND","message":"User no longer exists"})
    return user

def household_id(user:User,db:Session)->uuid.UUID:
    memberships=db.scalars(select(HouseholdMember).where(HouseholdMember.user_id==user.id)).all()
    if not memberships:raise HTTPException(403,detail={"code":"NO_HOUSEHOLD","message":"User has no household"})
    if len(memberships)!=1:raise HTTPException(409,detail={"code":"HOUSEHOLD_CONTEXT_AMBIGUOUS","message":"This deployment supports exactly one household per user"})
    return memberships[0].household_id
