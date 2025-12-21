import { PropsWithChildren } from "react";

export function Card({ children, className = "" }: PropsWithChildren<{ className?: string }>) {
  return (
    <div className={`rounded-lg border border-slate-200 bg-white shadow-sm ${className}`.trim()}>
      {children}
    </div>
  );
}
