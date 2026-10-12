import os,tempfile
os.environ['DATA_DIR']=tempfile.mkdtemp(prefix='aurevix-test-')
os.environ['ENABLE_GRADIO']='0'
os.environ['LOAD_LOCAL_ENV']='0'
os.environ['FRONTEND_URL']='http://localhost:3000'
os.environ.pop('OPENROUTER_API_KEY',None)
os.environ.pop('PERSISTENT_DIR',None)
import pytest
from fastapi.testclient import TestClient
from aurevix.models import Base,engine
from aurevix.security import limiter
from app import api
@pytest.fixture(autouse=True)
def reset():
    Base.metadata.drop_all(engine);Base.metadata.create_all(engine);limiter.items.clear()
@pytest.fixture
def client():
    with TestClient(api) as c:yield c
@pytest.fixture
def auth(client):
    r=client.post('/api/auth/register',json={'nickname':'TestPilot','password':'safe-test-password'});assert r.status_code==201
    return {'Authorization':'Bearer '+r.json()['token']}
