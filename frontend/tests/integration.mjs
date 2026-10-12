/** Uses the actual TypeScript frontend API client against an isolated live backend. */
import assert from 'node:assert/strict';import fs from 'node:fs';import ts from 'typescript';
process.env.NEXT_PUBLIC_API_URL ||= 'http://localhost:7861';
const clientSource=fs.readFileSync('src/lib/api.ts','utf8');
const compiled=ts.transpileModule(clientSource,{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText;
const {API,request,ApiError}=await import('data:text/javascript;base64,'+Buffer.from(compiled).toString('base64'));
assert.equal(API,process.env.NEXT_PUBLIC_API_URL);
let passed=0;const check=(name)=>{passed++;console.log('PASS '+name)};
const nick='Integration_'+Date.now().toString().slice(-8);const password='integration-safe-password';
const health=await fetch(API+'/health');assert.equal(health.status,200);check('health');
const catalog=await request('/games');assert.ok(Array.isArray(catalog.items));check('catalog via frontend API client');
const registration=await request('/auth/register',{method:'POST',body:JSON.stringify({nickname:nick,password})});const token=registration.token;assert.ok(token);check('registration');
const login=await request('/auth/login',{method:'POST',body:JSON.stringify({nickname:nick,password})});assert.ok(login.token);check('login');
const me=await request('/me',{},token);assert.equal(me.nickname,nick);check('profile');
await assert.rejects(request('/me'),e=>e instanceof ApiError&&e.status===401);check('API authorization/error format');
const zip=fs.readFileSync('../examples/minimal-game.zip');const image=fs.readFileSync('../examples/test-image.png');
const body=new FormData();body.set('metadata',JSON.stringify({title_ru:'Интеграционный тест',title_en:'Integration test',description_ru:'Тестовая браузерная игра',description_en:'Integration browser game',genres:['arcade'],tags:['test'],platforms:['desktop'],controls_ru:'Мышь',controls_en:'Mouse',version:'1.0.0'}));body.set('archive',new Blob([zip]),'game.zip');for(const k of ['icon','screenshot1','screenshot2'])body.set(k,new Blob([image],{type:'image/png'}),k+'.png');
const upload=await request('/games/upload',{method:'POST',body},token);assert.ok(upload.version_id);check('ZIP upload');
const moderation=await request('/versions/'+upload.version_id+'/moderation',{},token);assert.equal(moderation.status,'manual_review');check('fail-closed moderation status');
// Explicit trusted offline role grant, not an API backdoor.
const {execFileSync}=await import('node:child_process');
execFileSync(process.env.PYTHON||'python',['admin.py',nick],{cwd:'../backend',env:{...process.env,DATA_DIR:process.env.INTEGRATION_DATA_DIR||'/data/aurevix-it-db',ENABLE_GRADIO:'0'}});
await request('/admin/versions/'+upload.version_id,{method:'POST',body:JSON.stringify({status:'approved',reason:'Local integration test manual approval'})},token);
const game=await request('/games/'+upload.game_id);assert.equal(game.title_en,'Integration test');check('published game page');
await request('/games/'+game.id+'/favorite',{method:'PUT'},token);assert.equal((await request('/me/favorites',{},token))[0].id,game.id);await request('/games/'+game.id+'/favorite',{method:'DELETE'},token);check('persistent favorites');
const allowed=await fetch(API+'/api/games',{method:'OPTIONS',headers:{Origin:'http://localhost:3000','Access-Control-Request-Method':'GET'}});assert.equal(allowed.headers.get('access-control-allow-origin'),'http://localhost:3000');const denied=await fetch(API+'/api/games',{headers:{Origin:'https://evil.example'}});assert.equal(denied.status,403);check('CORS allowed/denied origins');
const session=await request('/sdk/sessions',{method:'POST',body:JSON.stringify({game_id:game.id})},token);const score=await request('/sdk/scores',{method:'POST',body:JSON.stringify({play_token:session.play_token,value:42})},token);assert.equal(score.verified,false);await assert.rejects(request('/sdk/scores',{method:'POST',body:JSON.stringify({play_token:session.play_token,value:43})},token));check('SDK identity and replay protection');
await request('/auth/logout',{method:'POST'},token);await assert.rejects(request('/me',{},token));check('logout invalidates server token');
console.log(`${passed} integration checks passed. Database contains local test data only.`);
