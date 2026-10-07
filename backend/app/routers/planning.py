import json,uuid
from datetime import datetime,timezone
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import delete,select
from sqlalchemy.orm import Session
from ..auth import current_user,household_id
from ..database import get_db
from ..models import Alert,Recommendation,Report,User
from ..schemas import RecommendationDispositionIn,ReportCreateIn
from ..services import audit,financial_summary,generate_recommendations
from .analytics import collect_ml_insights

summary_router=APIRouter(tags=["Financial summary"]);recommendation_router=APIRouter(prefix="/recommendations",tags=["Recommendations"]);report_router=APIRouter(prefix="/reports",tags=["Reports"]);alert_router=APIRouter(prefix="/alerts",tags=["Alerts"])
@summary_router.get('/financial-summary')
def summary(year:int|None=None,month:int|None=None,user:User=Depends(current_user),db:Session=Depends(get_db)):return financial_summary(db,household_id(user,db),user,year,month)
@recommendation_router.post('/refresh')
def refresh(user:User=Depends(current_user),db:Session=Depends(get_db)):
    hid=household_id(user,db)
    try:ml=collect_ml_insights(db,hid,user)
    except HTTPException:ml=None
    items=generate_recommendations(db,hid,user,ml);audit(db,user,hid,'refresh','recommendations',metadata={"ml_available":ml is not None});db.commit();return items
@recommendation_router.get('')
def list_recommendations(user:User=Depends(current_user),db:Session=Depends(get_db)):
    hid=household_id(user,db);return db.scalars(select(Recommendation).where(Recommendation.household_id==hid,Recommendation.status=='active').order_by(Recommendation.priority,Recommendation.created_at.desc())).all()
@recommendation_router.patch('/{recommendation_id}')
def disposition(recommendation_id:uuid.UUID,payload:RecommendationDispositionIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    hid=household_id(user,db);item=db.scalar(select(Recommendation).where(Recommendation.id==recommendation_id,Recommendation.household_id==hid))
    if not item:raise HTTPException(404,detail={"code":"RECOMMENDATION_NOT_FOUND","message":"Recommendation not found"})
    item.status=payload.status;audit(db,user,hid,'disposition','recommendation',item.id,{"status":item.status});db.commit();return item
@report_router.post('',status_code=201)
def create_report(payload:ReportCreateIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    hid=household_id(user,db);snapshot=financial_summary(db,hid,user);recommendations=db.scalars(select(Recommendation).where(Recommendation.household_id==hid,Recommendation.status=='active')).all();data={"summary":snapshot,"recommendations":[{"type":item.type,"title":item.title,"explanation":item.explanation,"reason":item.reason,"estimated_impact":str(item.estimated_impact) if item.estimated_impact is not None else None,"priority":item.priority,"methodology_version":item.methodology_version} for item in recommendations],"generated_at":datetime.now(timezone.utc).isoformat(),"data_as_of":snapshot['data_as_of'],"methodology":snapshot['methodology'],"assumptions":["Calculations use recorded data in the household base currency","User-entered portfolio prices are not live market data","Projections and recommendations are educational and are not guaranteed"]};report=Report(household_id=hid,kind=payload.kind,locale=payload.locale,snapshot=json.loads(json.dumps(data,default=str)));db.add(report);db.flush();audit(db,user,hid,'create','report',report.id,{"kind":payload.kind});db.commit();return {"id":report.id,"kind":report.kind,"locale":report.locale,"created_at":report.created_at,"data":report.snapshot}
@report_router.get('')
def reports(user:User=Depends(current_user),db:Session=Depends(get_db)):
    hid=household_id(user,db);return db.scalars(select(Report).where(Report.household_id==hid).order_by(Report.created_at.desc()).limit(50)).all()
@report_router.delete('',status_code=204)
def clear_reports(user:User=Depends(current_user),db:Session=Depends(get_db)):
    hid=household_id(user,db);db.execute(delete(Report).where(Report.household_id==hid));audit(db,user,hid,'delete_all','report');db.commit()
@report_router.get('/{report_id}')
def report(report_id:uuid.UUID,user:User=Depends(current_user),db:Session=Depends(get_db)):
    hid=household_id(user,db);item=db.scalar(select(Report).where(Report.id==report_id,Report.household_id==hid))
    if not item:raise HTTPException(404,detail={"code":"REPORT_NOT_FOUND","message":"Report not found"})
    return item
@alert_router.get('')
def alerts(unread_only:bool=False,user:User=Depends(current_user),db:Session=Depends(get_db)):
    hid=household_id(user,db);query=select(Alert).where(Alert.household_id==hid)
    if unread_only:query=query.where(Alert.read_at==None)
    return db.scalars(query.order_by(Alert.created_at.desc()).limit(100)).all()
@alert_router.patch('/{alert_id}/read')
def mark_read(alert_id:uuid.UUID,user:User=Depends(current_user),db:Session=Depends(get_db)):
    hid=household_id(user,db);item=db.scalar(select(Alert).where(Alert.id==alert_id,Alert.household_id==hid))
    if not item:raise HTTPException(404,detail={"code":"ALERT_NOT_FOUND","message":"Alert not found"})
    item.read_at=datetime.now(timezone.utc);audit(db,user,hid,'read','alert',item.id);db.commit();return item
