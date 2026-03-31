"use client";

import { FadeIn } from "@/components/pitch/FadeIn";

const voicePillars = [
  {
    voice: "I see you.",
    body: "Build a living model of you evolving over time.",
  },
  {
    voice: "I understand you.",
    body: "Make your life visible across time, as a whole.",
  },
  {
    voice: "I act for you.",
    body: "Help you act decisively and learn from what follows.",
  },
];

export function PitchVision() {
  return (
    <section
      id="vision"
      className="relative overflow-hidden border-t border-white/[0.06] bg-[#020617] px-8 py-32 scroll-mt-16 sm:px-16 lg:px-24"
    >
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_18%,rgba(162,179,255,0.14),transparent_22%),radial-gradient(circle_at_18%_72%,rgba(108,128,255,0.08),transparent_28%),radial-gradient(circle_at_82%_76%,rgba(112,205,255,0.06),transparent_28%)]" />

      <div className="relative mx-auto max-w-6xl">
        <FadeIn>
          <p className="text-[10px] sm:text-[11px] font-semibold uppercase tracking-[0.3em] text-[#8ab0ff]/80">
            Vision
          </p>
        </FadeIn>

        <FadeIn delay={100}>
          <h2
            className="mt-5 max-w-[12ch] font-semibold leading-[0.98] -tracking-[0.06em] text-white"
            style={{ fontSize: "clamp(3rem, 6.5vw, 5.8rem)" }}
          >
            Sakhi makes your life seen, understood, and actionable.
          </h2>
        </FadeIn>

        <div className="mt-16 grid gap-6 md:grid-cols-3">
          {voicePillars.map((pillar, index) => (
            <FadeIn key={pillar.voice} delay={200 + index * 100}>
              <div className="h-full rounded-[30px] border border-white/[0.08] bg-white/[0.03] px-6 py-7">
                <p
                  className="text-balance font-semibold leading-[1.04] -tracking-[0.05em] text-white"
                  style={{ fontSize: "clamp(2rem, 3vw, 3.2rem)" }}
                >
                  {pillar.voice}
                </p>
                <p className="mt-5 text-balance text-[1rem] leading-[1.6] tracking-[-0.02em] text-white/55">
                  {pillar.body}
                </p>
              </div>
            </FadeIn>
          ))}
        </div>

        <FadeIn delay={560}>
          <p className="mt-10 text-[0.92rem] font-medium uppercase tracking-[0.28em] text-[#c8d4ff]/74">
            - Sakhi
          </p>
        </FadeIn>
      </div>
    </section>
  );
}
