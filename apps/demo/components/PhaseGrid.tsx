export type PhaseItem = {
  title: string;
  detail: string;
  note?: string;
};

export type PhaseGridProps = {
  title: string;
  description?: string;
  phases: ReadonlyArray<PhaseItem>;
  className?: string;
};

export function PhaseGrid({
  title,
  description,
  phases,
  className = "",
}: PhaseGridProps) {
  return (
    <section className={`space-y-6 ${className}`}>
      <div className="max-w-2xl">
        <div className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-400">
          Phases
        </div>
        <h3 className="mt-3 font-display text-2xl font-semibold tracking-[-0.03em] text-white">
          {title}
        </h3>
        {description ? (
          <p className="mt-3 text-sm leading-7 text-slate-300">{description}</p>
        ) : null}
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {phases.map((phase, index) => (
          <article
            key={phase.title}
            className="rounded-[24px] border border-white/10 bg-[linear-gradient(180deg,rgba(18,23,32,0.92),rgba(14,17,23,0.94))] p-5 shadow-panel"
          >
            <div className="flex items-center justify-between gap-3">
              <div className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-500">
                Phase {index + 1}
              </div>
              {phase.note ? (
                <div className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[11px] uppercase tracking-[0.22em] text-slate-300">
                  {phase.note}
                </div>
              ) : null}
            </div>
            <h4 className="mt-4 font-display text-lg font-semibold tracking-[-0.02em] text-white">
              {phase.title}
            </h4>
            <p className="mt-3 text-sm leading-7 text-slate-300">
              {phase.detail}
            </p>
          </article>
        ))}
      </div>
    </section>
  );
}

export default PhaseGrid;
