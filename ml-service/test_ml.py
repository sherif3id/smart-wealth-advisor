import json
import numpy as np,pandas as pd
from fastapi.testclient import TestClient
import main as api
from feature_definitions import CONTRACT_VERSION,ENGINEERED_COLUMNS,engineer_frame,payload_to_frame
from train_models import main as train

def dataset(path):
    rng=np.random.default_rng(42);rows=[]
    profiles=[(.18,.05),(.35,.08),(.03,.45),(.08,.12)]
    for month in pd.date_range('2025-01-01',periods=12,freq='MS'):
        for user in range(12):
            saving,debt_ratio=profiles[user%4];income=float(rng.normal(20000,1800));base={'food':3000,'transport':1500,'shopping':1800,'bills':2200,'housing':5000,'health':700,'entertainment':1000}
            if user%4==0:base['shopping']*=.5;base['entertainment']*=.5
            if user%4==2:base['shopping']*=2;base['entertainment']*=2
            categories={key:max(0,float(rng.normal(value,120))) for key,value in base.items()};expense=sum(categories.values());rows.append({'user_id':user,'month':month.date(),'income':income,**categories,'monthly_debt_payments':income*debt_ratio,'monthly_surplus':income* saving,'total_expenses_next_month':max(0,expense+rng.normal(0,350))})
    pd.DataFrame(rows).to_csv(path,index=False)

def payload():return {'income':20000,'food':3000,'transport':1500,'shopping':1800,'bills':2200,'housing':5000,'health':700,'entertainment':1000,'monthly_debt_payments':1000,'monthly_surplus':4800}

def test_feature_contract_is_identical_for_training_and_inference():
    value=payload();training=engineer_frame(pd.DataFrame([value]));inference=payload_to_frame(value);pd.testing.assert_frame_equal(training,inference);assert list(inference.columns)==ENGINEERED_COLUMNS;assert inference.iloc[0]['debt_service_ratio']==.05;assert inference.iloc[0]['saving_ratio']==.24

def test_training_loading_prediction_anomaly_and_unique_deterministic_clustering(tmp_path,monkeypatch):
    csv=tmp_path/'synthetic-demo.csv';models1=tmp_path/'models1';models2=tmp_path/'models2';dataset(csv);metrics1=train(str(csv),str(models1),synthetic=True);metrics2=train(str(csv),str(models2),synthetic=True);assert metrics1['cluster_labels']==metrics2['cluster_labels'];assert len(metrics1['cluster_labels'])==4;assert len(set(metrics1['cluster_labels'].values()))==4;assert metrics1['dataset']['synthetic'] is True;assert metrics1['feature_contract_version']==CONTRACT_VERSION;assert metrics1['validation_strategy']=='chronological train/validation/test';assert {'mae','rmse','r2'}<=set(metrics1['selected_model_test_metrics'])
    monkeypatch.setattr(api,'MODELS',models1);monkeypatch.setattr(api,'ALLOW_SYNTHETIC_DEMO',True);client=TestClient(api.app);ready=client.get('/health/ready');assert ready.status_code==200;assert ready.json()['ready'] is True;assert ready.json()['models']['expense']['dataset_classification']=='synthetic-demo';assert ready.json()['models']['expense']['production_eligible'] is False
    prediction=client.post('/predict-expenses',json=payload());assert prediction.status_code==200;assert prediction.json()['predicted_expense']>=0;assert prediction.json()['classification']=='educational projection'
    anomaly=client.post('/check-expense',json=payload());assert anomaly.status_code==200;assert anomaly.json()['detection_scope']=='unusual monthly category-level spending pattern';assert 'fraud' in anomaly.json()['note'].lower()
    behavior=client.post('/financial-profile',json=payload());assert behavior.status_code==200;assert behavior.json()['profile'] in ['Saver','Balanced','High Spender','Debt-heavy'];assert 'confidence' not in behavior.json();assert behavior.json()['dataset_classification']=='synthetic-demo'
    monkeypatch.setattr(api,'APP_ENV','production');blocked=client.get('/health/ready').json();assert blocked['ready'] is False;assert blocked['models']['expense']['reason']=='SYNTHETIC_MODEL_NOT_ALLOWED'

def test_invalid_input_and_unavailable_or_unloadable_models(tmp_path,monkeypatch):
    monkeypatch.setattr(api,'MODELS',tmp_path);client=TestClient(api.app);assert client.post('/predict-expenses',json={'income':-1}).status_code==422;assert client.post('/predict-expenses',json=payload()).status_code==503;health=client.get('/health/ready').json();assert health['service'] is True and health['ready'] is False
    (tmp_path/'expense_model.joblib').write_text('not joblib');response=client.post('/predict-expenses',json=payload());assert response.status_code==503;assert response.json()['detail']['code']=='MODEL_UNLOADABLE'
