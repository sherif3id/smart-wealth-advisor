"""Train Smart Wealth models from deterministic monthly observations.

Each row is one user-month. Required columns are defined in feature_definitions.py.
The final chronological test period is touched only after model selection.
"""
from __future__ import annotations
import argparse,hashlib,json,platform
from datetime import datetime,timezone
from pathlib import Path
import joblib,numpy as np,pandas as pd,sklearn
from sklearn.cluster import KMeans
from sklearn.ensemble import GradientBoostingRegressor,IsolationForest,RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error,mean_squared_error,r2_score,silhouette_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler,StandardScaler
from feature_definitions import CATEGORY_COLUMNS,CLUSTER_COLUMNS,CONTRACT_VERSION,ENGINEERED_COLUMNS,MODEL_VERSION,RAW_COLUMNS,TARGET,engineer_frame,unique_cluster_labels

def regression_pipeline(model):return Pipeline([("impute",SimpleImputer(strategy="median")),("scale",RobustScaler()),("model",model)])
def evaluate(model,x,y):
    prediction=np.maximum(0,model.predict(x));return {"mae":float(mean_absolute_error(y,prediction)),"rmse":float(mean_squared_error(y,prediction)**.5),"r2":float(r2_score(y,prediction))}

def main(csv_path:str,out_dir:str,synthetic:bool=False):
    source=Path(csv_path);out=Path(out_dir);out.mkdir(parents=True,exist_ok=True);df=pd.read_csv(source).drop_duplicates()
    required=set(RAW_COLUMNS+[TARGET,"user_id","month"]);missing=required-set(df.columns)
    if missing:raise ValueError(f"Missing columns: {sorted(missing)}")
    for column in RAW_COLUMNS+[TARGET]:df[column]=pd.to_numeric(df[column],errors="coerce")
    df["month"]=pd.to_datetime(df["month"],errors="coerce");df=df.dropna(subset=RAW_COLUMNS+[TARGET,"user_id","month"]).sort_values(["month","user_id"]);df[TARGET]=df[TARGET].clip(lower=0)
    months=df["month"].drop_duplicates().sort_values().tolist()
    if len(df)<96 or len(months)<8:raise ValueError("At least 96 complete records across eight months are required")
    train_end=max(1,int(len(months)*.6));validation_end=max(train_end+1,int(len(months)*.8));train_months=set(months[:train_end]);validation_months=set(months[train_end:validation_end]);test_months=set(months[validation_end:])
    train=df["month"].isin(train_months);validation=df["month"].isin(validation_months);test=df["month"].isin(test_months)
    if min(train.sum(),validation.sum(),test.sum())<10:raise ValueError("Train, validation, and chronological test partitions each require 10 records")
    features=engineer_frame(df);target=df[TARGET]
    candidates={"linear":LinearRegression(),"random_forest":RandomForestRegressor(n_estimators=350,min_samples_leaf=2,random_state=42,n_jobs=-1),"gradient_boosting":GradientBoostingRegressor(n_estimators=250,max_depth=3,learning_rate=.04,loss="huber",random_state=42)}
    validation_metrics={}
    for name,estimator in candidates.items():
        pipeline=regression_pipeline(estimator);pipeline.fit(features[train],target[train]);validation_metrics[name]=evaluate(pipeline,features[validation],target[validation])
    selected=min(validation_metrics,key=lambda name:validation_metrics[name]["mae"]);final_model=regression_pipeline(candidates[selected]);final_model.fit(features[train|validation],target[train|validation]);test_metrics=evaluate(final_model,features[test],target[test])
    metadata={"model_version":MODEL_VERSION,"feature_contract_version":CONTRACT_VERSION,"feature_names":ENGINEERED_COLUMNS,"selected_model":selected,"dataset_classification":"synthetic-demo" if synthetic else "real-user-provided","production_eligible":not synthetic}
    joblib.dump({"model":final_model,"features":ENGINEERED_COLUMNS,"name":selected,**metadata},out/"expense_model.joblib")
    anomaly=Pipeline([("impute",SimpleImputer(strategy="median")),("scale",RobustScaler()),("model",IsolationForest(n_estimators=300,contamination="auto",random_state=42))]);anomaly.fit(df.loc[train|validation,CATEGORY_COLUMNS]);joblib.dump({"model":anomaly,"features":CATEGORY_COLUMNS,"training_medians":df.loc[train|validation,CATEGORY_COLUMNS].median().to_dict(),**metadata},out/"anomaly_model.joblib")
    cluster_pipeline=Pipeline([("impute",SimpleImputer(strategy="median")),("scale",StandardScaler()),("model",KMeans(n_clusters=4,n_init=30,random_state=42))]);cluster_data=features.loc[train|validation,CLUSTER_COLUMNS];cluster_pipeline.fit(cluster_data);cluster_ids=cluster_pipeline.predict(cluster_data);transformed=cluster_pipeline[:-1].transform(cluster_data);silhouette=float(silhouette_score(transformed,cluster_ids));scaled_centers=cluster_pipeline.named_steps["model"].cluster_centers_;raw_centers=cluster_pipeline.named_steps["scale"].inverse_transform(scaled_centers);centers=pd.DataFrame(raw_centers,columns=CLUSTER_COLUMNS);label_map=unique_cluster_labels(centers)
    joblib.dump({"model":cluster_pipeline,"features":CLUSTER_COLUMNS,"labels":label_map,"centers":centers.to_dict(orient="index"),**metadata},out/"behavior_model.joblib")
    dataset_hash=hashlib.sha256(source.read_bytes()).hexdigest();metrics={"model_version":MODEL_VERSION,"feature_contract_version":CONTRACT_VERSION,"trained_at":datetime.now(timezone.utc).isoformat(),"runtime":{"python":platform.python_version(),"numpy":np.__version__,"pandas":pd.__version__,"scikit_learn":sklearn.__version__,"joblib":joblib.__version__},"dataset":{"sha256":dataset_hash,"rows":len(df),"users":int(df["user_id"].nunique()),"first_month":str(df["month"].min().date()),"last_month":str(df["month"].max().date()),"synthetic":bool(synthetic),"classification":"synthetic-demo" if synthetic else "real-user-provided","production_eligible":not synthetic},"validation_strategy":"chronological train/validation/test","partitions":{"train_rows":int(train.sum()),"validation_rows":int(validation.sum()),"test_rows":int(test.sum()),"train_last_month":str(max(train_months).date()),"validation_last_month":str(max(validation_months).date()),"test_first_month":str(min(test_months).date())},"model_selection_metric":"validation_mae","selected_expense_model":selected,"validation_metrics":validation_metrics,"selected_model_test_metrics":test_metrics,"cluster_silhouette":silhouette,"cluster_labels":label_map,"feature_names":ENGINEERED_COLUMNS}
    (out/"metrics.json").write_text(json.dumps(metrics,indent=2),encoding="utf-8");print(json.dumps(metrics,indent=2));return metrics

if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("csv");parser.add_argument("--out",default="models");parser.add_argument("--synthetic",action="store_true",help="mark dataset metadata as synthetic/demo only");args=parser.parse_args();main(args.csv,args.out,args.synthetic)
