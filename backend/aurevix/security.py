import hashlib, secrets, time, threading, re
from collections import defaultdict, deque
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session as DBSession
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from .models import User, Session, db
ph=PasswordHasher(time_cost=2,memory_cost=19456,parallelism=1)
DUMMY_HASH=ph.hash(secrets.token_urlsafe(24))
def digest(t): return hashlib.sha256(t.encode()).hexdigest()
def verify(h,p):
    try: return ph.verify(h,p)
    except VerificationError: return False
class Limiter:
    def __init__(self): self.items=defaultdict(deque); self.lock=threading.Lock()
    def hit(self,key,limit,window=60):
        with self.lock:
            t=time.monotonic(); q=self.items[key]
            while q and q[0]<t-window: q.popleft()
            if len(q)>=limit: raise HTTPException(429,'rate_limit')
            q.append(t)
            if len(self.items)>10000:
                for k in list(self.items):
                    if not self.items[k] or self.items[k][-1]<t-3600: del self.items[k]
limiter=Limiter()
def current(request:Request,s:DBSession=Depends(db)):
    auth=request.headers.get('authorization','')
    if not auth.startswith('Bearer '): raise HTTPException(401,'unauthorized')
    token=s.get(Session,digest(auth[7:]))
    if not token or token.expires<time.time(): raise HTTPException(401,'unauthorized')
    u=s.get(User,token.user_id)
    if not u: raise HTTPException(401,'unauthorized')
    return u
def admin(u:User=Depends(current)):
    if not u.admin: raise HTTPException(403,'forbidden')
    return u
def issue(s,u):
    raw=secrets.token_urlsafe(48)
    s.add(Session(digest=digest(raw),user_id=u.id,expires=int(time.time())+86400));s.commit()
    return {'token':raw,'expires_in':86400,'user':public_user(u)}
def public_user(u): return {'id':u.id,'nickname':u.nickname,'bio':u.bio,'avatar':u.avatar,'admin':u.admin,'created_at':u.created_at}
