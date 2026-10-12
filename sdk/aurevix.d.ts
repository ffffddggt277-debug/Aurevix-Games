export interface Board {competitive:false;verified:false;items:{nickname:string;value:number}[]}
export interface Init {gameId:string;authenticated:boolean;competitive:false}
export class AurevixError extends Error {code:string}
export class AurevixSDK {
 constructor(gameId:string,options?:{parentOrigin?:string});
 init():Promise<Init>;
 submitScore(value:number):Promise<{accepted:boolean;verified:false;competitive:false}>;
 getLeaderboard():Promise<Board>;
 destroy():void;
}
