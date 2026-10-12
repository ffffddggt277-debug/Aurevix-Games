export const API=(process.env.NEXT_PUBLIC_API_URL||'http://localhost:7860').replace(/\/$/,'');
export interface User {id:string;nickname:string;bio:string;avatar:string;admin:boolean;created_at:string}
export interface Version {id:string;label:string;status:string;reason:string;created_at:string;play_url?:string}
export interface Game {id:string;owner_id:string;title_ru:string;title_en:string;description_ru:string;description_en:string;controls_ru:string;controls_en:string;genres:string[];tags:string[];platforms:string[];multiplayer:boolean;demo:boolean;plays:number;rating:number|null;icon:string;screenshots:string[];author:string;version:string|null;created_at:string;updated_at:string;play_url:string|null;versions?:Version[];blocked?:boolean}
export class ApiError extends Error {constructor(public code:string,public status:number){super(code)}}
export async function request<T>(path:string,init:RequestInit={},token='',signal?:AbortSignal):Promise<T>{
 const headers=new Headers(init.headers);if(token)headers.set('Authorization',`Bearer ${token}`);
 if(init.body && !(init.body instanceof FormData))headers.set('Content-Type','application/json');
 const response=await fetch(`${API}/api${path}`,{...init,headers,signal:signal||AbortSignal.timeout(35000),cache:'no-store'});
 const data=await response.json();if(!response.ok)throw new ApiError(data?.error?.code||'request_failed',response.status);return data;
}
export function media(key:string){return key?`${API}/api/media/${key}`:'/nebula.jpg'}
