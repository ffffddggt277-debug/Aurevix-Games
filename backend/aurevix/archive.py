import io, zipfile, stat, hashlib
from pathlib import PurePosixPath
from fastapi import HTTPException
from .config import MAX_ZIP,MAX_FILES,MAX_EXPANDED
ALLOWED={'.html','.htm','.css','.js','.mjs','.json','.wasm','.png','.jpg','.jpeg','.webp','.gif','.ico','.mp3','.ogg','.wav','.mp4','.webm','.woff','.woff2','.ttf','.otf','.txt','.data','.bin','.unityweb'}
def inspect_zip(data:bytes):
    if len(data)>MAX_ZIP: raise HTTPException(413,'zip_size')
    result={}; total=0; seen=set()
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            infos=z.infolist()
            if len(infos)>MAX_FILES: raise HTTPException(422,'zip_files')
            for i in infos:
                name=i.filename; p=PurePosixPath(name)
                if '\\' in name or '\x00' in name or ':' in name or name.startswith('/') or '..' in p.parts or len(name)>240:
                    raise HTTPException(422,'zip_path')
                mode=i.external_attr>>16
                if stat.S_ISLNK(mode) or i.flag_bits&1: raise HTTPException(422,'zip_type')
                if i.is_dir(): continue
                normalized=str(p)
                if normalized.casefold() in seen: raise HTTPException(422,'zip_duplicate')
                seen.add(normalized.casefold())
                if p.suffix.lower() not in ALLOWED: raise HTTPException(422,'zip_type')
                total+=i.file_size
                if total>MAX_EXPANDED or i.file_size>25*1024*1024 or (i.file_size>1024*1024 and i.file_size/max(1,i.compress_size)>150):
                    raise HTTPException(422,'zip_bomb')
                body=z.read(i)
                if len(body)!=i.file_size: raise HTTPException(422,'zip_corrupt')
                result[normalized]=body
    except (zipfile.BadZipFile,RuntimeError,ValueError,NotImplementedError,EOFError): raise HTTPException(422,'zip_corrupt')
    if 'index.html' not in result: raise HTTPException(422,'zip_entry')
    return result
