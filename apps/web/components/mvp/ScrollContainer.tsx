"use client";

import type { ReactNode } from "react";

type ScrollContainerProps = {
  children: ReactNode;
  id?: string;
};

export function ScrollContainer({ children, id }: ScrollContainerProps) {
  return (
    <div
      id={id}
      className="relative h-[100svh] overflow-y-auto overscroll-y-contain snap-y snap-mandatory scroll-smooth"
    >
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute inset-0 bg-hero-glow opacity-90" />
        <div className="absolute inset-x-0 top-0 h-px bg-white/10" />
      </div>
      <div className="relative isolate">{children}</div>
    </div>
  );
}

export default ScrollContainer;
