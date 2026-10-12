import os
from pathlib import Path
DATA = Path(os.getenv("DATA_DIR", "./var"))
DATA.mkdir(parents=True, exist_ok=True)
from .persistence import restore
restore(DATA)
DATABASE_URL = f"sqlite:///{DATA / 'aurevix.db'}"
ORIGINS = [x.strip().rstrip('/') for x in os.getenv("FRONTEND_URL", "http://localhost:3000").split(',') if x.strip()]
MAX_ZIP = 20 * 1024 * 1024
MAX_EXPANDED = 80 * 1024 * 1024
MAX_FILES = 600
MAX_IMAGE = 4 * 1024 * 1024
PRODUCTION = os.getenv("APP_ENV") == "production"
if PRODUCTION and (os.getenv("PERSISTENCE_CONFIRMED") != "yes" or not os.getenv('PERSISTENT_DIR')):
    raise RuntimeError("Configure persistent DATA_DIR and backups; then set PERSISTENCE_CONFIRMED=yes")
