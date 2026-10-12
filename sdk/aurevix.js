/* Aurevix SDK v1. No credentials are exposed to the game. */
(function(global){
 class AurevixError extends Error {constructor(code){super(code);this.code=code}}
 class AurevixSDK {
  constructor(gameId,options={}){
   this.gameId=gameId;this.pending=new Map();this.seq=0;
   this.origin=options.parentOrigin||new URLSearchParams(global.location.search).get('platformOrigin');
   if(!this.origin||!/^https?:\/\//.test(this.origin)||new URL(this.origin).origin!==this.origin)throw new AurevixError('invalid_parent_origin');
   this.receive=(e)=>{if(e.source!==global.parent||e.origin!==this.origin||e.data?.channel!=='aurevix:v1')return;const pending=this.pending.get(e.data.id);if(!pending)return;clearTimeout(pending.timer);this.pending.delete(e.data.id);e.data.error?pending.reject(new AurevixError(e.data.error)):pending.resolve(e.data.result)};
   global.addEventListener('message',this.receive);
  }
  call(type,payload={}){
   if(global.parent===global)return Promise.reject(new AurevixError('not_embedded'));
   if(this.pending.size>=10)return Promise.reject(new AurevixError('too_many_requests'));
   return new Promise((resolve,reject)=>{const id=`sdk-${Date.now()}-${++this.seq}`;const timer=setTimeout(()=>{this.pending.delete(id);reject(new AurevixError('timeout'))},10000);this.pending.set(id,{resolve,reject,timer});global.parent.postMessage({channel:'aurevix:v1',id,type,payload},this.origin)})
  }
  init(){return this.call('init',{gameId:this.gameId})}
  submitScore(value){if(!Number.isSafeInteger(value)||value<0||value>1000000)return Promise.reject(new AurevixError('invalid_score'));return this.call('score',{value})}
  getLeaderboard(){return this.call('leaderboard')}
  destroy(){global.removeEventListener('message',this.receive);for(const p of this.pending.values()){clearTimeout(p.timer);p.reject(new AurevixError('destroyed'))}this.pending.clear()}
 }
 global.AurevixSDK=AurevixSDK;global.AurevixError=AurevixError;
})(typeof window!=='undefined'?window:globalThis);
