import uuid
from datetime import datetime, timezone
from sqlalchemy import create_engine, String, Text, Integer, Boolean, ForeignKey, UniqueConstraint, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session as SASession
from .config import DATABASE_URL

def uid(): return uuid.uuid4().hex
def now(): return datetime.now(timezone.utc).isoformat()
class Base(DeclarativeBase): pass
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False, "timeout": 20} if DATABASE_URL.startswith('sqlite') else {})
if DATABASE_URL.startswith('sqlite'):
    @event.listens_for(engine, "connect")
    def setup_sqlite(conn, record):
        conn.execute('PRAGMA foreign_keys=ON'); conn.execute('PRAGMA journal_mode=WAL')
class DurableSession(SASession):
    def commit(self):
        super().commit()
        from .config import DATA
        from .persistence import checkpoint
        checkpoint(DATA)
SessionLocal = sessionmaker(engine, class_=DurableSession, expire_on_commit=False)
class User(Base):
    __tablename__='users'
    id: Mapped[str]=mapped_column(String(32),primary_key=True,default=uid)
    nickname: Mapped[str]=mapped_column(String(32),unique=True)
    nickname_key: Mapped[str]=mapped_column(String(32),unique=True)
    password_hash: Mapped[str]=mapped_column(Text)
    bio: Mapped[str]=mapped_column(String(600),default='')
    avatar: Mapped[str]=mapped_column(String(100),default='')
    admin: Mapped[bool]=mapped_column(Boolean,default=False)
    created_at: Mapped[str]=mapped_column(String,default=now)
class Session(Base):
    __tablename__='sessions'
    digest: Mapped[str]=mapped_column(String(64),primary_key=True)
    user_id: Mapped[str]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'))
    expires: Mapped[int]=mapped_column(Integer)
class Game(Base):
    __tablename__='games'
    id: Mapped[str]=mapped_column(String(32),primary_key=True,default=uid)
    owner_id: Mapped[str]=mapped_column(ForeignKey('users.id'))
    title_ru: Mapped[str]=mapped_column(String(100))
    title_en: Mapped[str]=mapped_column(String(100))
    description_ru: Mapped[str]=mapped_column(Text)
    description_en: Mapped[str]=mapped_column(Text)
    genres: Mapped[str]=mapped_column(Text,default='[]')
    tags: Mapped[str]=mapped_column(Text,default='[]')
    platforms: Mapped[str]=mapped_column(Text,default='["desktop"]')
    controls_ru: Mapped[str]=mapped_column(String(600),default='')
    controls_en: Mapped[str]=mapped_column(String(600),default='')
    multiplayer: Mapped[bool]=mapped_column(Boolean,default=False)
    demo: Mapped[bool]=mapped_column(Boolean,default=False)
    blocked: Mapped[bool]=mapped_column(Boolean,default=False)
    current_version: Mapped[str | None]=mapped_column(String(32),nullable=True)
    icon: Mapped[str]=mapped_column(String(100),default='')
    screenshots: Mapped[str]=mapped_column(Text,default='[]')
    plays: Mapped[int]=mapped_column(Integer,default=0)
    created_at: Mapped[str]=mapped_column(String,default=now)
    updated_at: Mapped[str]=mapped_column(String,default=now)
class Version(Base):
    __tablename__='versions'
    __table_args__=(UniqueConstraint('game_id','label'),)
    id: Mapped[str]=mapped_column(String(32),primary_key=True,default=uid)
    game_id: Mapped[str]=mapped_column(ForeignKey('games.id'))
    label: Mapped[str]=mapped_column(String(40))
    status: Mapped[str]=mapped_column(String(20),default='pending')
    reason: Mapped[str]=mapped_column(Text,default='')
    entry: Mapped[str]=mapped_column(String(300),default='index.html')
    metadata_json: Mapped[str]=mapped_column(Text,default='{}')
    created_at: Mapped[str]=mapped_column(String,default=now)
class File(Base):
    __tablename__='files'
    id: Mapped[str]=mapped_column(String(32),primary_key=True,default=uid)
    version_id: Mapped[str]=mapped_column(ForeignKey('versions.id'))
    path: Mapped[str]=mapped_column(String(300))
    size: Mapped[int]=mapped_column(Integer)
    sha256: Mapped[str]=mapped_column(String(64))
class Favorite(Base):
    __tablename__='favorites'
    user_id: Mapped[str]=mapped_column(ForeignKey('users.id'),primary_key=True)
    game_id: Mapped[str]=mapped_column(ForeignKey('games.id'),primary_key=True)
class Rating(Base):
    __tablename__='ratings'
    user_id: Mapped[str]=mapped_column(ForeignKey('users.id'),primary_key=True)
    game_id: Mapped[str]=mapped_column(ForeignKey('games.id'),primary_key=True)
    value: Mapped[int]=mapped_column(Integer)
class Score(Base):
    __tablename__='scores'
    id: Mapped[str]=mapped_column(String(32),primary_key=True,default=uid)
    user_id: Mapped[str]=mapped_column(ForeignKey('users.id'))
    game_id: Mapped[str]=mapped_column(ForeignKey('games.id'))
    value: Mapped[int]=mapped_column(Integer)
    verified: Mapped[bool]=mapped_column(Boolean,default=False)
    created_at: Mapped[str]=mapped_column(String,default=now)
class PlaySession(Base):
    __tablename__='play_sessions'
    id: Mapped[str]=mapped_column(String(64),primary_key=True)
    user_id: Mapped[str]=mapped_column(ForeignKey('users.id'))
    game_id: Mapped[str]=mapped_column(ForeignKey('games.id'))
    expires: Mapped[int]=mapped_column(Integer)
    used: Mapped[bool]=mapped_column(Boolean,default=False)
class Moderation(Base):
    __tablename__='moderation'
    id: Mapped[str]=mapped_column(String(32),primary_key=True,default=uid)
    version_id: Mapped[str]=mapped_column(ForeignKey('versions.id'))
    decision: Mapped[str]=mapped_column(String(20))
    reason: Mapped[str]=mapped_column(Text)
    created_at: Mapped[str]=mapped_column(String,default=now)
class Audit(Base):
    __tablename__='audit'
    id: Mapped[str]=mapped_column(String(32),primary_key=True,default=uid)
    actor: Mapped[str]=mapped_column(String(32))
    action: Mapped[str]=mapped_column(String(100))
    target: Mapped[str]=mapped_column(String(32))
    reason: Mapped[str]=mapped_column(String(1000),default='')
    created_at: Mapped[str]=mapped_column(String,default=now)
def db():
    with SessionLocal() as s: yield s

def apply_version(g,v):
    import json
    fields=json.loads(v.metadata_json or '{}')
    for k,val in fields.items():
        if k in ['genres','tags','platforms','screenshots']:setattr(g,k,json.dumps(val,ensure_ascii=False))
        elif k in ['title_ru','title_en','description_ru','description_en','controls_ru','controls_en','multiplayer','icon']:setattr(g,k,val)
    g.current_version=v.id;g.updated_at=now()
