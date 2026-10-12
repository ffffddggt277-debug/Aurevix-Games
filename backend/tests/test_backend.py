import io,json,zipfile,stat,time,hashlib
import pytest,httpx
from PIL import Image
from sqlalchemy import select
from aurevix.models import SessionLocal,User,Session,Version,Game,Base,engine
from aurevix.security import digest
from aurevix.archive import inspect_zip
from aurevix.moderation import classify
from fastapi import HTTPException
META={'title_ru':'Тестовая игра','title_en':'Test game','description_ru':'Безопасная тестовая игра','description_en':'A safe test browser game','genres':['arcade'],'tags':['test'],'platforms':['desktop'],'controls_ru':'Мышь','controls_en':'Mouse','version':'1.0.0'}
def zipdata(files=None,compression=zipfile.ZIP_DEFLATED):
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w',compression) as z:
        for k,v in (files or {'index.html':'<html><script>console.log("demo")</script></html>'}).items():z.writestr(k,v)
    return b.getvalue()
def pic():
    b=io.BytesIO();Image.new('RGB',(64,64),'purple').save(b,'PNG');return b.getvalue()
def upload(client,auth,data=None,game_id='',version='1.0.0'):
    return client.post('/api/games/upload',headers=auth,data={'metadata':json.dumps(META|{'version':version}),'game_id':game_id},files={'archive':('game.zip',data or zipdata(),'application/zip'),'icon':('icon.png',pic(),'image/png'),'screenshot1':('one.png',pic(),'image/png'),'screenshot2':('two.png',pic(),'image/png')})
def grant(auth):
    with SessionLocal() as s:
        session=s.get(Session,digest(auth['Authorization'][7:]));s.get(User,session.user_id).admin=True;s.commit()
def approve(client,auth,v):
    grant(auth);return client.post('/api/admin/versions/'+v,json={'status':'approved','reason':'Test manual review passed'},headers=auth)
def test_health_openapi(client):
    assert client.get('/health').json()['status']=='ok'
    spec=client.get('/openapi.json').json();assert '/api/games/upload' in spec['paths']
def test_auth_uniqueness_login_logout(client,auth):
    assert client.get('/api/me',headers=auth).status_code==200
    assert client.post('/api/auth/register',json={'nickname':'testpilot','password':'safe-test-password'}).status_code==409
    assert client.post('/api/auth/login',json={'nickname':'TestPilot','password':'wrong-password'}).status_code==401
    login=client.post('/api/auth/login',json={'nickname':'TestPilot','password':'safe-test-password'});assert login.status_code==200
    assert client.post('/api/auth/logout',headers=auth).status_code==200
    assert client.get('/api/me',headers=auth).status_code==401
    with SessionLocal() as s:assert 'safe-test-password' not in s.scalar(select(User)).password_hash
@pytest.mark.parametrize('token',['invalid','expired'])
def test_invalid_expired_tokens(client,auth,token):
    if token=='expired':
        with SessionLocal() as s:s.get(Session,digest(auth['Authorization'][7:])).expires=1;s.commit()
        h=auth
    else:h={'Authorization':'Bearer nonsense'}
    assert client.get('/api/me',headers=h).status_code==401

def test_password_change_revokes_all(client,auth):
    r=client.post('/api/auth/password',headers=auth,json={'old_password':'safe-test-password','new_password':'new-safe-password'});assert r.status_code==200
    assert client.get('/api/me',headers=auth).status_code==401
    assert client.post('/api/auth/login',json={'nickname':'TestPilot','password':'new-safe-password'}).status_code==200

def test_profile_access_validation(client,auth):
    assert client.patch('/api/me',headers=auth,json={'bio':'Testing','admin':True}).status_code==422
    assert client.patch('/api/me',headers=auth,json={'bio':'Testing'}).json()['bio']=='Testing'
    assert client.patch('/api/profiles/someone',headers=auth,json={'bio':'hack'}).status_code==405
    assert client.post('/api/auth/register',json={'nickname':'AdminGuy','password':'safe-test-password','admin':True}).status_code==422

def test_cors(client):
    r=client.options('/api/games',headers={'Origin':'http://localhost:3000','Access-Control-Request-Method':'GET'});assert r.status_code==200;assert r.headers['access-control-allow-origin']=='http://localhost:3000'
    r=client.get('/api/games',headers={'Origin':'https://evil.example'});assert r.status_code==403;assert 'access-control-allow-origin' not in r.headers

def test_rate_limits(client):
    for i in range(8):assert client.post('/api/auth/login',json={'nickname':'Unknown','password':'wrong-password'}).status_code==401
    assert client.post('/api/auth/login',json={'nickname':'Unknown','password':'wrong-password'}).status_code==429

def test_upload_moderation_publish_versions_favorites_ratings(client,auth):
    r=upload(client,auth);assert r.status_code==201;r=r.json();v=r['version_id'];g=r['game_id']
    status=client.get('/api/versions/'+v+'/moderation',headers=auth).json();assert status['status']=='manual_review'
    assert client.get('/api/games/'+g).status_code==404
    assert approve(client,auth,v).status_code==200
    d=client.get('/api/games/'+g).json();assert d['version']=='1.0.0'
    assert client.put('/api/games/'+g+'/favorite',headers=auth).status_code==200
    assert client.put('/api/games/'+g+'/favorite',headers=auth).status_code==200
    assert len(client.get('/api/me/favorites',headers=auth).json())==1
    assert client.put('/api/games/'+g+'/rating',headers=auth,json={'value':5}).status_code==200
    assert client.get('/api/games?q=Test&genre=arcade').json()['total']==1
    assert client.get('/api/games?tag=test').json()['total']==1
    assert client.get('/api/games?sort=rating').json()['items'][0]['rating']==5
    assert client.get('/api/games?q=nonexistent').json()['total']==0
    newer=upload(client,auth,game_id=g,version='2.0.0').json()
    assert client.get('/api/games/'+g).json()['version']=='1.0.0'
    assert approve(client,auth,newer['version_id']).status_code==200
    assert client.get('/api/games/'+g).json()['version']=='2.0.0'
    assert client.delete('/api/games/'+g+'/favorite',headers=auth).status_code==200
    assert client.get('/api/me/favorites',headers=auth).json()==[]
    content=client.get('/api'+d['play_url']);assert content.status_code==200;assert 'sandbox allow-scripts' in content.headers['content-security-policy'];assert 'allow-same-origin' not in content.headers['content-security-policy']
    assert client.get('/api/content/'+g+'/'+v+'/../private').status_code in (404,422)

def test_owner_admin_isolation(client,auth):
    r=upload(client,auth).json()
    other=client.post('/api/auth/register',json={'nickname':'OtherPilot','password':'other-safe-password'}).json();h={'Authorization':'Bearer '+other['token']}
    assert client.get('/api/versions/'+r['version_id']+'/moderation',headers=h).status_code==403
    assert upload(client,h,game_id=r['game_id'],version='2').status_code==403
    assert client.get('/api/admin/moderation',headers=h).status_code==403
    assert client.post('/api/admin/versions/'+r['version_id'],headers=h,json={'status':'approved','reason':'hack attempt'}).status_code==403

def test_score_forgery_replay(client,auth):
    r=upload(client,auth).json();approve(client,auth,r['version_id']);g=r['game_id']
    play=client.post('/api/sdk/sessions',headers=auth,json={'game_id':g}).json()
    assert client.post('/api/sdk/scores',headers=auth,json={'play_token':play['play_token'],'value':10,'user_id':'fake'}).status_code==422
    assert client.post('/api/sdk/scores',headers=auth,json={'play_token':play['play_token'],'value':-10}).status_code==422
    assert client.post('/api/sdk/scores',headers=auth,json={'play_token':play['play_token'],'value':1.5}).status_code==422
    other=client.post('/api/auth/register',json={'nickname':'OtherScore','password':'another-safe-password'}).json()
    assert client.post('/api/sdk/scores',headers={'Authorization':'Bearer '+other['token']},json={'play_token':play['play_token'],'value':99}).status_code==403
    result=client.post('/api/sdk/scores',headers=auth,json={'play_token':play['play_token'],'value':100});assert result.status_code==200;assert result.json()['verified'] is False
    assert client.post('/api/sdk/scores',headers=auth,json={'play_token':play['play_token'],'value':200}).status_code==403
    board=client.get('/api/leaderboards?game_id='+g).json();assert not board['competitive'];assert board['items'][0]['nickname']=='TestPilot'

def test_block_and_audit(client,auth):
    r=upload(client,auth).json();approve(client,auth,r['version_id'])
    assert client.post('/api/admin/games/'+r['game_id']+'/block',headers=auth,json={'blocked':True,'reason':'Safety review required'}).status_code==200
    assert client.get('/api/games/'+r['game_id']).status_code==404
    assert len(client.get('/api/admin/audit',headers=auth).json())==2

@pytest.mark.parametrize('path',['../evil.js','/tmp/evil.js','C:/evil.js','folder/../../evil.js','a\\evil.js'])
def test_zip_slip(path):
    with pytest.raises(HTTPException) as e:inspect_zip(zipdata({'index.html':'safe',path:'bad'}))
    assert e.value.detail=='zip_path'
@pytest.mark.parametrize('kind',['corrupt','missing','bomb','files','size','type','duplicate','symlink'])
def test_zip_invalid(kind):
    if kind=='corrupt':data=b'invalid zip'
    elif kind=='missing':data=zipdata({'main.js':'no html'})
    elif kind=='bomb':data=zipdata({'index.html':'x','large.js':'0'*2000000})
    elif kind=='files':data=zipdata({f'{i}.js':'x' for i in range(601)})
    elif kind=='size':data=b'x'*(20*1024*1024+1)
    elif kind=='type':data=zipdata({'index.html':'safe','run.py':'print(1)'})
    elif kind=='duplicate':
        b=io.BytesIO()
        with zipfile.ZipFile(b,'w') as z:z.writestr('index.html','a');z.writestr('INDEX.HTML','b')
        data=b.getvalue()
    else:
        b=io.BytesIO()
        with zipfile.ZipFile(b,'w') as z:
            info=zipfile.ZipInfo('index.html');info.external_attr=(stat.S_IFLNK|0o777)<<16;z.writestr(info,'/etc/passwd')
        data=b.getvalue()
    with pytest.raises(HTTPException):inspect_zip(data)

def test_persistence_snapshot_restore(tmp_path,monkeypatch):
    import sqlite3
    from aurevix.persistence import checkpoint,restore
    local=tmp_path/'local';local.mkdir();remote=tmp_path/'volume';monkeypatch.setenv('PERSISTENT_DIR',str(remote))
    with sqlite3.connect(local/'aurevix.db') as db:db.execute('CREATE TABLE test (value TEXT)');db.execute("INSERT INTO test VALUES ('persistent')")
    checkpoint(local);other=tmp_path/'restored';other.mkdir();restore(other)
    with sqlite3.connect(other/'aurevix.db') as db:assert db.execute('SELECT value FROM test').fetchone()[0]=='persistent'

@pytest.mark.parametrize('scenario',['success','401','403','429','timeout','badjson','shape','invaliddecision','missing'])
def test_openrouter_fail_closed(scenario,monkeypatch):
    import asyncio
    captured=[]
    if scenario!='missing':monkeypatch.setenv('OPENROUTER_API_KEY','test-key-not-real')
    def handler(req):
        captured.append(req)
        if scenario=='timeout':raise httpx.ReadTimeout('timeout')
        if scenario in ['401','403','429']:return httpx.Response(int(scenario),json={'error':'upstream'})
        if scenario=='badjson':return httpx.Response(200,content=b'not json')
        if scenario=='shape':return httpx.Response(200,json={'unexpected':True})
        content=json.dumps({'status':'approved','reason':'Mock checked'}) if scenario=='success' else '{"status":"approve"}'
        return httpx.Response(200,json={'choices':[{'message':{'content':content}}]})
    async def call():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:return await classify({'title':'test'},'source',c)
    result=asyncio.run(call());assert result.status==('approved' if scenario=='success' else 'manual_review')
    if captured:
        body=json.loads(captured[0].content);assert str(captured[0].url)=='https://openrouter.ai/api/v1/chat/completions';assert body['model']=='inclusionai/ling-3.1-flash'
        assert 'test-key-not-real' not in result.reason

def test_missing_key_upload_never_approves(client,auth):
    r=upload(client,auth).json();assert client.get('/api/versions/'+r['version_id']+'/moderation',headers=auth).json()['status']=='manual_review'

def test_validation_errors_hide_values(client):
    r=client.post('/api/auth/register',json={'nickname':'!','password':'DO_NOT_LEAK'});assert r.status_code==422;assert 'DO_NOT_LEAK' not in r.text
    assert client.get('/api/games?page=0').status_code==422

def test_body_limit_chunked(client):
    size=34*1024*1024+1
    r=client.post('/api/auth/login',content=iter([b'x'*size]),headers={'Content-Type':'application/json'})
    assert r.status_code==413
    assert r.json()['error']['code']=='file_size'

def test_game_files_opaque_origin_allowed_auth_denied(client,auth):
    r=upload(client,auth).json();approve(client,auth,r['version_id'])
    play=client.get('/api/games/'+r['game_id']).json()['play_url']
    assert client.get('/api'+play,headers={'Origin':'null'}).status_code==200
    assert client.get('/api/me',headers=auth|{'Origin':'null'}).status_code==403

def test_version_metadata_is_atomic(client,auth):
    first=upload(client,auth).json();approve(client,auth,first['version_id'])
    g=first['game_id'];metadata=META|{'version':'2.0.0','title_en':'New title','title_ru':'Новое название'}
    second=client.post('/api/games/upload',headers=auth,data={'metadata':json.dumps(metadata),'game_id':g},files={'archive':('game.zip',zipdata(),'application/zip'),'icon':('icon.png',pic(),'image/png'),'screenshot1':('one.png',pic(),'image/png'),'screenshot2':('two.png',pic(),'image/png')}).json()
    assert client.get('/api/games/'+g).json()['title_en']=='Test game'
    approve(client,auth,second['version_id'])
    assert client.get('/api/games/'+g).json()['title_en']=='New title'

def test_admin_inspection_archive(client,auth):
    result=upload(client,auth).json();v=result['version_id']
    assert client.get('/api/admin/versions/'+v+'/inspection',headers=auth).status_code==403
    grant(auth)
    inspection=client.get('/api/admin/versions/'+v+'/inspection',headers=auth).json()
    assert inspection['files'][0]['path']=='index.html'
    assert inspection['metadata']['title_en']=='Test game'
    response=client.get('/api/admin/versions/'+v+'/archive',headers=auth)
    assert response.status_code==200
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:assert 'index.html' in z.namelist()
