"""Single-writer SQLite snapshot persistence; never put WAL on an object mount."""
import os, json, hashlib, sqlite3, tempfile, threading, time, uuid
from pathlib import Path
lock=threading.Lock()
def volume():
    value=os.getenv('PERSISTENT_DIR','')
    return Path(value) if value else None
def restore(data_dir):
    target=data_dir/'aurevix.db';root=volume()
    if not root or target.exists():return
    snapshots=root/'snapshots'
    if not snapshots.exists():return
    for metadata in sorted(snapshots.glob('*.json'),reverse=True):
        try:
            info=json.loads(metadata.read_text());blob=snapshots/info['file'];data=blob.read_bytes()
            if hashlib.sha256(data).hexdigest()!=info['sha256']:continue
            tmp=target.with_suffix('.restore');tmp.write_bytes(data)
            with sqlite3.connect(tmp) as db:
                if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':tmp.unlink();continue
            tmp.replace(target);return
        except (OSError,ValueError,KeyError,sqlite3.DatabaseError):continue
    raise RuntimeError('No valid persistent database snapshot. Restore a verified backup; do not create an empty database.')
def checkpoint(data_dir):
    root=volume()
    if not root:return
    with lock:
        source=data_dir/'aurevix.db'
        if not source.exists():return
        snapshots=root/'snapshots';snapshots.mkdir(parents=True,exist_ok=True)
        name=f'{time.time_ns():020d}-{uuid.uuid4().hex}.db'
        with tempfile.TemporaryDirectory() as temporary:
            local=Path(temporary)/name
            with sqlite3.connect(source) as src,sqlite3.connect(local) as dst:src.backup(dst)
            data=local.read_bytes()
        (snapshots/name).write_bytes(data)
        (snapshots/(name+'.json')).write_text(json.dumps({'file':name,'sha256':hashlib.sha256(data).hexdigest()}))
        # Small deployment, one writer. Keep five complete snapshots.
        complete=sorted(snapshots.glob('*.json'),reverse=True)
        for meta in complete[5:]:
            try:
                old=json.loads(meta.read_text())['file'];meta.unlink();(snapshots/old).unlink(missing_ok=True)
            except (OSError,ValueError,KeyError):pass
