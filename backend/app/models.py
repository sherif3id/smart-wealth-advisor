from __future__ import annotations
import uuid
from datetime import date,datetime,timezone
from decimal import Decimal
from sqlalchemy import Boolean,CheckConstraint,Date,DateTime,ForeignKey,Index,Integer,JSON,Numeric,String,Text,UniqueConstraint,Uuid
from sqlalchemy.orm import Mapped,mapped_column,relationship
from .database import Base

def uid(): return uuid.uuid4()
def now(): return datetime.now(timezone.utc)

class User(Base):
    __tablename__="users"
    id:Mapped[uuid.UUID]=mapped_column(Uuid,primary_key=True,default=uid)
    email:Mapped[str]=mapped_column(String(320),unique=True,index=True)
    password_hash:Mapped[str]=mapped_column(String(255))
    name:Mapped[str]=mapped_column(String(120))
    locale:Mapped[str]=mapped_column(String(10),default="en")
    country:Mapped[str|None]=mapped_column(String(80))
    currency:Mapped[str]=mapped_column(String(3),default="USD")
    age:Mapped[int|None]=mapped_column(Integer)
    employment:Mapped[str|None]=mapped_column(String(80))
    risk_preference:Mapped[str|None]=mapped_column(String(40))
    investment_horizon:Mapped[int|None]=mapped_column(Integer)
    onboarding_complete:Mapped[bool]=mapped_column(Boolean,default=False)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,onupdate=now)

class Household(Base):
    __tablename__="households"
    id:Mapped[uuid.UUID]=mapped_column(Uuid,primary_key=True,default=uid)
    name:Mapped[str]=mapped_column(String(120));base_currency:Mapped[str]=mapped_column(String(3),default="USD")
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class HouseholdMember(Base):
    __tablename__="household_members";__table_args__=(UniqueConstraint("household_id","user_id"),UniqueConstraint("user_id",name="uq_single_household_per_user"))
    id:Mapped[uuid.UUID]=mapped_column(Uuid,primary_key=True,default=uid)
    household_id:Mapped[uuid.UUID]=mapped_column(ForeignKey("households.id",ondelete="CASCADE"),index=True)
    user_id:Mapped[uuid.UUID]=mapped_column(ForeignKey("users.id",ondelete="CASCADE"),index=True)
    role:Mapped[str]=mapped_column(String(20),default="owner")

class Account(Base):
    __tablename__="accounts";__table_args__=(CheckConstraint("balance >= 0",name="ck_account_balance_nonnegative"),)
    id:Mapped[uuid.UUID]=mapped_column(Uuid,primary_key=True,default=uid);household_id:Mapped[uuid.UUID]=mapped_column(ForeignKey("households.id",ondelete="CASCADE"),index=True)
    name:Mapped[str]=mapped_column(String(120));kind:Mapped[str]=mapped_column(String(30),default="checking");currency:Mapped[str]=mapped_column(String(3));balance:Mapped[Decimal]=mapped_column(Numeric(20,4),default=0);is_liquid:Mapped[bool]=mapped_column(Boolean,default=True);emergency_eligible:Mapped[bool]=mapped_column(Boolean,default=True);active:Mapped[bool]=mapped_column(Boolean,default=True);created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now);updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,onupdate=now)
class Category(Base):
    __tablename__="categories";__table_args__=(UniqueConstraint("household_id","name","kind"),Index("ix_categories_household_code","household_id","normalized_code"),)
    id:Mapped[uuid.UUID]=mapped_column(Uuid,primary_key=True,default=uid);household_id:Mapped[uuid.UUID]=mapped_column(ForeignKey("households.id",ondelete="CASCADE"),index=True);name:Mapped[str]=mapped_column(String(80));normalized_code:Mapped[str]=mapped_column(String(30),default="other");essential:Mapped[bool]=mapped_column(Boolean,default=False);kind:Mapped[str]=mapped_column(String(20))

class Transaction(Base):
    __tablename__="transactions";__table_args__=(CheckConstraint("amount > 0",name="ck_transaction_amount_positive"),Index("ix_transactions_household_date","household_id","occurred_on"))
    id:Mapped[uuid.UUID]=mapped_column(Uuid,primary_key=True,default=uid);household_id:Mapped[uuid.UUID]=mapped_column(ForeignKey("households.id",ondelete="CASCADE"),index=True);account_id:Mapped[uuid.UUID|None]=mapped_column(ForeignKey("accounts.id",ondelete="SET NULL"));category_id:Mapped[uuid.UUID|None]=mapped_column(ForeignKey("categories.id",ondelete="SET NULL"));kind:Mapped[str]=mapped_column(String(20));amount:Mapped[Decimal]=mapped_column(Numeric(20,4));currency:Mapped[str]=mapped_column(String(3));occurred_on:Mapped[date]=mapped_column(Date,index=True);description:Mapped[str]=mapped_column(String(300),default="");tags:Mapped[list]=mapped_column(JSON,default=list);recurring:Mapped[bool]=mapped_column(Boolean,default=False);created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now);updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,onupdate=now)

class Budget(Base):
    __tablename__="budgets";__table_args__=(UniqueConstraint("household_id","year","month"),CheckConstraint("month >= 1 AND month <= 12"))
    id:Mapped[uuid.UUID]=mapped_column(Uuid,primary_key=True,default=uid);household_id:Mapped[uuid.UUID]=mapped_column(ForeignKey("households.id",ondelete="CASCADE"),index=True);year:Mapped[int]=mapped_column(Integer);month:Mapped[int]=mapped_column(Integer);currency:Mapped[str]=mapped_column(String(3));savings_target:Mapped[Decimal]=mapped_column(Numeric(20,4),default=0);created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now);updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,onupdate=now)
class BudgetItem(Base):
    __tablename__="budget_items";__table_args__=(UniqueConstraint("budget_id","category"),CheckConstraint("limit_amount >= 0"),)
    id:Mapped[uuid.UUID]=mapped_column(Uuid,primary_key=True,default=uid);budget_id:Mapped[uuid.UUID]=mapped_column(ForeignKey("budgets.id",ondelete="CASCADE"),index=True);category:Mapped[str]=mapped_column(String(80));limit_amount:Mapped[Decimal]=mapped_column(Numeric(20,4));essential:Mapped[bool]=mapped_column(Boolean,default=False)

class Goal(Base):
    __tablename__="goals";__table_args__=(CheckConstraint("target_amount > 0"),CheckConstraint("current_amount >= 0"))
    id:Mapped[uuid.UUID]=mapped_column(Uuid,primary_key=True,default=uid);household_id:Mapped[uuid.UUID]=mapped_column(ForeignKey("households.id",ondelete="CASCADE"),index=True);name:Mapped[str]=mapped_column(String(140));target_amount:Mapped[Decimal]=mapped_column(Numeric(20,4));current_amount:Mapped[Decimal]=mapped_column(Numeric(20,4),default=0);currency:Mapped[str]=mapped_column(String(3));deadline:Mapped[date|None]=mapped_column(Date);priority:Mapped[int]=mapped_column(Integer,default=3);status:Mapped[str]=mapped_column(String(20),default="active");created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now);updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,onupdate=now)
class GoalContribution(Base):
    __tablename__="goal_contributions";__table_args__=(CheckConstraint("amount > 0"),)
    id:Mapped[uuid.UUID]=mapped_column(Uuid,primary_key=True,default=uid);goal_id:Mapped[uuid.UUID]=mapped_column(ForeignKey("goals.id",ondelete="CASCADE"),index=True);amount:Mapped[Decimal]=mapped_column(Numeric(20,4));contributed_on:Mapped[date]=mapped_column(Date,default=date.today);created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)

class Liability(Base):
    __tablename__="liabilities";__table_args__=(CheckConstraint("balance >= 0"),CheckConstraint("interest_rate >= 0 AND interest_rate <= 100"))
    id:Mapped[uuid.UUID]=mapped_column(Uuid,primary_key=True,default=uid);household_id:Mapped[uuid.UUID]=mapped_column(ForeignKey("households.id",ondelete="CASCADE"),index=True);name:Mapped[str]=mapped_column(String(140));kind:Mapped[str]=mapped_column(String(40));balance:Mapped[Decimal]=mapped_column(Numeric(20,4));monthly_payment:Mapped[Decimal]=mapped_column(Numeric(20,4),default=0);interest_rate:Mapped[Decimal]=mapped_column(Numeric(8,4),default=0);due_date:Mapped[date|None]=mapped_column(Date);currency:Mapped[str]=mapped_column(String(3));created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now);updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,onupdate=now)

class Portfolio(Base):
    __tablename__="portfolios"
    id:Mapped[uuid.UUID]=mapped_column(Uuid,primary_key=True,default=uid);household_id:Mapped[uuid.UUID]=mapped_column(ForeignKey("households.id",ondelete="CASCADE"),index=True);name:Mapped[str]=mapped_column(String(120));currency:Mapped[str]=mapped_column(String(3));created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class Position(Base):
    __tablename__="positions";__table_args__=(CheckConstraint("quantity >= 0"),)
    id:Mapped[uuid.UUID]=mapped_column(Uuid,primary_key=True,default=uid);portfolio_id:Mapped[uuid.UUID]=mapped_column(ForeignKey("portfolios.id",ondelete="CASCADE"),index=True);symbol:Mapped[str]=mapped_column(String(40));asset_class:Mapped[str]=mapped_column(String(60));quantity:Mapped[Decimal]=mapped_column(Numeric(24,8));cost_basis:Mapped[Decimal]=mapped_column(Numeric(20,4),default=0);current_price:Mapped[Decimal]=mapped_column(Numeric(20,4),default=0);currency:Mapped[str]=mapped_column(String(3));updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,onupdate=now)

class RiskAssessment(Base):
    __tablename__="risk_assessments"
    id:Mapped[uuid.UUID]=mapped_column(Uuid,primary_key=True,default=uid);household_id:Mapped[uuid.UUID]=mapped_column(ForeignKey("households.id",ondelete="CASCADE"),index=True);answers:Mapped[dict]=mapped_column(JSON);score:Mapped[Decimal]=mapped_column(Numeric(6,2));category:Mapped[str]=mapped_column(String(30));methodology_version:Mapped[str]=mapped_column(String(20),default="risk-v1");created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class FinancialSnapshot(Base):
    __tablename__="financial_snapshots"
    id:Mapped[uuid.UUID]=mapped_column(Uuid,primary_key=True,default=uid);household_id:Mapped[uuid.UUID]=mapped_column(ForeignKey("households.id",ondelete="CASCADE"),index=True);as_of:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now);data:Mapped[dict]=mapped_column(JSON);methodology_version:Mapped[str]=mapped_column(String(30),default="summary-v1")
class Recommendation(Base):
    __tablename__="recommendations"
    id:Mapped[uuid.UUID]=mapped_column(Uuid,primary_key=True,default=uid);household_id:Mapped[uuid.UUID]=mapped_column(ForeignKey("households.id",ondelete="CASCADE"),index=True);type:Mapped[str]=mapped_column(String(50));title:Mapped[str]=mapped_column(String(180));explanation:Mapped[str]=mapped_column(Text);reason:Mapped[str]=mapped_column(Text);estimated_impact:Mapped[Decimal|None]=mapped_column(Numeric(20,4));priority:Mapped[int]=mapped_column(Integer);related_entity_type:Mapped[str|None]=mapped_column(String(40));related_entity_id:Mapped[uuid.UUID|None]=mapped_column(Uuid);methodology_version:Mapped[str]=mapped_column(String(30),default="recommendations-v2");status:Mapped[str]=mapped_column(String(20),default="active");created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class Alert(Base):
    __tablename__="alerts"
    id:Mapped[uuid.UUID]=mapped_column(Uuid,primary_key=True,default=uid);household_id:Mapped[uuid.UUID]=mapped_column(ForeignKey("households.id",ondelete="CASCADE"),index=True);type:Mapped[str]=mapped_column(String(40));severity:Mapped[str]=mapped_column(String(20));title:Mapped[str]=mapped_column(String(180));message:Mapped[str]=mapped_column(Text);read_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True));created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class Notification(Base):
    __tablename__="notifications";__table_args__=(UniqueConstraint("household_id","channel",name="uq_notification_channel"),Index("ix_notifications_dispatch","enabled","last_sent_at"))
    id:Mapped[uuid.UUID]=mapped_column(Uuid,primary_key=True,default=uid);household_id:Mapped[uuid.UUID]=mapped_column(ForeignKey("households.id",ondelete="CASCADE"),index=True);channel:Mapped[str]=mapped_column(String(20));frequency:Mapped[str]=mapped_column(String(20));destination:Mapped[str];enabled:Mapped[bool]=mapped_column(Boolean,default=True);locale:Mapped[str]=mapped_column(String(10),default="en");last_sent_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True));created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class Scenario(Base):
    __tablename__="scenarios"
    id:Mapped[uuid.UUID]=mapped_column(Uuid,primary_key=True,default=uid);household_id:Mapped[uuid.UUID]=mapped_column(ForeignKey("households.id",ondelete="CASCADE"),index=True);name:Mapped[str]=mapped_column(String(120));inputs:Mapped[dict]=mapped_column(JSON);results:Mapped[dict]=mapped_column(JSON);seed:Mapped[int]=mapped_column(Integer);created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class Report(Base):
    __tablename__="reports"
    id:Mapped[uuid.UUID]=mapped_column(Uuid,primary_key=True,default=uid);household_id:Mapped[uuid.UUID]=mapped_column(ForeignKey("households.id",ondelete="CASCADE"),index=True);kind:Mapped[str]=mapped_column(String(50));locale:Mapped[str]=mapped_column(String(10));snapshot:Mapped[dict]=mapped_column(JSON);created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class AuditEvent(Base):
    __tablename__="audit_events";__table_args__=(Index("ix_audit_household_time","household_id","created_at"),)
    id:Mapped[uuid.UUID]=mapped_column(Uuid,primary_key=True,default=uid);household_id:Mapped[uuid.UUID|None]=mapped_column(Uuid,index=True);user_id:Mapped[uuid.UUID|None]=mapped_column(Uuid,index=True);action:Mapped[str]=mapped_column(String(100));resource_type:Mapped[str]=mapped_column(String(60));resource_id:Mapped[str|None]=mapped_column(String(80));metadata_json:Mapped[dict]=mapped_column(JSON,default=dict);created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class RevokedToken(Base):
    __tablename__="revoked_tokens"
    jti:Mapped[str]=mapped_column(String(64),primary_key=True);expires_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),index=True);created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class UsedConfirmationToken(Base):
    __tablename__="used_confirmation_tokens"
    jti:Mapped[str]=mapped_column(String(64),primary_key=True);user_id:Mapped[uuid.UUID]=mapped_column(Uuid,index=True);expires_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),index=True);used_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class AdvisorMessage(Base):
    __tablename__="advisor_messages";__table_args__=(Index("ix_advisor_household_time","household_id","created_at"),)
    id:Mapped[uuid.UUID]=mapped_column(Uuid,primary_key=True,default=uid);household_id:Mapped[uuid.UUID]=mapped_column(ForeignKey("households.id",ondelete="CASCADE"));role:Mapped[str]=mapped_column(String(20));content:Mapped[str]=mapped_column(Text);actions:Mapped[list]=mapped_column(JSON,default=list);created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
