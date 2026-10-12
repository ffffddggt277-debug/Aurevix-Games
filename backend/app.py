import os
if __name__ == "__main__" and os.getenv("LOAD_LOCAL_ENV", "1") == "1":
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__),".env"),override=False)
from contextlib import asynccontextmanager
from fastapi import FastAPI,Request,HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse,RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from aurevix.api import router
from aurevix.config import ORIGINS,PRODUCTION
from aurevix.security import limiter
@asynccontextmanager
async def lifespan(app):
    # Migration is explicit, never silently create production tables.
    if os.getenv('AUTO_CREATE_TABLES')=='1':
        from aurevix.models import Base,engine
        Base.metadata.create_all(engine)
    yield
api=FastAPI(title='Aurevix Games API',version='1.0.0',lifespan=lifespan)
@api.exception_handler(HTTPException)
async def http_error(request,exc):return JSONResponse({'error':{'code':exc.detail if isinstance(exc.detail,str) else 'request_failed'}},status_code=exc.status_code)
@api.exception_handler(RequestValidationError)
async def validation(request,exc):return JSONResponse({'error':{'code':'validation_error'}},status_code=422)
@api.exception_handler(Exception)
async def failure(request,exc):return JSONResponse({'error':{'code':'internal_error'}},status_code=500)
@api.middleware('http')
async def guard(request:Request,call_next):
    if request.url.path.startswith('/api'):
        origin=request.headers.get('origin')
        if origin and origin not in ORIGINS and not request.url.path.startswith('/api/content/'):return JSONResponse({'error':{'code':'origin_forbidden'}},status_code=403)
        try:limiter.hit(('global',request.client.host),180)
        except HTTPException:return JSONResponse({'error':{'code':'rate_limit'}},status_code=429)
        length=request.headers.get('content-length')
        if length and (not length.isdigit() or int(length)>34*1024*1024):return JSONResponse({'error':{'code':'file_size'}},status_code=413)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='no-referrer'
    if request.url.path in ['/docs','/redoc']:
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https://fastapi.tiangolo.com; frame-ancestors 'none'"
    elif request.url.path in ['/docs','/redoc']:
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https://fastapi.tiangolo.com; frame-ancestors 'none'"
    elif not request.url.path.startswith('/api/content/'):
        response.headers['X-Frame-Options']='DENY'
        response.headers['Content-Security-Policy']="default-src 'self'; frame-ancestors 'none'; object-src 'none'"
    if request.url.path.startswith('/gradio') or request.url.path=='/':
        if 'X-Frame-Options' in response.headers:del response.headers['X-Frame-Options']
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; connect-src 'self'; frame-ancestors https://huggingface.co"
    if request.url.path.startswith(('/api/auth','/api/me','/api/admin','/api/versions','/api/sdk')):response.headers['Cache-Control']='no-store'
    return response
from aurevix.bodylimit import BodyLimit
api.add_middleware(BodyLimit)
api.add_middleware(CORSMiddleware,allow_origins=ORIGINS,allow_methods=['GET','POST','PATCH','PUT','DELETE','OPTIONS'],allow_headers=['Authorization','Content-Type'],allow_credentials=False)
@api.get('/health')
def health():
    from aurevix.models import SessionLocal
    from sqlalchemy import text
    with SessionLocal() as s:s.execute(text('SELECT 1'))
    return {'status':'ok','persistence_confirmed':os.getenv('PERSISTENCE_CONFIRMED')=='yes'}
@api.get('/',include_in_schema=False)
def index():return RedirectResponse('/gradio')
api.include_router(router,prefix='/api')
app=api
if os.getenv('ENABLE_GRADIO','1')=='1':
    import gradio as gr
    with gr.Blocks(title='Aurevix API') as blank:
        gr.Markdown('# Aurevix Games backend\nAPI health: `/health` · OpenAPI: `/openapi.json` · Docs: `/docs`\nNo user games are executed on this server.')
    blocked=[os.path.abspath('.env'),os.path.abspath(os.getenv('DATA_DIR','./var'))]
    if os.getenv('PERSISTENT_DIR'):blocked.append(os.path.abspath(os.environ['PERSISTENT_DIR']))
    app=gr.mount_gradio_app(api,blank,path='/gradio',blocked_paths=blocked)
if __name__=='__main__':
    from alembic.config import Config
    from alembic import command
    command.upgrade(Config('alembic.ini'),'head')
    from aurevix.persistence import checkpoint
    from aurevix.config import DATA
    checkpoint(DATA)
    import uvicorn
    uvicorn.run(app,host='0.0.0.0',port=int(os.getenv('PORT','7860')),proxy_headers=False)
