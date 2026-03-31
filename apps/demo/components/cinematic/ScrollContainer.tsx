"use client";

import type { ReactNode } from "react";

type ScrollContainerProps = {
  children: ReactNode;
  id?: string;
};

export default function ScrollContainer({
  children,
  id,
}: ScrollContainerProps) {
  return (
    <div
      id={id}
      className="cinematic-scroll relative h-[100svh] overflow-y-auto overscroll-y-contain snap-y snap-mandatory scroll-smooth bg-[#0f1115] text-white"
    >
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.08),transparent_18%),linear-gradient(180deg,rgba(8,10,15,0.2),rgba(8,10,15,0.76))]" />
        <div className="absolute left-[-12%] top-[-10%] h-[34rem] w-[34rem] rounded-full bg-[#6f8dff]/18 blur-3xl" />
        <div className="absolute right-[-10%] top-[16%] h-[28rem] w-[28rem] rounded-full bg-white/8 blur-3xl" />
        <div className="absolute bottom-[-14%] left-[18%] h-[30rem] w-[30rem] rounded-full bg-[#3f5bff]/14 blur-3xl" />
        <div className="absolute inset-0 bg-[linear-gradient(135deg,rgba(255,255,255,0.04),transparent_32%,transparent_68%,rgba(255,255,255,0.03))]" />
      </div>

      <div className="relative isolate">{children}</div>
    </div>
  );
}
