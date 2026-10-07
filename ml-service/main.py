from __future__ import annotations
from pathlib import Path
import os
import joblib,pandas as pd
from fastapi import FastAPI,HTTPException
from pydantic import BaseModel,Field
from feature_definitions import CATEGORY_COLUMNS,CONTRACT_VERSION,MODEL_VERSION,payload_to_frame

ROOT=Path(__file__).parent;MODELS=Path(os.getenv("ML_MODELS_DIR",str(ROOT/"models")));ARTIFACTS={"expense":"expense_model.joblib","anomaly":"anomaly_model.joblib","behavior":"behavior_model.joblib"}
APP_ENV=os.getenv("APP_ENV","development").lower();ALLOW_SYNTHETIC_DEMO=os.getenv("ML_ALLOW_SYNTHETIC_DEMO","false").lower() in {"1","true","yes"}
app=FastAPI(title="Smart Wealth ML Service",version=MODEL_VERSION)

def load(name:str):
    path=MODELS/name
    if not path.exists():raise HTTPException(503,detail={"code":"MODEL_UNAVAILABLE","message":f"{name} is not trained/deployed"})
    try:bundle=joblib.load(path)
    except Exception as exc:raise HTTPException(503,detail={"code":"MODEL_UNLOADABLE","message":f"{name} could not be loaded"}) from exc
    if bundle.get("feature_contract_version")!=CONTRACT_VERSION:raise HTTPException(503,detail={"code":"MODEL_CONTRACT_MISMATCH","message":f"{name} uses an incompatible feature contract"})
    if bundle.get("dataset_classification")=="synthetic-demo" and (APP_ENV=="production" or not ALLOW_SYNTHETIC_DEMO):raise HTTPException(503,detail={"code":"SYNTHETIC_MODEL_NOT_ALLOWED","message":f"{name} is a synthetic demo artifact and cannot be used in this environment"})
    return bundle

class FinancialVector(BaseModel):
    income:float=Field(ge=0);food:float=Field(ge=0);transport:float=Field(ge=0);shopping:float=Field(ge=0);bills:float=Field(ge=0);housing:float=Field(ge=0);health:float=Field(ge=0);entertainment:float=Field(ge=0);monthly_debt_payments:float=Field(ge=0);monthly_surplus:float
    def frame(self):return payload_to_frame(self.model_dump())

@app.get("/health/live")
def live():return {"service":True,"version":MODEL_VERSION}
@app.get("/health/ready")
def ready():
    models={};ready_count=0
    for key,file_name in ARTIFACTS.items():
        try:bundle=load(file_name);models[key]={"status":"ready","model_version":bundle.get("model_version"),"feature_contract_version":bundle.get("feature_contract_version"),"dataset_classification":bundle.get("dataset_classification","unknown"),"production_eligible":bool(bundle.get("production_eligible",False))};ready_count+=1
        except HTTPException as exc:models[key]={"status":"unavailable","reason":exc.detail.get("code") if isinstance(exc.detail,dict) else "MODEL_UNAVAILABLE"}
    return {"service":True,"ready":ready_count==len(ARTIFACTS),"models":models}
@app.get("/health")
def health():return ready()

@app.post("/predict-expenses")
def predict(vector:FinancialVector):
    bundle=load(ARTIFACTS["expense"]);frame=vector.frame();value=max(0,float(bundle["model"].predict(frame[bundle["features"]])[0]));return {"predicted_expense":round(value,2),"model":bundle["name"],"model_version":bundle["model_version"],"feature_contract_version":CONTRACT_VERSION,"period":"monthly observation","classification":"educational projection","dataset_classification":bundle.get("dataset_classification","unknown"),"production_eligible":bool(bundle.get("production_eligible",False)),"note":"A model projection is not a guarantee or market forecast"}
@app.post("/check-expense")
def anomaly(vector:FinancialVector):
    bundle=load(ARTIFACTS["anomaly"]);data=vector.model_dump();frame=pd.DataFrame([[data[key] for key in bundle["features"]]],columns=bundle["features"]);score=float(bundle["model"].decision_function(frame)[0]);medians=bundle.get("training_medians",{});ratios={key:data[key]/max(float(medians.get(key,0)),1) for key in bundle["features"]};dominant=max(ratios,key=ratios.get);return {"is_anomaly":bool(bundle["model"].predict(frame)[0]==-1),"anomaly_score":round(score,5),"detection_scope":"unusual monthly category-level spending pattern","context":{"largest_relative_category":dominant,"multiple_of_training_median":round(ratios[dominant],2)},"model_version":bundle["model_version"],"dataset_classification":bundle.get("dataset_classification","unknown"),"production_eligible":bool(bundle.get("production_eligible",False)),"note":"Negative scores are more unusual. Context is descriptive, not causal, and this is not fraud detection."}
@app.post("/financial-profile")
def profile(vector:FinancialVector):
    bundle=load(ARTIFACTS["behavior"]);frame=vector.frame()[bundle["features"]];cluster=int(bundle["model"].predict(frame)[0]);scaled=bundle["model"][:-1].transform(frame);distances=bundle["model"].named_steps["model"].transform(scaled)[0];return {"cluster":cluster,"profile":bundle["labels"][cluster],"distance_to_centroid":round(float(distances[cluster]),5),"model_version":bundle["model_version"],"dataset_classification":bundle.get("dataset_classification","unknown"),"production_eligible":bool(bundle.get("production_eligible",False)),"note":"Distance to centroid is not a probability or confidence score"}
