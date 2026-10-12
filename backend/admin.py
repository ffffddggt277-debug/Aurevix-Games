"""Offline privilege assignment. Run only with trusted shell access to backend."""
import argparse
from sqlalchemy import select
from aurevix.models import SessionLocal,User,Audit
p=argparse.ArgumentParser();p.add_argument('nickname');p.add_argument('--revoke',action='store_true');a=p.parse_args()
with SessionLocal() as s:
    u=s.scalar(select(User).where(User.nickname_key==a.nickname.lower()))
    if not u:raise SystemExit('Register this user first')
    u.admin=not a.revoke;s.add(Audit(actor='operator',action='revoke_admin' if a.revoke else 'grant_admin',target=u.id));s.commit()
print('Updated administrator role')
