import {Suspense} from 'react';
import Portal from '@/components/Portal';
export default function Page(){return <Suspense fallback={<main style={{padding:48}}>Aurevix Games…</main>}><Portal/></Suspense>}
