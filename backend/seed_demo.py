"""Explicit opt-in seed. No fake users, ratings, plays or scores."""
import json,hashlib,secrets
from pathlib import Path
from PIL import Image
from sqlalchemy import select
from aurevix.models import *
from aurevix.security import ph
from aurevix.storage import put
names=[('Космический дрейф','Cosmic Drift','arcade'),('Призма','Prism Grid','puzzle'),('Звездопад','Starfall','arcade'),('Лунные пары','Lunar Match','puzzle'),('Бег сквозь пустоту','Void Runner','action'),('Неоновая орбита','Neon Orbit','adventure')]
root=Path(__file__).resolve().parent/'demo'
with SessionLocal() as s:
    u=s.scalar(select(User).where(User.nickname_key=='aurevix_demo'))
    if not u:
        u=User(nickname='Aurevix_Demo',nickname_key='aurevix_demo',password_hash=ph.hash(secrets.token_urlsafe(48)),bio='Демонстрационные игры платформы / Platform demo games');s.add(u);s.flush()
    for mode,(ru,en,genre) in enumerate(names):
        if s.scalar(select(Game).where(Game.owner_id==u.id,Game.title_en==en)):continue
        g=Game(id=uid(),owner_id=u.id,title_ru=ru,title_en=en,description_ru='Демонстрационная браузерная игра Aurevix. Бесплатный пример для проверки игрового плеера. Не является публикацией реального пользователя.',description_en='An Aurevix browser demo. A free example for testing the game player, not a real user publication.',genres=json.dumps([genre]),tags=json.dumps(['demo','space']),platforms=json.dumps(['desktop','mobile']),controls_ru='Мышь, касание или стрелки. Инструкция внутри игры.',controls_en='Mouse, touch or arrow keys. Instructions inside the game.',demo=True)
        v=Version(id=uid(),game_id=g.id,label='1.0.0',status='approved',reason='bundled_demo_reviewed')
        s.add(g);s.flush();s.add(v);s.flush();g.current_version=v.id
        body=(root/'game.html').read_text().replace('__MODE__',str(mode)).replace('__NAMES__',json.dumps({'ru':ru,'en':en},ensure_ascii=False)).encode()
        put(f'{g.id}/{v.id}/index.html',body);s.add(File(version_id=v.id,path='index.html',size=len(body),sha256=hashlib.sha256(body).hexdigest()))
        from io import BytesIO
        cover=root/f'covers/{mode}.webp'
        im=Image.open(cover if cover.exists() else root/'nebula.jpg');im=im.resize((800,500))
        out=BytesIO();im.save(out,'WEBP',quality=90)
        keys=[]
        for n in range(3):
            key=f'media/{g.id}/{n}.webp';put(key,out.getvalue());keys.append(key)
        g.icon=keys[0];g.screenshots=json.dumps(keys[1:]);s.add(Moderation(version_id=v.id,decision='approved',reason='bundled_demo_reviewed'))
    s.commit()
print('Demo games created (explicitly marked; no fabricated activity).')
