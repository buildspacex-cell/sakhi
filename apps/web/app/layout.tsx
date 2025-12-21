import type { ReactNode } from 'react';
import './globals.css';

export const metadata = {
  title: 'Sakhi Web',
  description: 'Web experience for Sakhi, built with Next.js'
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-50 text-slate-900 antialiased">
        {children}
      </body>
    </html>
  );
}
