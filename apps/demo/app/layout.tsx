import type { ReactNode } from "react";
import "./globals.css";

export const metadata = {
  title: "Sakhi Demo",
  description: "Narrative roadmap demo for Sakhi",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[#0f1115] text-slate-50 antialiased">
        {children}
      </body>
    </html>
  );
}
