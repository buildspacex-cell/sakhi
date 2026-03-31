"use client";

import { FadeIn } from "@/components/pitch/FadeIn";

const pillars = [
  {
    title: "Learns how you think",
    body: "Builds a living model of you that evolves over time.",
  },
  {
    title: "Makes life visible across time",
    body: "Your life becomes legible as a whole, not a pile of disconnected moments.",
  },
  {
    title: "Helps you act decisively",
    body: "Turns continuity into clearer action and learns from what follows.",
  },
];

export function PitchSolution() {
  return (
    <section
      id="solution"
      className="relative overflow-hidden border-t border-white/[0.06] bg-[#020617] scroll-mt-16"
    >
      {/* "Sakhi makes it all come together." */}
      <div className="min-h-[80svh] flex items-center px-8 sm:px-16 lg:px-24 py-32">
        <div className="mx-auto max-w-6xl w-full">
          <FadeIn>
            <h2
              className="font-semibold text-white leading-[0.96] -tracking-[0.06em]"
              style={{ fontSize: "clamp(3.5rem, 9vw, 8rem)" }}
            >
              Sakhi makes it all come together.
            </h2>
          </FadeIn>
        </div>
      </div>

      {/* "Stop reacting. Start shaping." + explainer + pillars */}
      <div className="min-h-[90svh] flex items-center px-8 sm:px-16 lg:px-24 py-24">
        <div className="mx-auto max-w-6xl w-full">
          <FadeIn>
            <h2
              className="font-semibold text-white leading-[0.96] -tracking-[0.075em]"
              style={{ fontSize: "clamp(3.5rem, 9vw, 8rem)" }}
            >
              Stop reacting.
            </h2>
          </FadeIn>
          <FadeIn delay={150}>
            <h2
              className="font-semibold text-white/20 leading-[0.96] -tracking-[0.075em] mt-1"
              style={{ fontSize: "clamp(3.5rem, 9vw, 8rem)" }}
            >
              Start shaping.
            </h2>
          </FadeIn>

          <FadeIn delay={300}>
            <p className="mt-14 max-w-2xl text-balance text-white/60 leading-[1.5] -tracking-[0.03em]"
              style={{ fontSize: "clamp(1.2rem, 2.1vw, 1.7rem)" }}
            >
              Sakhi learns how you think and evolves with you, so your decisions become clearer over time.
            </p>
          </FadeIn>

          <div className="mt-16 grid sm:grid-cols-3 gap-8">
            {pillars.map((pillar, i) => (
              <FadeIn key={pillar.title} delay={450 + i * 150}>
                <div className="h-full rounded-[28px] border border-white/[0.08] bg-white/[0.03] px-6 py-7">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-[#8ab0ff]/70">
                    Pillar {i + 1}
                  </p>
                  <h3
                    className="mt-4 text-balance text-white leading-[1.08] -tracking-[0.04em] font-semibold"
                    style={{ fontSize: "clamp(1.35rem, 1.9vw, 2rem)" }}
                  >
                    {pillar.title}
                  </h3>
                  <p className="mt-4 text-balance text-white/56 leading-[1.6]">
                    {pillar.body}
                  </p>
                </div>
              </FadeIn>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
