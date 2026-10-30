import type {Metadata} from 'next';
import './globals.css';
export const metadata:Metadata={title:'NB Dispatch',description:'Restaurant delivery planning and dispatch',manifest:'/manifest.json'};
export default function Layout({children}:{children:React.ReactNode}){return <html lang="en"><body>{children}</body></html>}
