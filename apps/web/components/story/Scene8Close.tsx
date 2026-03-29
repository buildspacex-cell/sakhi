"use client";

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
          <div className="relative z-10 flex h-9 w-9 items-center justify-center rounded-full border border-[#8cb7ff]/25 bg-[#8cb7ff]/10">
            <svg viewBox="0 0 16 16" className="h-4 w-4 fill-none stroke-[#8cb7ff] stroke-[1.5]" strokeLinecap="round" strokeLinejoin="round">
              <path d="M2 8h12M9 3l5 5-5 5" />
            </svg>
          </div>
          <h3 className="relative z-10 mt-5 text-[1.5rem] font-semibold tracking-[-0.05em] text-white">
            Collaborate
          </h3>
          <p className="relative z-10 mt-2 text-[0.95rem] leading-[1.65] tracking-[-0.01em] text-white/48">
            Help shape what this becomes.
          </p>
          <button className="relative z-10 mt-8 inline-flex items-center gap-2 text-[0.92rem] font-semibold tracking-[-0.01em] text-[#8cb7ff]/80 transition-colors hover:text-[#8cb7ff]">
            Work with us
            <span className="text-[#8cb7ff]/50 transition-transform group-hover:translate-x-0.5">↗</span>
          </button>
        </div>

        {/* Invest */}
        <div className="group relative flex flex-1 flex-col items-start overflow-hidden rounded-[28px] border border-white/[0.08] bg-[linear-gradient(160deg,rgba(255,255,255,0.04),rgba(255,255,255,0.015))] px-7 py-7 text-left shadow-[0_24px_60px_rgba(0,0,0,0.28)] backdrop-blur-sm transition-colors hover:border-white/14 hover:bg-white/[0.06]">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_0%_0%,rgba(180,210,255,0.06),transparent_55%)]" />
          <div className="relative z-10 flex h-9 w-9 items-center justify-center rounded-full border border-white/18 bg-white/[0.07]">
            <svg viewBox="0 0 16 16" className="h-4 w-4 fill-none stroke-white/70 stroke-[1.5]" strokeLinecap="round" strokeLinejoin="round">
              <path d="M8 2v12M3 7l5-5 5 5" />
            </svg>
          </div>
          <h3 className="relative z-10 mt-5 text-[1.5rem] font-semibold tracking-[-0.05em] text-white">
            Invest
          </h3>
          <p className="relative z-10 mt-2 text-[0.95rem] leading-[1.65] tracking-[-0.01em] text-white/48">
            Back the system we&apos;re building.
          </p>
          <button className="relative z-10 mt-8 inline-flex items-center gap-2 text-[0.92rem] font-semibold tracking-[-0.01em] text-white/60 transition-colors hover:text-white/90">
            Talk to us
            <span className="text-white/32 transition-transform group-hover:translate-x-0.5">↗</span>
          </button>
        </div>
      </div>

      {/* Footer signature */}
      <p className="close-line mt-10 text-[0.78rem] font-semibold uppercase tracking-[0.28em] text-white/20">
        Sakhi · 2026
      </p>
    </div>
  );
}
