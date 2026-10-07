"""Generate deterministic SYNTHETIC data for tests/demos only.

This data contains no personal information and must never be presented as real-world
validation or production model performance.
"""
import argparse
import numpy as np,pandas as pd

def generate(path:str,seed:int=42):
    rng=np.random.default_rng(seed);rows=[];profiles=[(.18,.05),(.35,.08),(.03,.45),(.08,.12)]
    for month in pd.date_range('2025-01-01',periods=12,freq='MS'):
        for user in range(12):
            saving,debt_ratio=profiles[user%4];income=float(rng.normal(20000,1800));base={'food':3000,'transport':1500,'shopping':1800,'bills':2200,'housing':5000,'health':700,'entertainment':1000}
            if user%4==0:base['shopping']*=.5;base['entertainment']*=.5
            if user%4==2:base['shopping']*=2;base['entertainment']*=2
            categories={key:max(0,float(rng.normal(value,120))) for key,value in base.items()};expense=sum(categories.values());rows.append({'user_id':f'SYNTHETIC-{user:02d}','month':month.date(),'income':income,**categories,'monthly_debt_payments':income*debt_ratio,'monthly_surplus':income*saving,'total_expenses_next_month':max(0,expense+rng.normal(0,350))})
    frame=pd.DataFrame(rows);frame.to_csv(path,index=False);print(f'Wrote {len(frame)} synthetic demo rows to {path}')
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',default='synthetic_demo_monthly.csv');parser.add_argument('--seed',type=int,default=42);args=parser.parse_args();generate(args.out,args.seed)
