import type { Metadata } from 'next';
import './globals.css';
export const metadata:Metadata={title:'Aurevix Games — Твоя вселенная игр',description:'Бесплатные браузерные игры. Играй, создавай, делись.'};
export default function Layout({children}:{children:React.ReactNode}){return <html lang="ru"><body>{children}</body></html>}
