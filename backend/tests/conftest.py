import os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]))
os.environ['JWT_SECRET']='test-secret-at-least-32-characters-long'
os.environ['DATABASE_URL']='sqlite://'
os.environ['AUTO_CREATE_TABLES']='false'
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base,get_db
from app.main import app,requests as rate_limit_requests
engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
TestingSession=sessionmaker(bind=engine,expire_on_commit=False)
def override_db():
 db=TestingSession()
 try:yield db
 finally:db.close()
app.dependency_overrides[get_db]=override_db
@pytest.fixture(autouse=True)
def tables():
 rate_limit_requests.clear();Base.metadata.create_all(engine);yield;Base.metadata.drop_all(engine);rate_limit_requests.clear()
@pytest.fixture
def client():return TestClient(app)
def register(client,email='a@example.com',name='Alice'):
 r=client.post('/auth/register',json={'email':email,'password':'VeryStrong123!','name':name,'locale':'en'});assert r.status_code==201,r.text;return r.json()['access_token']
@pytest.fixture
def token(client):return register(client)
@pytest.fixture
def headers(token):return {'Authorization':f'Bearer {token}'}
