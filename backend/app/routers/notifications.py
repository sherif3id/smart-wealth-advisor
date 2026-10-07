import hmac,smtplib
from datetime import datetime,timedelta,timezone
from email.message import EmailMessage
from fastapi import APIRouter,Depends,HTTPException,Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..auth import current_user,household_id
from ..config import get_settings
from ..database import get_db
from ..models import HouseholdMember,Notification,User
from ..schemas import NotificationSettingsIn
from ..services import audit,financial_summary

router=APIRouter(prefix='/notifications',tags=['Notifications']);settings=get_settings()
def delivery_configured():return bool(settings.smtp_host and settings.smtp_user and settings.smtp_pass)
@router.get('')
def notification_settings(user:User=Depends(current_user),db:Session=Depends(get_db)):
    hid=household_id(user,db);item=db.scalar(select(Notification).where(Notification.household_id==hid,Notification.channel=='email'));return {'configured':bool(item),'email':item.destination if item else user.email,'frequency':item.frequency if item else 'weekly','enabled':item.enabled if item else False,'locale':item.locale if item else user.locale,'delivery_available':delivery_configured(),'last_sent_at':item.last_sent_at if item else None}
@router.put('')
def save(data:NotificationSettingsIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    hid=household_id(user,db);item=db.scalar(select(Notification).where(Notification.household_id==hid,Notification.channel=='email'))
    if not item:item=Notification(household_id=hid,channel='email',frequency=data.frequency,destination=str(data.email));db.add(item)
    item.destination=str(data.email);item.frequency=data.frequency;item.locale=data.locale;item.enabled=data.enabled;db.flush();audit(db,user,hid,'upsert','notification',item.id);db.commit();return {'saved':True,'delivery_available':delivery_configured()}
def deliver(to:str,locale:str,summary:dict):
    if not delivery_configured():raise HTTPException(503,detail={'code':'EMAIL_NOT_CONFIGURED','message':'SMTP delivery is not configured'})
    message=EmailMessage();message['From']=settings.notification_from;message['To']=to;message['Subject']='ملخص Smart Wealth Advisor' if locale=='ar' else 'Smart Wealth Advisor summary';income=summary['total_income'];expense=summary['total_expenses'];message.set_content(f"الدخل: {income}\nالمصروفات: {expense}\nهذه معلومات تعليمية وليست ضمانًا للنتائج." if locale=='ar' else f"Income: {income}\nExpenses: {expense}\nThis is educational information, not a guarantee of outcomes.")
    try:
        with smtplib.SMTP_SSL(settings.smtp_host,settings.smtp_port,timeout=10) as smtp:smtp.login(settings.smtp_user,settings.smtp_pass);smtp.send_message(message)
    except Exception as exc:raise HTTPException(502,detail={'code':'EMAIL_DELIVERY_FAILED','message':'Email delivery failed'}) from exc
@router.post('/test')
def send_test(user:User=Depends(current_user),db:Session=Depends(get_db)):
    hid=household_id(user,db);item=db.scalar(select(Notification).where(Notification.household_id==hid,Notification.channel=='email',Notification.enabled==True))
    if not item:raise HTTPException(404,detail={'code':'NOTIFICATION_NOT_FOUND','message':'Enable email notifications first'})
    deliver(item.destination,item.locale,financial_summary(db,hid,user));item.last_sent_at=datetime.now(timezone.utc);audit(db,user,hid,'deliver_test','notification',item.id);db.commit();return {'sent':True,'delivered':True}
def is_due(item:Notification,now:datetime):
    last=item.last_sent_at
    if last is None:return True
    if last.tzinfo is None:last=last.replace(tzinfo=timezone.utc)
    if item.frequency=='daily':return last<=now-timedelta(days=1)
    if item.frequency=='weekly':return last<=now-timedelta(days=7)
    return (last.year,last.month)!=(now.year,now.month)
@router.post('/dispatch')
def dispatch(request:Request,db:Session=Depends(get_db)):
    supplied=request.headers.get('x-cron-secret','')
    if not settings.cron_secret or not hmac.compare_digest(supplied,settings.cron_secret):raise HTTPException(401,detail={'code':'INVALID_CRON_SECRET','message':'Unauthorized dispatcher'})
    now=datetime.now(timezone.utc);sent=failed=skipped=0
    for item in db.scalars(select(Notification).where(Notification.enabled==True).order_by(Notification.last_sent_at)).all():
        if not is_due(item,now):skipped+=1;continue
        memberships=db.scalars(select(HouseholdMember).where(HouseholdMember.household_id==item.household_id,HouseholdMember.role=='owner')).all();user=db.get(User,memberships[0].user_id) if len(memberships)==1 else None
        if not user:failed+=1;continue
        try:deliver(item.destination,item.locale,financial_summary(db,item.household_id,user));item.last_sent_at=now;sent+=1;audit(db,user,item.household_id,'deliver','notification',item.id)
        except HTTPException:failed+=1
    db.commit();return {'sent':sent,'failed':failed,'skipped_not_due':skipped,'checked_at':now,'delivered':sent>0}
