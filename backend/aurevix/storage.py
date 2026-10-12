import io, os, hashlib
from pathlib import Path
from PIL import Image, UnidentifiedImageError
from fastapi import HTTPException
from .config import DATA, MAX_IMAGE
ROOT=Path(os.getenv('PERSISTENT_DIR') or str(DATA))/'objects'; ROOT.mkdir(parents=True,exist_ok=True)
def put(key,data):
    path=ROOT/key; path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp');temp.write_bytes(data);temp.replace(path)
def get(key):
    path=(ROOT/key).resolve()
    if not path.is_relative_to(ROOT.resolve()) or not path.is_file(): raise HTTPException(404,'not_found')
    return path
async def bounded(upload,maximum):
    data=bytearray()
    while chunk:=await upload.read(64*1024):
        data.extend(chunk)
        if len(data)>maximum: raise HTTPException(413,'file_size')
    return bytes(data)
def image(data):
    if len(data)>MAX_IMAGE: raise HTTPException(413,'file_size')
    try:
        with Image.open(io.BytesIO(data)) as im:
            if im.width*im.height>16000000: raise HTTPException(422,'image_invalid')
            im.load(); im.thumbnail((1600,1000)); out=io.BytesIO(); im.convert('RGB').save(out,'WEBP',quality=86); return out.getvalue()
    except (UnidentifiedImageError,OSError,Image.DecompressionBombError): raise HTTPException(422,'image_invalid')
