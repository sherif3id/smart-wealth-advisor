from __future__ import annotations
import uuid
from datetime import date,datetime
from decimal import Decimal
from typing import Annotated,Any,Literal,Union
from pydantic import BaseModel,ConfigDict,EmailStr,Field,field_validator,model_validator
DateValue=date

class ORM(BaseModel): model_config=ConfigDict(from_attributes=True)
class ErrorBody(BaseModel): code:str;message:str;details:dict|None=None
class ErrorResponse(BaseModel): error:ErrorBody
class RegisterIn(BaseModel):
 email:EmailStr;password:str=Field(min_length=12,max_length=128);name:str=Field(min_length=2,max_length=120);locale:Literal['en','ar']='en'
 @field_validator('email')
 @classmethod
 def normalize_email(cls,value):return str(value).strip().casefold()
 @field_validator('password')
 @classmethod
 def password_policy(cls,value):
  if not any(c.islower() for c in value) or not any(c.isupper() for c in value) or not any(c.isdigit() for c in value) or not any(not c.isalnum() for c in value):raise ValueError('Password must include upper, lower, digit, and symbol characters')
  return value
class LoginIn(BaseModel):
 email:EmailStr;password:str=Field(min_length=1,max_length=128)
 @field_validator('email')
 @classmethod
 def normalize_email(cls,value):return str(value).strip().casefold()
class TokenOut(BaseModel): access_token:str;token_type:str='bearer';expires_in:int
class ProfileIn(BaseModel):
 name:str=Field(min_length=2,max_length=120);locale:Literal['en','ar']='en';country:str=Field(min_length=2,max_length=80);currency:str=Field(pattern='^[A-Z]{3}$');age:int=Field(ge=18,le=100);employment:str=Field(min_length=2,max_length=80);risk_preference:Literal['Conservative','Balanced','Growth','Aggressive'];investment_horizon:int=Field(ge=1,le=60);onboarding_complete:bool=True
class ProfileOut(ProfileIn): id:uuid.UUID;email:EmailStr;created_at:datetime

TransactionKind=Literal['income','expense','transfer']
class TransactionIn(BaseModel):
 kind:TransactionKind;amount:Decimal=Field(gt=0,max_digits=20,decimal_places=4);currency:str=Field(pattern='^[A-Z]{3}$');occurred_on:date;description:str=Field(default='',max_length=300);category:str|None=Field(default=None,max_length=80);account_id:uuid.UUID|None=None;tags:list[str]=Field(default_factory=list,max_length=20);recurring:bool=False
 @field_validator('tags')
 @classmethod
 def clean_tags(cls,v): return list(dict.fromkeys(x.strip()[:40] for x in v if x.strip()))
class TransactionPatch(BaseModel):
 kind:TransactionKind|None=None;amount:Decimal|None=Field(default=None,gt=0);currency:str|None=Field(default=None,pattern='^[A-Z]{3}$');occurred_on:date|None=None;description:str|None=Field(default=None,max_length=300);category:str|None=Field(default=None,max_length=80);account_id:uuid.UUID|None=None;tags:list[str]|None=None;recurring:bool|None=None
class TransactionOut(ORM): id:uuid.UUID;kind:str;amount:Decimal;currency:str;occurred_on:date;description:str;category:str|None=None;category_code:str|None=None;essential:bool=False;account_id:uuid.UUID|None;tags:list;recurring:bool;created_at:datetime;updated_at:datetime
class Page(BaseModel): items:list[Any];page:int;page_size:int;total:int;pages:int

AccountKind=Literal['cash','checking','savings','money_market','other']
class AccountIn(BaseModel):
 name:str=Field(min_length=2,max_length=120);kind:AccountKind='checking';currency:str=Field(pattern='^[A-Z]{3}$');balance:Decimal=Field(default=Decimal('0'),ge=0,max_digits=20,decimal_places=4);is_liquid:bool=True;emergency_eligible:bool=True;active:bool=True
class AccountPatch(BaseModel):
 name:str|None=Field(default=None,min_length=2,max_length=120);balance:Decimal|None=Field(default=None,ge=0,max_digits=20,decimal_places=4);is_liquid:bool|None=None;emergency_eligible:bool|None=None;active:bool|None=None
class AccountOut(ORM):
 id:uuid.UUID;name:str;kind:str;currency:str;balance:Decimal;is_liquid:bool;emergency_eligible:bool;active:bool;created_at:datetime;updated_at:datetime

class BudgetItemIn(BaseModel): category:str=Field(min_length=1,max_length=80);limit_amount:Decimal=Field(ge=0);essential:bool=False
class BudgetIn(BaseModel): year:int=Field(ge=2000,le=2200);month:int=Field(ge=1,le=12);currency:str=Field(pattern='^[A-Z]{3}$');savings_target:Decimal=Field(default=Decimal('0'),ge=0);items:list[BudgetItemIn]=Field(min_length=1,max_length=100)
class BudgetItemOut(BudgetItemIn): spent:Decimal;remaining:Decimal;utilization:float;over_budget:bool
class BudgetOut(BaseModel): id:uuid.UUID;year:int;month:int;currency:str;savings_target:Decimal;total_limit:Decimal;total_spent:Decimal;remaining:Decimal;projected_spending:Decimal;items:list[BudgetItemOut]

class GoalIn(BaseModel): name:str=Field(min_length=2,max_length=140);target_amount:Decimal=Field(gt=0);current_amount:Decimal=Field(default=Decimal('0'),ge=0);currency:str=Field(pattern='^[A-Z]{3}$');deadline:date|None=None;priority:int=Field(default=3,ge=1,le=5)
class GoalPatch(BaseModel): name:str|None=Field(default=None,min_length=2,max_length=140);target_amount:Decimal|None=Field(default=None,gt=0);current_amount:Decimal|None=Field(default=None,ge=0);deadline:date|None=None;priority:int|None=Field(default=None,ge=1,le=5);status:Literal['active','completed','paused','cancelled']|None=None
class ContributionIn(BaseModel): amount:Decimal=Field(gt=0);contributed_on:date=Field(default_factory=date.today)
class GoalOut(ORM): id:uuid.UUID;name:str;target_amount:Decimal;current_amount:Decimal;currency:str;deadline:date|None;priority:int;status:str;created_at:datetime;remaining_amount:Decimal|None=None;progress_percent:float|None=None;required_monthly_saving:Decimal|None=None;projected_completion_date:date|None=None

class LiabilityIn(BaseModel): name:str=Field(min_length=2,max_length=140);kind:str=Field(min_length=2,max_length=40);balance:Decimal=Field(ge=0);monthly_payment:Decimal=Field(default=Decimal('0'),ge=0);interest_rate:Decimal=Field(default=Decimal('0'),ge=0,le=100);due_date:date|None=None;currency:str=Field(pattern='^[A-Z]{3}$')
class LiabilityPatch(BaseModel): name:str|None=None;balance:Decimal|None=Field(default=None,ge=0);monthly_payment:Decimal|None=Field(default=None,ge=0);interest_rate:Decimal|None=Field(default=None,ge=0,le=100);due_date:date|None=None
class LiabilityOut(ORM): id:uuid.UUID;name:str;kind:str;balance:Decimal;monthly_payment:Decimal;interest_rate:Decimal;due_date:date|None;currency:str

class RiskIn(BaseModel): answers:dict[str,int]
class RiskOut(BaseModel): id:uuid.UUID;score:float;category:str;methodology_version:str;created_at:datetime
class PositionIn(BaseModel): symbol:str=Field(min_length=1,max_length=40);asset_class:str=Field(min_length=2,max_length=60);quantity:Decimal=Field(ge=0);cost_basis:Decimal=Field(ge=0);current_price:Decimal=Field(ge=0);currency:str=Field(pattern='^[A-Z]{3}$')
class PortfolioIn(BaseModel): name:str=Field(min_length=2,max_length=120);currency:str=Field(pattern='^[A-Z]{3}$')
class MonteCarloIn(BaseModel): initial_capital:float=Field(ge=0,le=1_000_000_000);monthly_contribution:float=Field(ge=0,le=10_000_000);horizon_years:int=Field(ge=1,le=60);expected_return:float=Field(ge=-.5,le=.5);volatility:float=Field(ge=0,le=1);inflation:float=Field(default=.03,ge=-.05,le=.25);simulations:int=Field(default=10000,ge=1000,le=100000);goal_amount:float|None=Field(default=None,ge=0,le=10_000_000_000);seed:int=Field(default=42,ge=0,le=2_147_483_647)
class AIProfilePayload(BaseModel):
 employment:str|None=Field(default=None,min_length=2,max_length=80);risk_preference:Literal['Conservative','Balanced','Growth','Aggressive']|None=None;investment_horizon:int|None=Field(default=None,ge=1,le=60)
 @model_validator(mode='after')
 def nonempty(self):
  if not self.model_fields_set:raise ValueError('At least one profile field is required')
  return self
class AITransactionPayload(BaseModel): kind:Literal['income','expense'];amount:Decimal=Field(gt=0,max_digits=20,decimal_places=4);category:str=Field(default='Other',min_length=1,max_length=80);date:DateValue=Field(default_factory=DateValue.today);description:str=Field(default='',max_length=300)
class AIBudgetPayload(BaseModel): category:str=Field(min_length=1,max_length=80);limit:Decimal=Field(ge=0,max_digits=20,decimal_places=4)
class AIGoalPayload(BaseModel): name:str=Field(min_length=2,max_length=140);target_amount:Decimal=Field(gt=0,max_digits=20,decimal_places=4);current_amount:Decimal=Field(default=Decimal('0'),ge=0,max_digits=20,decimal_places=4);deadline:date|None=None
class AIAlertPayload(BaseModel): frequency:Literal['daily','weekly','monthly'];destination:EmailStr
class AIProfileAction(BaseModel): type:Literal['update_profile'];payload:AIProfilePayload
class AITransactionAction(BaseModel): type:Literal['add_transaction'];payload:AITransactionPayload
class AIBudgetAction(BaseModel): type:Literal['update_budget'];payload:AIBudgetPayload
class AIGoalAction(BaseModel): type:Literal['save_goal'];payload:AIGoalPayload
class AIAlertAction(BaseModel): type:Literal['set_alert'];payload:AIAlertPayload
AIAction=Annotated[Union[AIProfileAction,AITransactionAction,AIBudgetAction,AIGoalAction,AIAlertAction],Field(discriminator='type')]
class AIActionPrepareIn(BaseModel): action:AIAction
class AIActionExecuteIn(BaseModel): action:AIAction;confirmation_token:str=Field(min_length=16,max_length=1000)
class AdvisorMessageIn(BaseModel): user:str=Field(default='',max_length=4000);assistant:str=Field(default='',max_length=8000)
class RecommendationDispositionIn(BaseModel): status:Literal['accepted','dismissed']
class ReportCreateIn(BaseModel): kind:Literal['health','wealth','spending','risk','retirement','action','monthly']='health';locale:Literal['en','ar']='en'
class NotificationSettingsIn(BaseModel): email:EmailStr;frequency:Literal['daily','weekly','monthly'];enabled:bool=True;locale:Literal['en','ar']='en'
