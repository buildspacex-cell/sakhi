"use client";

import type { ReactNode } from "react";

export default function ThoughtParticle({
  text,
  top,
  left,
  className = "",
  blip = false,
  markerSize = "base",
}: {
  text: ReactNode;
  top: string;
  left: string;
  className?: string;
  blip?: boolean;
  markerSize?: "base" | "lg";
}) {
  const markerSizeClasses = {
    base: {
      marker: "h-5 w-5",
      dot: "h-2.5 w-2.5",
      gap: "gap-3",
      text: "",
    },
    lg: {
      marker: "h-6 w-6",
      dot: "h-3.5 w-3.5",
      gap: "gap-3.5",
      text: "text-[1.08em]",
    },
  } as const;

  const size = markerSizeClasses[markerSize];

  return (
    <div
      className={`thought absolute text-sm text-white/60 blur-[0.2px] ${className}`}
      style={{ top, left }}
    >
      {blip ? (
        <div className={`relative flex items-center ${size.gap}`}>
          <span
            className={`blip-marker relative inline-flex shrink-0 items-center justify-center ${size.marker}`}
          >
            <span
              className={`absolute rounded-full bg-white/95 ${size.dot}`}
              style={{ boxShadow: "0 0 10px rgba(255,255,255,0.26)" }}
            />
          </span>
          <span className={size.text}>{text}</span>
        </div>
      ) : (
        text
      )}
    </div>
  );
}
