"use client";

import { FadeIn } from "@/components/pitch/FadeIn";

export function PitchFounderBridge() {
  return (
    <section
      id="founders"
      className="relative flex min-h-[100svh] items-center justify-center overflow-hidden border-t border-white/[0.06] bg-[#020617] px-8 py-32 scroll-mt-16 sm:px-16 lg:px-24"
    >
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_24%,rgba(162,179,255,0.12),transparent_24%),radial-gradient(circle_at_16%_78%,rgba(108,128,255,0.07),transparent_28%),radial-gradient(circle_at_84%_78%,rgba(112,205,255,0.06),transparent_28%)]" />

      <div className="relative mx-auto max-w-5xl text-center">
        <FadeIn>
          <p className="text-[10px] sm:text-[11px] font-semibold uppercase tracking-[0.34em] text-[#c8d4ff]/72">
            Founders
          </p>
        </FadeIn>
        <FadeIn delay={120}>
          <h2
            className="mt-6 text-balance font-semibold leading-[0.96] tracking-[-0.06em] text-white"
            style={{ fontSize: "clamp(3rem, 7vw, 6rem)" }}
          >
            The Minds Behind...
          </h2>
        </FadeIn>
      </div>
    </section>
  );
}
