import hashlib,logging,time,uuid
from contextlib import asynccontextmanager
from collections import defaultdict,deque
import httpx
from fastapi import FastAPI,HTTPException,Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from .config import get_settings
from .database import Base,engine
from .routers import accounts,advisor,ai_actions,analytics,auth,budgets,goals,liabilities,notifications,planning,risk_portfolio,transactions

settings=get_settings();logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(name)s %(message)s');logger=logging.getLogger('smart_wealth.core')
@asynccontextmanager
async def lifespan(_:FastAPI):
    if settings.auto_create_tables:
        if settings.app_env.lower()=='production':raise RuntimeError('AUTO_CREATE_TABLES is forbidden in production')
        Base.metadata.create_all(engine)
    yield
app=FastAPI(title='Smart Wealth Core API',version='2.0.0',description='Authoritative financial API. Authenticate with a Bearer JWT.',lifespan=lifespan);app.add_middleware(CORSMiddleware,allow_origins=settings.origins,allow_credentials=True,allow_methods=['GET','POST','PUT','PATCH','DELETE'],allow_headers=['Authorization','Content-Type'])
requests=defaultdict(deque)
@app.middleware('http')
async def security_and_rate_limit(request:Request,call_next):
    request_id=request.headers.get('x-request-id') or uuid.uuid4().hex;direct_ip=request.client.host if request.client else 'unknown';forwarded=request.headers.get('x-forwarded-for','').split(',')[0].strip();client_ip=forwarded if settings.trust_proxy_headers and forwarded else direct_ip;authorization=request.headers.get('authorization','');identity=hashlib.sha256(authorization.encode()).hexdigest()[:16] if authorization else client_ip;key=f"{identity}:{request.url.path}";now=time.time();bucket=requests[key]
    while bucket and bucket[0]<now-60:bucket.popleft()
    limit=20 if request.url.path.startswith('/auth/') else 180
    if len(bucket)>=limit:return JSONResponse(status_code=429,content={'error':{'code':'RATE_LIMITED','message':'Too many requests; retry later'}},headers={'x-request-id':request_id})
    bucket.append(now);started=time.monotonic();response=await call_next(request);response.headers['X-Content-Type-Options']='nosniff';response.headers['X-Frame-Options']='DENY';response.headers['Referrer-Policy']='no-referrer';response.headers['Cache-Control']='no-store';response.headers['X-Request-ID']=request_id
    if response.status_code>=400:logger.warning('request_failed method=%s path=%s status=%s request_id=%s duration_ms=%d',request.method,request.url.path,response.status_code,request_id,(time.monotonic()-started)*1000)
    return response
@app.exception_handler(HTTPException)
async def http_error(_:Request,exc:HTTPException):
    detail=exc.detail if isinstance(exc.detail,dict) else {'code':'REQUEST_ERROR','message':str(exc.detail)};return JSONResponse(status_code=exc.status_code,content={'error':detail},headers=exc.headers)
@app.exception_handler(RequestValidationError)
async def validation_error(_:Request,exc:RequestValidationError):return JSONResponse(status_code=422,content={'error':{'code':'VALIDATION_ERROR','message':'Request validation failed','details':{'fields':jsonable_encoder(exc.errors())}}})
@app.exception_handler(Exception)
async def unhandled(request:Request,exc:Exception):
    logger.exception('unhandled_error path=%s',request.url.path);return JSONResponse(status_code=500,content={'error':{'code':'INTERNAL_ERROR','message':'An unexpected server error occurred'}})
@app.get('/health/live',tags=['System'])
def live():return {'service':True,'version':app.version}
def readiness_payload():
    database={'ready':False};ml={'service':False,'models_ready':False}
    try:
        with engine.connect() as connection:connection.execute(text('SELECT 1'));database={'ready':True}
    except Exception as exc:database={'ready':False,'error':type(exc).__name__}
    try:
        response=httpx.get(f"{settings.ml_service_url}/health/ready",timeout=min(settings.request_timeout_seconds,3));body=response.json() if response.status_code==200 else {};ml={'service':response.status_code==200,'models_ready':bool(body.get('ready')),'models':body.get('models',{})}
    except Exception:ml={'service':False,'models_ready':False}
    return {'ready':database['ready'],'environment':settings.app_env,'database':database,'ml':ml,'required_configuration':{'jwt_secret':bool(settings.jwt_secret),'cors_origins':bool(settings.origins)}}
@app.get('/health/ready',tags=['System'])
def ready():
    payload=readiness_payload();return JSONResponse(status_code=200 if payload['ready'] else 503,content=payload)
@app.get('/health',tags=['System'])
def health():
    payload=readiness_payload();return JSONResponse(status_code=200 if payload['ready'] else 503,content=payload)
for router in [auth.router,auth.profile_router,accounts.router,transactions.router,transactions.income_router,budgets.router,goals.router,liabilities.router,planning.summary_router,planning.recommendation_router,planning.report_router,planning.alert_router,risk_portfolio.risk_router,risk_portfolio.portfolio_router,analytics.scenario_router,analytics.ml_router,ai_actions.router,advisor.router,notifications.router]:app.include_router(router)
