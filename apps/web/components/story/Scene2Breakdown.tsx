"use client";

export default function Scene2Breakdown() {
  return (
    <div className="flex h-full flex-col items-center justify-center px-8 text-center sm:px-12">
      {/* Dark radial gradient to ensure text legibility over bleeding scene-1 thoughts */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_85%_75%_at_50%_50%,rgba(2,6,23,0.82),transparent_82%)]" />
      <div className="relative max-w-4xl">
        <div className="mx-auto max-w-2xl space-y-3 text-lg leading-8 tracking-[-0.03em] text-slate-300 drop-shadow-[0_0_18px_rgba(2,6,23,1)] sm:text-xl">
          <p className="bridge-1">You wind down for the day.</p>
          <p className="bridge-2">The signal fades with it.</p>
          <p className="bridge-3 text-slate-100">By morning, the thread is gone.</p>
        </div>

        <div className="mt-12 space-y-5">
          <div className="break-1 rounded-full bg-white/6 px-8 py-5 text-3xl font-medium leading-none tracking-[-0.04em] text-white backdrop-blur-md sm:text-4xl">
            Thoughts reset
          </div>
          <div className="break-2 rounded-full bg-white/6 px-8 py-5 text-3xl font-medium leading-none tracking-[-0.04em] text-white backdrop-blur-md sm:text-4xl">
            Good ideas die
          </div>
          <div className="break-3 rounded-full bg-white/6 px-8 py-5 text-3xl font-medium leading-none tracking-[-0.04em] text-white backdrop-blur-md sm:text-4xl">
            Continuity is lost
          </div>
        </div>
      </div>
    </div>
  );
}
