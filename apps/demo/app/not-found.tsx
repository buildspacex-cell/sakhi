export default function NotFound() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[#0f1115] px-6 text-slate-50">
      <div className="max-w-md text-center">
        <p className="text-xs font-semibold uppercase tracking-[0.32em] text-slate-400">
          Sakhi Demo
        </p>
        <h1 className="mt-4 text-3xl font-semibold tracking-[-0.03em] text-white">
          Page not found
        </h1>
        <p className="mt-4 text-sm leading-7 text-slate-300">
          The demo route you asked for does not exist.
        </p>
      </div>
    </main>
  );
}
