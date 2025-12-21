import { PropsWithChildren } from "react";

interface BadgeProps {
  className?: string;
  variant?: "default" | "secondary";
}

export function Badge({ children, className = "", variant = "default" }: PropsWithChildren<BadgeProps>) {
  const base =
    variant === "secondary"
      ? "bg-slate-100 text-slate-600"
      : "bg-slate-900 text-white";
  return (
    <span className={`inline-flex items-center rounded-sm px-2 py-0.5 text-[11px] font-medium ${base} ${className}`.trim()}>
      {children}
    </span>
  );
}
