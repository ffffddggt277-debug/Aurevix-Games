import json, re, secrets, time, hashlib, mimetypes, io, os
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException,Request,UploadFile,File as Upload,Form,BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel,Field,ConfigDict
from sqlalchemy.orm import Session as DB
from sqlalchemy import select,func,delete,or_
from sqlalchemy.exc import IntegrityError
from .models import *
from .security import current,admin,issue,public_user,ph,verify,digest,limiter,DUMMY_HASH
from .archive import inspect_zip
from .storage import put,get,bounded,image
from .config import MAX_ZIP,MAX_IMAGE,ORIGINS
from .moderation import moderate
router=APIRouter()
class Strict(BaseModel): model_config=ConfigDict(extra='forbid')
class Credentials(Strict):
    nickname:str=Field(min_length=3,max_length=24,pattern=r'^[A-Za-z0-9_]+$')
    password:str=Field(min_length=10,max_length=128)
class Password(Strict):
    old_password:str=Field(max_length=128)
    new_password:str=Field(min_length=10,max_length=128)
class Profile(Strict): bio:str=Field(max_length=600)
class Meta(Strict):
    title_ru:str=Field(min_length=2,max_length=100)
    title_en:str=Field(min_length=2,max_length=100)
    description_ru:str=Field(min_length=10,max_length=4000)
    description_en:str=Field(min_length=10,max_length=4000)
    genres:list[Literal['arcade','puzzle','action','racing','strategy','adventure']]=Field(min_length=1,max_length=3)
    tags:list[str]=Field(default_factory=list,max_length=8)
    platforms:list[Literal['desktop','mobile']]=Field(min_length=1,max_length=2)
    controls_ru:str=Field(min_length=1,max_length=600)
    controls_en:str=Field(min_length=1,max_length=600)
    multiplayer:bool=False
    version:str=Field(min_length=1,max_length=40,pattern=r'^[a-zA-Z0-9._-]+$')
@router.post('/auth/register',status_code=201)
def register(data:Credentials,request:Request,s:DB=Depends(db)):
    limiter.hit(('register',request.client.host),5,3600)
    if s.scalar(select(User).where(User.nickname_key==data.nickname.lower())): raise HTTPException(409,'nickname_taken')
    u=User(nickname=data.nickname,nickname_key=data.nickname.lower(),password_hash=ph.hash(data.password));s.add(u)
    try:s.commit()
    except IntegrityError:s.rollback();raise HTTPException(409,'nickname_taken')
    return issue(s,u)
@router.post('/auth/login')
def login(data:Credentials,request:Request,s:DB=Depends(db)):
    limiter.hit(('login-ip',request.client.host),15,300);limiter.hit(('login-account',data.nickname.lower()),8,300)
    u=s.scalar(select(User).where(User.nickname_key==data.nickname.lower()))
    valid=verify(u.password_hash if u else DUMMY_HASH,data.password)
    if not u or not valid:raise HTTPException(401,'invalid_credentials')
    return issue(s,u)
@router.post('/auth/logout')
def logout(request:Request,u:User=Depends(current),s:DB=Depends(db)):
    s.execute(delete(Session).where(Session.digest==digest(request.headers['authorization'][7:])));s.commit();return {'ok':True}
@router.post('/auth/password')
def password(data:Password,u:User=Depends(current),s:DB=Depends(db)):
    limiter.hit(('password',u.id),5,300)
    row=s.get(User,u.id)
    if not verify(row.password_hash,data.old_password):raise HTTPException(401,'invalid_credentials')
    row.password_hash=ph.hash(data.new_password);s.execute(delete(Session).where(Session.user_id==u.id));s.commit();return {'ok':True}
@router.get('/me')
def me(u:User=Depends(current)):return public_user(u)
@router.patch('/me')
def edit_me(data:Profile,u:User=Depends(current),s:DB=Depends(db)):
    row=s.get(User,u.id);row.bio=data.bio;s.commit();return public_user(row)
@router.post('/me/avatar')
async def avatar(file:UploadFile=Upload(...),u:User=Depends(current),s:DB=Depends(db)):
    limiter.hit(('avatar',u.id),5,3600)
    key=f'avatars/{u.id}-{secrets.token_hex(8)}.webp';put(key,image(await bounded(file,MAX_IMAGE)))
    row=s.get(User,u.id);row.avatar=key;s.commit();return public_user(row)
@router.get('/profiles/{user_id}')
def profile(user_id:str,s:DB=Depends(db)):
    u=s.get(User,user_id)
    if not u:raise HTTPException(404,'not_found')
    result=public_user(u);result.pop('admin');return result

def game_json(g,s):
    owner=s.get(User,g.owner_id);v=s.get(Version,g.current_version) if g.current_version else None
    avg=s.scalar(select(func.avg(Rating.value)).where(Rating.game_id==g.id))
    return {k:getattr(g,k) for k in ['id','owner_id','title_ru','title_en','description_ru','description_en','controls_ru','controls_en','multiplayer','demo','plays','created_at','updated_at','icon']} | {
      'genres':json.loads(g.genres),'tags':json.loads(g.tags),'platforms':json.loads(g.platforms),'screenshots':json.loads(g.screenshots),
      'author':owner.nickname,'rating':round(avg,1) if avg else None,'version':v.label if v else None,
      'play_url':f'/content/{g.id}/{v.id}/{v.entry}' if v else None}
def visible(s,id):
    g=s.get(Game,id)
    if not g or g.blocked or not g.current_version:raise HTTPException(404,'not_found')
    return g
@router.get('/games')
def games(q:str='',genre:str='',platform:str='',tag:str='',multiplayer:bool|None=None,sort:Literal['new','popular','rating','updated']='new',page:int=1,limit:int=12,s:DB=Depends(db)):
    if page<1 or page>10000 or limit<1 or limit>24 or len(q)>100 or len(tag)>30:raise HTTPException(422,'validation_error')
    stmt=select(Game).where(Game.current_version.is_not(None),Game.blocked==False)
    if q:
        escaped=q.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
        stmt=stmt.where(or_(*[c.ilike(f'%{escaped}%',escape='\\') for c in [Game.title_ru,Game.title_en,Game.description_ru,Game.description_en]]))
    if genre:stmt=stmt.where(Game.genres.contains(json.dumps(genre)))
    if platform:stmt=stmt.where(Game.platforms.contains(json.dumps(platform)))
    if tag:stmt=stmt.where(Game.tags.contains(json.dumps(tag)))
    if multiplayer is not None:stmt=stmt.where(Game.multiplayer==multiplayer)
    total=s.scalar(select(func.count()).select_from(stmt.subquery()))
    order={'new':Game.created_at.desc(),'updated':Game.updated_at.desc(),'popular':Game.plays.desc(),'rating':select(func.avg(Rating.value)).where(Rating.game_id==Game.id).correlate(Game).scalar_subquery().desc()}[sort]
    rows=s.scalars(stmt.order_by(order,Game.id).offset((page-1)*limit).limit(limit)).all()
    return {'items':[game_json(g,s) for g in rows],'total':total,'page':page,'pages':max(1,(total+limit-1)//limit)}
@router.get('/games/{game_id}')
def game(game_id:str,s:DB=Depends(db)):
    g=visible(s,game_id);return game_json(g,s)|{'versions':[{'id':v.id,'label':v.label,'created_at':v.created_at,'play_url':f'/content/{g.id}/{v.id}/{v.entry}'} for v in s.scalars(select(Version).where(Version.game_id==g.id,Version.status=='approved').order_by(Version.created_at.desc())).all()]}
@router.get('/me/games')
def my_games(u:User=Depends(current),s:DB=Depends(db)):
    rows=s.scalars(select(Game).where(Game.owner_id==u.id).order_by(Game.updated_at.desc()).limit(100)).all()
    return [game_json(g,s)|{'blocked':g.blocked,'versions':[{'id':v.id,'label':v.label,'status':v.status,'reason':v.reason,'created_at':v.created_at} for v in s.scalars(select(Version).where(Version.game_id==g.id).order_by(Version.created_at.desc())).all()]} for g in rows]
@router.get('/me/favorites')
def favorites(u:User=Depends(current),s:DB=Depends(db)):
    rows=s.scalars(select(Game).join(Favorite,Favorite.game_id==Game.id).where(Favorite.user_id==u.id,Game.blocked==False,Game.current_version.is_not(None)).limit(100)).all();return [game_json(g,s) for g in rows]
@router.put('/games/{game_id}/favorite')
def favorite(game_id:str,u:User=Depends(current),s:DB=Depends(db)):
    visible(s,game_id)
    if not s.get(Favorite,(u.id,game_id)):s.add(Favorite(user_id=u.id,game_id=game_id));s.commit()
    return {'ok':True}
@router.delete('/games/{game_id}/favorite')
def unfavorite(game_id:str,u:User=Depends(current),s:DB=Depends(db)):
    s.execute(delete(Favorite).where(Favorite.user_id==u.id,Favorite.game_id==game_id));s.commit();return {'ok':True}
class Rate(Strict):value:int=Field(ge=1,le=5)
@router.put('/games/{game_id}/rating')
def rating(game_id:str,data:Rate,u:User=Depends(current),s:DB=Depends(db)):
    visible(s,game_id);limiter.hit(('rate',u.id),15)
    row=s.get(Rating,(u.id,game_id))
    if row:row.value=data.value
    else:s.add(Rating(user_id=u.id,game_id=game_id,value=data.value))
    s.commit();return {'ok':True}
@router.post('/games/upload',status_code=201)
async def upload(background:BackgroundTasks,metadata:str=Form(...),archive:UploadFile=Upload(...),icon:UploadFile=Upload(...),screenshot1:UploadFile=Upload(...),screenshot2:UploadFile=Upload(...),game_id:str=Form(''),u:User=Depends(current),s:DB=Depends(db)):
    limiter.hit(('upload',u.id),4,3600)
    try:
        if len(metadata)>14000:raise ValueError()
        meta=Meta.model_validate_json(metadata)
        if any(len(t)>30 or not re.fullmatch(r'[\w-]+',t) for t in meta.tags):raise ValueError()
    except ValueError:raise HTTPException(422,'validation_error')
    if game_id:
        g=s.get(Game,game_id)
        if not g or g.owner_id!=u.id:raise HTTPException(403,'forbidden')
        if g.blocked:raise HTTPException(403,'forbidden')
        if s.scalar(select(Version).where(Version.game_id==g.id,Version.label==meta.version)):raise HTTPException(409,'version_exists')
    else:
        if s.scalar(select(func.count()).select_from(Game).where(Game.owner_id==u.id))>=100:raise HTTPException(409,'quota')
        fields=meta.model_dump(exclude={'version'})
        for field in ['genres','tags','platforms']:fields[field]=json.dumps(fields[field],ensure_ascii=False)
        g=Game(id=uid(),owner_id=u.id,**fields)
    files=inspect_zip(await bounded(archive,MAX_ZIP))
    pictures=[image(await bounded(f,MAX_IMAGE)) for f in [icon,screenshot1,screenshot2]]
    v=Version(id=uid(),game_id=g.id,label=meta.version)
    keys=[]
    for i,data in enumerate(pictures):
        key=f'media/{g.id}/{v.id}-{i}.webp';put(key,data);keys.append(key)
    proposal=meta.model_dump(exclude={'version'})|{'icon':keys[0],'screenshots':keys[1:]}
    v.metadata_json=json.dumps(proposal,ensure_ascii=False)
    if not game_id:
        g.icon=keys[0];g.screenshots=json.dumps(keys[1:]);s.add(g);s.flush()
    s.add(v);s.flush()
    for path,data in files.items():
        put(f'{g.id}/{v.id}/{path}',data);s.add(File(version_id=v.id,path=path,size=len(data),sha256=hashlib.sha256(data).hexdigest()))
    s.commit();background.add_task(moderate,v.id)
    return {'game_id':g.id,'version_id':v.id,'status':'pending'}
@router.get('/versions/{version_id}/moderation')
def status(version_id:str,u:User=Depends(current),s:DB=Depends(db)):
    v=s.get(Version,version_id);g=s.get(Game,v.game_id) if v else None
    if not g:raise HTTPException(404,'not_found')
    if g.owner_id!=u.id and not u.admin:raise HTTPException(403,'forbidden')
    return {'id':v.id,'status':v.status,'reason':v.reason,'log':[{'decision':m.decision,'reason':m.reason,'created_at':m.created_at} for m in s.scalars(select(Moderation).where(Moderation.version_id==v.id)).all()]}
@router.post('/versions/{version_id}/resubmit')
def resubmit(version_id:str,background:BackgroundTasks,u:User=Depends(current),s:DB=Depends(db)):
    v=s.get(Version,version_id);g=s.get(Game,v.game_id) if v else None
    if not g or g.owner_id!=u.id:raise HTTPException(403,'forbidden')
    if v.status not in ['manual_review','rejected']:raise HTTPException(409,'invalid_status')
    limiter.hit(('resubmit',u.id),3,3600);v.status='pending';v.reason='';s.commit();background.add_task(moderate,v.id);return {'status':'pending'}
@router.get('/admin/moderation')
def queue(u:User=Depends(admin),s:DB=Depends(db)):
    return [{'id':v.id,'game_id':v.game_id,'label':v.label,'status':v.status,'reason':v.reason,'title':s.get(Game,v.game_id).title_ru} for v in s.scalars(select(Version).order_by(Version.created_at.desc()).limit(100)).all()]
class Review(Strict):
    status:Literal['approved','rejected','manual_review']
    reason:str=Field(min_length=5,max_length=1000)
@router.post('/admin/versions/{version_id}')
def review(version_id:str,data:Review,u:User=Depends(admin),s:DB=Depends(db)):
    v=s.get(Version,version_id)
    if not v:raise HTTPException(404,'not_found')
    g=s.get(Game,v.game_id);v.status=data.status;v.reason=data.reason
    if data.status=='approved' and not g.blocked:apply_version(g,v)
    elif g.current_version==v.id:g.current_version=None
    s.add(Moderation(version_id=v.id,decision=data.status,reason=data.reason));s.add(Audit(actor=u.id,action='review',target=v.id,reason=data.reason));s.commit();return {'ok':True}
class Block(Strict):
    blocked:bool
    reason:str=Field(min_length=5,max_length=1000)
@router.post('/admin/games/{game_id}/block')
def block(game_id:str,data:Block,u:User=Depends(admin),s:DB=Depends(db)):
    g=s.get(Game,game_id)
    if not g:raise HTTPException(404,'not_found')
    g.blocked=data.blocked;s.add(Audit(actor=u.id,action='block' if data.blocked else 'unblock',target=g.id,reason=data.reason));s.commit();return {'ok':True}
@router.get('/admin/audit')
def audit(u:User=Depends(admin),s:DB=Depends(db)):
    return [{'actor':a.actor,'action':a.action,'target':a.target,'reason':a.reason,'created_at':a.created_at} for a in s.scalars(select(Audit).order_by(Audit.created_at.desc()).limit(100)).all()]
class Play(Strict):game_id:str
@router.post('/sdk/sessions')
def play(data:Play,u:User=Depends(current),s:DB=Depends(db)):
    g=visible(s,data.game_id);limiter.hit(('play',u.id),20)
    token=secrets.token_urlsafe(32);s.add(PlaySession(id=digest(token),user_id=u.id,game_id=g.id,expires=int(time.time())+600));g.plays+=1;s.commit()
    return {'play_token':token,'game_id':g.id,'expires_in':600,'competitive':False}
class Submit(Strict):
    play_token:str=Field(max_length=100)
    value:int=Field(ge=0,le=1000000,strict=True)
@router.post('/sdk/scores')
def score(data:Submit,u:User=Depends(current),s:DB=Depends(db)):
    limiter.hit(('score',u.id),10)
    ps=s.get(PlaySession,digest(data.play_token))
    if not ps or ps.user_id!=u.id or ps.used or ps.expires<time.time():raise HTTPException(403,'invalid_play_session')
    visible(s,ps.game_id)
    # Atomic consume prevents replay even in concurrent requests.
    from sqlalchemy import update
    consumed=s.execute(update(PlaySession).where(PlaySession.id==ps.id,PlaySession.used==False).values(used=True)).rowcount
    if not consumed:raise HTTPException(409,'invalid_play_session')
    s.add(Score(user_id=u.id,game_id=ps.game_id,value=data.value,verified=False));s.commit();return {'accepted':True,'verified':False,'competitive':False}
@router.get('/leaderboards')
def leaders(game_id:str='',s:DB=Depends(db)):
    stmt=select(User.nickname,func.max(Score.value).label('value')).join(Score,Score.user_id==User.id).join(Game,Score.game_id==Game.id).where(Game.blocked==False,Game.current_version.is_not(None),Score.verified==False)
    if game_id:visible(s,game_id);stmt=stmt.where(Score.game_id==game_id)
    return {'verified':False,'competitive':False,'items':[{'nickname':n,'value':v} for n,v in s.execute(stmt.group_by(User.id).order_by(func.max(Score.value).desc()).limit(50))]}
@router.get('/media/{path:path}')
def media(path:str,s:DB=Depends(db)):
    if path.startswith('avatars/'):
        if not s.scalar(select(User).where(User.avatar==path)):raise HTTPException(404,'not_found')
    else:
        parts=path.split('/')
        if len(parts)!=3 or parts[0]!='media':raise HTTPException(404,'not_found')
        visible(s,parts[1])
    return FileResponse(get(path),media_type='image/webp',headers={'Cache-Control':'public, max-age=3600','X-Content-Type-Options':'nosniff'})
@router.get('/content/{game_id}/{version_id}/{path:path}')
def content(game_id:str,version_id:str,path:str,s:DB=Depends(db)):
    g=visible(s,game_id);v=s.get(Version,version_id)
    if not v or v.game_id!=g.id or v.status!='approved':raise HTTPException(404,'not_found')
    f=s.scalar(select(File).where(File.version_id==v.id,File.path==path))
    if not f:raise HTTPException(404,'not_found')
    csp="default-src 'none'; script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; media-src 'self' blob:; font-src 'self'; connect-src 'self'; worker-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors "+' '.join(ORIGINS)+"; sandbox allow-scripts allow-pointer-lock"
    return FileResponse(get(f'{g.id}/{v.id}/{path}'),media_type=mimetypes.guess_type(path)[0] or 'application/octet-stream',headers={'Content-Security-Policy':csp,'X-Content-Type-Options':'nosniff','Access-Control-Allow-Origin':'*','Cross-Origin-Resource-Policy':'cross-origin','Cache-Control':'public,max-age=3600'})

@router.get('/profiles/{user_id}/games')
def creator_games(user_id:str,s:DB=Depends(db)):
    if not s.get(User,user_id):raise HTTPException(404,'not_found')
    return [game_json(g,s) for g in s.scalars(select(Game).where(Game.owner_id==user_id,Game.blocked==False,Game.current_version.is_not(None)).limit(100)).all()]

@router.get('/admin/versions/{version_id}/inspection')
def inspection(version_id:str,u:User=Depends(admin),s:DB=Depends(db)):
    v=s.get(Version,version_id)
    if not v:raise HTTPException(404,'not_found')
    files=s.scalars(select(File).where(File.version_id==v.id)).all();samples=[];remaining=20000
    for f in files:
        if f.path.endswith(('.html','.js','.css','.json','.mjs','.txt')) and remaining>0:
            text=get(f'{v.game_id}/{v.id}/{f.path}').read_bytes()[:min(4000,remaining)].decode('utf-8',errors='replace');remaining-=len(text);samples.append({'path':f.path,'text':text})
    return {'version_id':v.id,'metadata':json.loads(v.metadata_json or '{}'),'files':[{'path':f.path,'size':f.size,'sha256':f.sha256} for f in files],'samples':samples,'log':[{'decision':m.decision,'reason':m.reason,'created_at':m.created_at} for m in s.scalars(select(Moderation).where(Moderation.version_id==v.id)).all()]}

@router.get('/admin/versions/{version_id}/archive')
def review_archive(version_id:str,u:User=Depends(admin),s:DB=Depends(db)):
    import tempfile,zipfile
    from pathlib import Path
    from starlette.background import BackgroundTask
    v=s.get(Version,version_id)
    if not v:raise HTTPException(404,'not_found')
    limiter.hit(('inspect',u.id),10,3600)
    handle=tempfile.NamedTemporaryFile(suffix='.zip',delete=False);target=Path(handle.name);handle.close()
    try:
        with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:
            for f in s.scalars(select(File).where(File.version_id==v.id)):archive.write(get(f'{v.game_id}/{v.id}/{f.path}'),f.path)
        s.add(Audit(actor=u.id,action='download_review_archive',target=v.id));s.commit()
        return FileResponse(target,media_type='application/zip',filename=f'aurevix-review-{v.id}.zip',background=BackgroundTask(target.unlink,missing_ok=True),headers={'Cache-Control':'no-store'})
    except Exception:
        target.unlink(missing_ok=True);raise
