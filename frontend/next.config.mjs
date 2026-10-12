import path from 'node:path';
const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:7860';
const backend = new URL(API).origin;
export default {
  poweredByHeader: false,
  outputFileTracingRoot: path.resolve(import.meta.dirname),
  turbopack: {root: path.resolve(import.meta.dirname)},
  async headers() {return [{source:'/:path*',headers:[
    {key:'X-Content-Type-Options',value:'nosniff'},
    {key:'Referrer-Policy',value:'no-referrer'},
    {key:'X-Frame-Options',value:'DENY'},
    {key:'Permissions-Policy',value:'camera=(), microphone=(), geolocation=()'},
    {key:'Content-Security-Policy',value:`default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' ${backend} data: blob:; connect-src 'self' ${backend}; frame-src ${backend}; font-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'`}
  ]}];}
};
