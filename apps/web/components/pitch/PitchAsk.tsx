"use client";

import { FadeIn } from "@/components/pitch/FadeIn";

export function PitchAsk() {
  return (
    <section
      id="ask"
      className="flex min-h-[100svh] items-center border-t border-white/[0.06] bg-[#020617] px-8 py-32 scroll-mt-16 sm:px-16 lg:px-24"
    >
      <div className="mx-auto max-w-6xl w-full text-center">
        <FadeIn>
          <p className="text-[10px] sm:text-[11px] font-semibold uppercase tracking-[0.3em] text-[#8ab0ff]/80">
            The Ask
          </p>
        </FadeIn>

        <FadeIn delay={100}>
          <h2
            className="mt-5 font-semibold text-white max-w-[13ch] mx-auto leading-[1.08] -tracking-[0.06em]"
            style={{ fontSize: "clamp(3rem, 7vw, 6rem)" }}
          >
            This is just the beginning.
          </h2>
        </FadeIn>

        <FadeIn delay={200}>
          <p className="mt-6 text-xl text-white/50 max-w-xl mx-auto leading-relaxed">
            If this resonates, let&apos;s build this together. We share everything: vision, GTM, early product, and roadmap.
          </p>
        </FadeIn>

        <FadeIn delay={320}>
          <div className="mt-14 max-w-[720px] mx-auto flex flex-col sm:flex-row gap-5">
            <div className="rounded-[32px] border border-white/10 bg-white/[0.04] px-8 py-8 flex-1 text-left">
              <p className="text-sm font-semibold uppercase tracking-[0.2em] text-[#8ab0ff]/70">
                Collaborate
              </p>
              <p className="mt-4 text-base text-white/60 leading-relaxed">
                If you believe we should shape our lives, not just react to them, come build this with us.
              </p>
            </div>
            <div className="rounded-[32px] border border-white/10 bg-white/[0.04] px-8 py-8 flex-1 text-left">
              <p className="text-sm font-semibold uppercase tracking-[0.2em] text-[#8ab0ff]/70">
                Invest
              </p>
              <p className="mt-4 text-base text-white/60 leading-relaxed">
                For investors who see this space the way we do — we share everything: vision, GTM, early product, and roadmap.
              </p>
            </div>
          </div>
        </FadeIn>

        <FadeIn delay={440}>
          <div className="mt-12">
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-white/30 mb-3">
              For Collaboration Or Investment
            </p>
            <a
              href="mailto:founders@sakhiintelligence.com"
              className="inline-flex items-center gap-2 text-lg sm:text-xl font-medium text-white/80 hover:text-white transition-colors"
            >
              founders@sakhiintelligence.com
              <svg
                viewBox="0 0 20 20"
                fill="none"
                className="h-4 w-4 opacity-50"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M4.5 15.5l11-11m0 0H7.5m8 0v8"
                />
              </svg>
            </a>
          </div>
        </FadeIn>

        <FadeIn delay={560}>
          <p className="mt-8 text-xs text-white/20 tracking-widest uppercase">
            Sakhi · 2026
          </p>
        </FadeIn>
      </div>
    </section>
  );
}
