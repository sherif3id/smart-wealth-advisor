import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = { title: 'Smart Wealth Advisor', description: 'AI-powered wealth management, made personal.' };
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="en"><body>{children}</body></html>}
