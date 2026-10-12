from fastapi import HTTPException
class BodyLimit:
    def __init__(self,app,max_bytes=34*1024*1024):self.app=app;self.max_bytes=max_bytes
    async def __call__(self,scope,receive,send):
        if scope['type']!='http' or not scope['path'].startswith('/api'):
            return await self.app(scope,receive,send)
        total=0;exceeded=False;body_sent=False
        payload=b'{"error":{"code":"file_size"}}'
        async def bounded_receive():
            nonlocal total,exceeded
            message=await receive();total+=len(message.get('body',b''))
            if total>self.max_bytes:
                exceeded=True;raise HTTPException(413,'file_size')
            return message
        async def bounded_send(message):
            nonlocal body_sent
            if exceeded and message['type']=='http.response.start':
                # Some request parsers translate receive errors into 400. Keep a uniform 413.
                message=message|{'status':413,'headers':[(k,v) for k,v in message.get('headers',[]) if k not in [b'content-length',b'content-type']]+[(b'content-type',b'application/json'),(b'content-length',str(len(payload)).encode())]}
            elif exceeded and message['type']=='http.response.body':
                if body_sent:return
                body_sent=True;message={'type':'http.response.body','body':payload,'more_body':False}
            await send(message)
        await self.app(scope,bounded_receive,bounded_send)
