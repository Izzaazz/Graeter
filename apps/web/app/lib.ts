export async function api<T>(path:string,method='GET',body?:unknown):Promise<T>{
 const r=await fetch('/api'+path,{method,headers:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});
 if(!r.ok){let message='Request failed';try{const error=await r.json();message=typeof error.detail==='string'?error.detail:JSON.stringify(error.detail)}catch{}throw new Error(message)}
 return r.json();
}
export const clock=(s:string)=>new Date(s).toLocaleTimeString('en-GB',{hour:'2-digit',minute:'2-digit',timeZone:'Europe/London'});
export const minutes=(seconds:number)=>Math.round(seconds/60);
export function navigation(lat:number,lng:number){return `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}&travelmode=driving`}
