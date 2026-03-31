"use client";

export default function Scene6Transition() {
  return (
    <div className="relative flex h-full w-full items-center justify-center overflow-hidden px-6 text-center sm:px-10 lg:px-16 xl:px-24">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_24%,rgba(162,179,255,0.12),transparent_24%),radial-gradient(circle_at_16%_78%,rgba(108,128,255,0.07),transparent_28%),radial-gradient(circle_at_84%_78%,rgba(112,205,255,0.06),transparent_28%)]" />

      <div className="relative mx-auto max-w-5xl">
        <p className="builders-bridge-kicker text-[11px] font-semibold uppercase tracking-[0.34em] text-[#c8d4ff]/72">
          Founders
        </p>
        <h2 className="builders-bridge-line mt-6 text-balance text-[clamp(3rem,7vw,6rem)] font-semibold leading-[0.96] tracking-[-0.06em] text-white">
          The Minds Behind...
        </h2>
      </div>
    </div>
  );
}
