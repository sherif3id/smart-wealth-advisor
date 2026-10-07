"""Single source of truth for monthly ML feature semantics."""
from __future__ import annotations
import numpy as np
import pandas as pd

CONTRACT_VERSION="monthly-financial-v2"
MODEL_VERSION="2.0.0"
CATEGORY_COLUMNS=["food","transport","shopping","bills","housing","health","entertainment"]
RAW_COLUMNS=["income",*CATEGORY_COLUMNS,"monthly_debt_payments","monthly_surplus"]
ENGINEERED_COLUMNS=[*RAW_COLUMNS,"expense_ratio","saving_ratio","debt_service_ratio","discretionary_ratio"]
CLUSTER_COLUMNS=["expense_ratio","saving_ratio","debt_service_ratio","discretionary_ratio"]
TARGET="total_expenses_next_month"

def engineer_frame(df:pd.DataFrame)->pd.DataFrame:
    """Create model features from one row per user-month, using monthly currency amounts."""
    frame=df[RAW_COLUMNS].copy();expense=frame[CATEGORY_COLUMNS].sum(axis=1);income=frame["income"].replace(0,np.nan)
    frame["expense_ratio"]=(expense/income).fillna(0).clip(0,10)
    frame["saving_ratio"]=(frame["monthly_surplus"]/income).fillna(0).clip(-10,10)
    frame["debt_service_ratio"]=(frame["monthly_debt_payments"]/income).fillna(0).clip(0,10)
    frame["discretionary_ratio"]=((frame["shopping"]+frame["entertainment"])/income).fillna(0).clip(0,10)
    return frame[ENGINEERED_COLUMNS]

def payload_to_frame(payload:dict)->pd.DataFrame:
    return engineer_frame(pd.DataFrame([{key:payload[key] for key in RAW_COLUMNS}]))

def unique_cluster_labels(centers:pd.DataFrame)->dict[int,str]:
    """Assign exactly one deterministic semantic label per four-cluster model."""
    if len(centers)!=4:raise ValueError("Behavior interpretation requires exactly four clusters")
    remaining=set(int(i) for i in centers.index);mapping={}
    debt=max(remaining,key=lambda i:(centers.loc[i,"debt_service_ratio"],-i));mapping[debt]="Debt-heavy";remaining.remove(debt)
    saver=max(remaining,key=lambda i:(centers.loc[i,"saving_ratio"]-centers.loc[i,"expense_ratio"],-i));mapping[saver]="Saver";remaining.remove(saver)
    spender=max(remaining,key=lambda i:(centers.loc[i,"expense_ratio"]+centers.loc[i,"discretionary_ratio"],-i));mapping[spender]="High Spender";remaining.remove(spender)
    balanced=remaining.pop();mapping[balanced]="Balanced"
    if set(mapping.values())!={"Saver","Balanced","High Spender","Debt-heavy"}:raise AssertionError("Cluster labels must be unique")
    return mapping
