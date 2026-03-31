"use client";

import { FadeIn } from "@/components/pitch/FadeIn";

const columns = [
  {
    label: "WHO",
    title: "The person who holds it all",
    body: "Executives, founders, caregivers, and professionals navigating career, family, health, and responsibility simultaneously. Primarily urban India, 28–50.",
  },
  {
    label: "ENTRY",
    title: "Personal AI companion",
    body: "Mobile-first, voice-native. One conversation a day becomes a thread. A week of threads becomes a pattern. A month becomes clarity.",
  },
  {
    label: "EXPANSION",
    title: "Platform and network",
    body: "Enterprise continuity for teams. Sakhi Mesh for shared context across relationships. API layer for developers building on continuity.",
  },
];

const tiers = [
  {
    name: "Free",
    price: "30 conversations/month",
    tagline: "Try it, feel the difference",
  },
  {
    name: "Pro",
    price: "₹999/month",
    tagline: "Unlimited memory, voice, deep reflection",
    highlighted: true,
  },
  {
    name: "Enterprise",
    price: "Custom",
    tagline: "Teams, shared context, API access",
  },
];

export function PitchGTM() {
  return (
    <section
      id="gtm"
      className="min-h-[100svh] py-32 px-8 sm:px-16 lg:px-24 bg-[#020617]"
    >
      <div className="mx-auto max-w-6xl">
        <FadeIn>
          <p className="text-[10px] sm:text-[11px] font-semibold uppercase tracking-[0.3em] text-[#8ab0ff]/80">
            Go To Market
          </p>
        </FadeIn>

        <FadeIn delay={100}>
          <h2
            className="mt-5 font-semibold text-white max-w-[20ch] leading-[1.08] -tracking-[0.04em]"
            style={{ fontSize: "clamp(2.5rem, 5vw, 4.5rem)" }}
          >
            Built for people managing complex lives.
          </h2>
        </FadeIn>

        <FadeIn delay={200}>
          <p className="mt-6 text-xl text-white/60 max-w-2xl leading-relaxed">
            Urban professionals, founders, and knowledge workers who carry more threads than any tool can hold.
          </p>
        </FadeIn>

        <div className="mt-16 grid sm:grid-cols-3 gap-5">
          {columns.map((col, i) => (
            <FadeIn key={col.label} delay={300 + i * 100}>
              <div className="rounded-[28px] border border-white/10 bg-white/[0.03] px-7 py-8 h-full">
                <p className="text-[10px] font-semibold uppercase tracking-[0.3em] text-[#8ab0ff]/60">
                  {col.label}
                </p>
                <h3 className="mt-3 text-lg font-semibold text-white leading-snug">
                  {col.title}
                </h3>
                <p className="mt-3 text-sm text-white/50 leading-relaxed">
                  {col.body}
                </p>
              </div>
            </FadeIn>
          ))}
        </div>

        <FadeIn delay={600}>
          <div className="mt-16">
            <p className="text-[10px] sm:text-[11px] font-semibold uppercase tracking-[0.3em] text-white/30 mb-6">
              Revenue model
            </p>
            <div className="grid sm:grid-cols-3 gap-4">
              {tiers.map((tier) => (
                <div
                  key={tier.name}
                  className={`rounded-[24px] border px-7 py-7 ${
                    tier.highlighted
                      ? "border-[#8ab0ff]/30 bg-[#8ab0ff]/[0.06]"
                      : "border-white/[0.08] bg-white/[0.02]"
                  }`}
                >
                  <p className="text-sm font-semibold text-white/60">
                    {tier.name}
                  </p>
                  <p className="mt-2 text-xl font-semibold text-white -tracking-[0.02em]">
                    {tier.price}
                  </p>
                  <p className="mt-2 text-sm text-white/44 leading-snug">
                    {tier.tagline}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </FadeIn>

        <FadeIn delay={720}>
          <div className="mt-16 flex flex-col sm:flex-row sm:items-end gap-4">
            <span
              className="font-semibold text-white -tracking-[0.06em] leading-none"
              style={{ fontSize: "clamp(4rem, 10vw, 7rem)" }}
            >
              10,000
            </span>
            <div className="sm:pb-3">
              <p className="text-xl font-medium text-white/80">active users — Year 1 target.</p>
              <p className="mt-1 text-base text-white/44 max-w-lg leading-relaxed">
                100K is the Series A signal. 15% D30 retention at scale proves the loop.
              </p>
            </div>
          </div>
        </FadeIn>
      </div>
    </section>
  );
}
