import {NextRequest,NextResponse} from 'next/server';
export const runtime='nodejs';export const dynamic='force-dynamic';
const backend=()=>process.env.BACKEND_URL||'http://127.0.0.1:8000';
const unsafe=(method:string)=>!['GET','HEAD','OPTIONS'].includes(method);
function csrfSafe(req:NextRequest){
 if(!unsafe(req.method))return true;
 const site=req.headers.get('sec-fetch-site');
 if(site==='cross-site')return false;
 if(site==='same-origin')return true;
 const origin=req.headers.get('origin');
 if(!origin)return true;
 const forwardedHost=req.headers.get('x-forwarded-host')?.split(',')[0]?.trim();
 const host=forwardedHost||req.headers.get('host');
 const forwardedProto=req.headers.get('x-forwarded-proto')?.split(',')[0]?.trim();
 const protocol=forwardedProto||req.nextUrl.protocol.replace(':','');
 const requestOrigin=host?`${protocol}://${host}`:req.nextUrl.origin;
 return origin===requestOrigin||origin===req.nextUrl.origin;
}
async function proxy(req:NextRequest,{params}:{params:Promise<{path:string[]}>}){
 if(!csrfSafe(req))return NextResponse.json({error:{code:'CSRF_REJECTED',message:'Cross-site state-changing requests are not allowed'}},{status:403});
 const size=Number(req.headers.get('content-length')||0);if(size>1_000_000)return NextResponse.json({error:{code:'PAYLOAD_TOO_LARGE',message:'Request body exceeds 1 MB'}},{status:413});
 const {path}=await params;const token=req.cookies.get('swa_access')?.value;const url=new URL(`${backend()}/${path.map(encodeURIComponent).join('/')}`);req.nextUrl.searchParams.forEach((value,key)=>url.searchParams.append(key,value));const headers=new Headers();const contentType=req.headers.get('content-type');if(contentType)headers.set('content-type',contentType);if(token)headers.set('authorization',`Bearer ${token}`);const clientIp=req.headers.get('x-forwarded-for')?.split(',')[0]?.trim();if(clientIp)headers.set('x-forwarded-for',clientIp);let body:BodyInit|undefined;if(!['GET','HEAD'].includes(req.method))body=await req.arrayBuffer();
 try{const upstream=await fetch(url,{method:req.method,headers,body,cache:'no-store'});const payload=await upstream.arrayBuffer();const response=new NextResponse(payload,{status:upstream.status,headers:{'content-type':upstream.headers.get('content-type')||'application/json','cache-control':'no-store'}});const authPath=path.join('/');if(upstream.ok&&['auth/login','auth/register'].includes(authPath)){const data=JSON.parse(new TextDecoder().decode(payload));const secure=process.env.COOKIE_SECURE==='false'?false:process.env.NODE_ENV==='production';response.cookies.set('swa_access',data.access_token,{httpOnly:true,secure,sameSite:'lax',path:'/',maxAge:data.expires_in})}if(authPath==='auth/logout')response.cookies.delete('swa_access');return response}catch{return NextResponse.json({error:{code:'BACKEND_UNAVAILABLE',message:'Core API is unavailable'}},{status:503})}
}
export const GET=proxy;export const POST=proxy;export const PUT=proxy;export const PATCH=proxy;export const DELETE=proxy;
