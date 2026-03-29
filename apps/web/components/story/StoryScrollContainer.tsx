"use client";

import type { ReactNode } from "react";

type StoryScrollContainerProps = {
  children: ReactNode;
  id?: string;
};

export default function StoryScrollContainer({
  children,
  id,
}: StoryScrollContainerProps) {
  return (
    <div
      id={id}
      className="relative min-h-screen bg-[#0a0d13] text-white"
    >
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_12%_18%,rgba(115,146,255,0.16),transparent_28%),radial-gradient(circle_at_84%_26%,rgba(255,255,255,0.06),transparent_18%),radial-gradient(circle_at_58%_82%,rgba(111,141,255,0.11),transparent_24%),linear-gradient(180deg,#0f1219_0%,#0a0d13_42%,#090c12_100%)]" />
        <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:96px_96px] opacity-[0.045] [mask-image:radial-gradient(circle_at_center,black_26%,transparent_82%)]" />
        <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(10,13,19,0.2),rgba(10,13,19,0.78))]" />
      </div>

      <div className="relative isolate">{children}</div>
    </div>
  );
}
