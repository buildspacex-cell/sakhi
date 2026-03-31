"use client";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[#0f1115] text-slate-50 antialiased">
        <main className="flex min-h-screen items-center justify-center px-6">
          <div className="max-w-lg rounded-[28px] border border-white/10 bg-[#121720]/90 p-8 text-center shadow-panel">
            <p className="text-xs font-semibold uppercase tracking-[0.32em] text-slate-400">
              Sakhi Demo
            </p>
            <h1 className="mt-4 text-3xl font-semibold tracking-[-0.03em] text-white">
              Something went wrong
            </h1>
            <p className="mt-4 text-sm leading-7 text-slate-300">
              {error.message || "A global error occurred."}
            </p>
            <button
              type="button"
              onClick={reset}
              className="mt-6 rounded-full border border-white/10 bg-white/10 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-white/15"
            >
              Try again
            </button>
          </div>
        </main>
      </body>
    </html>
  );
}
