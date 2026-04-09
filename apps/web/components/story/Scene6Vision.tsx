"use client";

export default function Scene6Vision() {
  return (
    <div className="relative flex h-full w-full items-center justify-center overflow-hidden">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_70%_60%_at_50%_46%,rgba(30,50,100,0.5),rgba(3,11,24,0.0)_68%)]" />

      <div className="relative flex flex-col items-center text-center">
        {/* Orb */}
        <div className="vision-orb-wrap relative flex items-center justify-center" style={{ opacity: 0 }}>
          <div className="vision-orb-ring absolute h-[min(420px,72vw)] w-[min(420px,72vw)] rounded-full border border-white/[0.04]" />
          <div className="vision-orb-ring absolute h-[min(320px,55vw)] w-[min(320px,55vw)] rounded-full border border-white/[0.07]" />
          <div className="vision-orb-ring absolute h-[min(236px,40vw)] w-[min(236px,40vw)] rounded-full border border-white/[0.10]" />
          <div className="relative flex h-[min(168px,28vw)] w-[min(168px,28vw)] items-center justify-center rounded-full border border-[#8ab0ff]/25 bg-[radial-gradient(circle_at_38%_32%,rgba(140,183,255,0.22),rgba(80,120,210,0.14)_48%,rgba(3,11,24,0.85)_78%)] shadow-[0_0_80px_rgba(100,148,255,0.18),0_0_160px_rgba(80,120,255,0.08)]">
            <div className="pointer-events-none absolute inset-[14%] rounded-full border border-white/[0.09]" />
            <span className="relative z-10 text-[clamp(8px,1.2vw,12px)] font-semibold tracking-[0.42em] text-[#8ab0ff]/90">SAKHI</span>
          </div>
        </div>

        {/* Signoff */}
        <div className="vision-signoff mt-12 max-w-3xl px-6" style={{ opacity: 0 }}>
          <p className="vision-signoff-label text-balance text-[clamp(1.1rem,1.9vw,1.9rem)] font-semibold leading-[1.28] tracking-[-0.04em] text-white/86">
            The physical world has infrastructure.<br />
            <span className="text-[#c8d4ff]">The mind has none. Sakhi is built to become it.</span>
          </p>
        </div>
      </div>
    </div>
  );
}
