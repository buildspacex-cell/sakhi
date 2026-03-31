"use client";

import { FadeIn } from "@/components/pitch/FadeIn";

const painPoints = [
  {
    icon: "○",
    iconColor: "text-white/30",
    title: "Thoughts reset",
    body: "Every day starts from scratch. Yesterday's context is gone before it can shape what comes next.",
  },
  {
    icon: "✦",
    iconColor: "text-amber-400",
    title: "Good ideas die",
    body: "Insights arrive in flashes. Without continuity, they disappear before they become direction.",
  },
  {
    icon: "◈",
    iconColor: "text-rose-400",
    title: "Life gets fragmented",
    body: "Life is a long thread. But the tools we use treat every day as a separate conversation.",
  },
];

export function PitchProblem() {
  return (
    <section
      id="problem"
      className="relative border-t border-white/[0.06] bg-[#020617] px-8 scroll-mt-16 sm:px-16 lg:px-24"
    >
      <div className="mx-auto max-w-6xl">
        <div className="flex min-h-[100svh] flex-col justify-center py-28 sm:py-32">
          <FadeIn>
            <p className="text-[10px] sm:text-[11px] font-semibold uppercase tracking-[0.3em] text-[#8ab0ff]/80">
              The Problem
            </p>
          </FadeIn>

          <FadeIn delay={100}>
            <h2
              className="mt-5 max-w-[14ch] font-semibold leading-[1.08] -tracking-[0.04em] text-white"
              style={{ fontSize: "clamp(3rem, 6vw, 5.5rem)" }}
            >
              There&apos;s a conversation happening in your head.
            </h2>
          </FadeIn>

          <FadeIn delay={200}>
            <p className="mt-6 max-w-2xl text-xl leading-relaxed text-white/60">
              It never really stops. And it doesn&apos;t carry forward. Nothing actually holds it together.
            </p>
          </FadeIn>
        </div>

        <div className="border-t border-white/[0.06] pb-28 pt-10 sm:pb-32 sm:pt-14">
          <div className="grid gap-4 sm:grid-cols-3">
            {painPoints.map((point, i) => (
              <FadeIn key={point.title} delay={180 + i * 100}>
                <div className="h-full rounded-[28px] border border-white/[0.08] bg-white/[0.03] px-7 py-8">
                  <span className={`text-2xl ${point.iconColor}`}>
                    {point.icon}
                  </span>
                  <h3 className="mt-4 text-lg font-semibold text-white leading-snug">
                    {point.title}
                  </h3>
                  <p className="mt-3 text-sm leading-relaxed text-white/50">
                    {point.body}
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
