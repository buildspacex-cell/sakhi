export default function HomePage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[#0f1115] px-6 text-slate-50">
      <div className="w-full max-w-2xl rounded-[32px] border border-white/10 bg-[linear-gradient(180deg,rgba(20,25,34,0.92),rgba(14,17,23,0.94))] p-8 shadow-[0_24px_80px_rgba(0,0,0,0.32)]">
        <div className="text-[11px] font-semibold uppercase tracking-[0.32em] text-slate-400">
          Demo workspace parked
        </div>
        <h1 className="mt-5 font-serif text-4xl font-semibold tracking-[-0.04em] text-white">
          MVP presentation now lives in the web app only.
        </h1>
        <p className="mt-5 max-w-xl text-base leading-8 text-slate-300">
          Use the web app for both the cinematic investor story and the
          password-protected MVP roadmap surface. The standalone demo app is
          parked again to avoid drift between parallel presentation shells.
        </p>
        <div className="mt-8 rounded-2xl border border-white/10 bg-white/[0.04] px-5 py-4">
          <div className="text-[11px] font-semibold uppercase tracking-[0.26em] text-slate-500">
            Active surfaces
          </div>
          <div className="mt-2 text-lg font-medium text-white">`apps/web/app/story/page.tsx` and `apps/web/app/mvp/page.tsx`</div>
        </div>
      </div>
    </main>
  );
}
