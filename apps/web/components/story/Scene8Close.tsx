"use client";

const foundersEmail = "sakhiadmin@gmail.com";

export default function Scene8Close() {
  return (
    <div className="relative flex h-full w-full flex-col items-center justify-center overflow-hidden px-6 pb-12 text-center sm:px-10 sm:pb-14 lg:px-16 lg:pb-16">
      {/* Ambient glow */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_60%_45%_at_50%_30%,rgba(140,183,255,0.07),transparent)]" />

      {/* Headline */}
      <div className="close-line relative">
        <h1 className="max-w-[13ch] text-balance text-[clamp(3.4rem,8vw,6.8rem)] font-bold leading-[0.92] tracking-[-0.07em] text-white">
          This is just the beginning.
        </h1>
      </div>

      <p className="close-line mt-6 max-w-xl text-balance text-[1.1rem] leading-[1.7] tracking-[-0.02em] text-white/50 sm:text-[1.2rem]">
        If this resonates, let&apos;s build this together.
      </p>

      {/* CTA cards */}
      <div className="close-line mt-14 flex w-full max-w-[680px] flex-col gap-4 sm:flex-row sm:gap-5">
        {/* Collaborate */}
        <div className="group relative flex flex-1 flex-col items-start overflow-hidden rounded-[28px] border border-white/[0.08] bg-[linear-gradient(160deg,rgba(255,255,255,0.04),rgba(255,255,255,0.015))] px-7 py-7 text-left shadow-[0_24px_60px_rgba(0,0,0,0.28)] backdrop-blur-sm transition-colors hover:border-white/14 hover:bg-white/[0.06]">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_0%_0%,rgba(140,183,255,0.07),transparent_55%)]" />
          <h3 className="relative z-10 mt-5 text-[1.5rem] font-semibold tracking-[-0.05em] text-white">
            Collaborate
          </h3>
          <p className="relative z-10 mt-2 text-[0.95rem] leading-[1.65] tracking-[-0.01em] text-white/48">
            If you believe we should shape our lives, not just react to them, come build this with us.
          </p>
        </div>

        {/* Invest */}
        <div className="group relative flex flex-1 flex-col items-start overflow-hidden rounded-[28px] border border-white/[0.08] bg-[linear-gradient(160deg,rgba(255,255,255,0.04),rgba(255,255,255,0.015))] px-7 py-7 text-left shadow-[0_24px_60px_rgba(0,0,0,0.28)] backdrop-blur-sm transition-colors hover:border-white/14 hover:bg-white/[0.06]">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_0%_0%,rgba(180,210,255,0.06),transparent_55%)]" />
          <h3 className="relative z-10 mt-5 text-[1.5rem] font-semibold tracking-[-0.05em] text-white">
            Invest
          </h3>
          <p className="relative z-10 mt-2 text-[0.95rem] leading-[1.65] tracking-[-0.01em] text-white/48">
            For investors who see this space the way we do, we share everything: vision, GTM, early product, and roadmap.
          </p>
        </div>
      </div>

      <div className="close-line mt-10 flex flex-col items-center">
        <p className="text-[0.72rem] font-semibold uppercase tracking-[0.28em] text-white/28">
          For Collaboration Or Investment
        </p>
        <a
          href={`mailto:${foundersEmail}?subject=${encodeURIComponent("Sakhi")}`}
          className="mt-3 inline-flex items-center gap-3 text-[1.08rem] font-semibold tracking-[-0.03em] text-white/78 transition-colors hover:text-white"
        >
          {foundersEmail}
          <span className="text-white/34 transition-transform hover:translate-x-0.5">↗</span>
        </a>
      </div>

      {/* Footer signature */}
      <p className="close-line mt-8 text-[0.78rem] font-semibold uppercase tracking-[0.28em] text-white/20">
        Sakhi · 2026
      </p>
    </div>
  );
}
