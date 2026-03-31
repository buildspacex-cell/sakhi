export type LoopStep = {
  title: string;
  detail: string;
};

export type LoopDiagramProps = {
  title: string;
  description?: string;
  steps: ReadonlyArray<LoopStep>;
  className?: string;
};

export function LoopDiagram({
  title,
  description,
  steps,
  className = "",
}: LoopDiagramProps) {
  return (
    <section
      className={`rounded-[28px] border border-white/10 bg-[#121720]/80 p-6 shadow-panel ${className}`}
    >
      <div className="max-w-2xl">
        <div className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-400">
          Operating loop
        </div>
        <h3 className="mt-3 font-display text-2xl font-semibold tracking-[-0.03em] text-white">
          {title}
        </h3>
        {description ? (
          <p className="mt-3 text-sm leading-7 text-slate-300">{description}</p>
        ) : null}
      </div>

      <div className="mt-6 flex flex-col gap-3 xl:flex-row xl:flex-wrap xl:items-stretch">
        {steps.map((step, index) => (
          <div key={step.title} className="flex min-w-[180px] flex-1 items-stretch">
            <div className="flex flex-1 flex-col rounded-2xl border border-white/10 bg-[#0f131a] px-4 py-4">
              <div className="text-[11px] font-semibold uppercase tracking-[0.26em] text-slate-500">
                {String(index + 1).padStart(2, "0")}
              </div>
              <div className="mt-2 text-sm font-medium text-white">
                {step.title}
              </div>
              <div className="mt-2 text-sm leading-6 text-slate-300">
                {step.detail}
              </div>
            </div>

            {index < steps.length - 1 ? (
              <div className="flex items-center justify-center px-2 text-lg font-medium text-slate-500 xl:px-3">
                -&gt;
              </div>
            ) : null}
          </div>
        ))}
      </div>
    </section>
  );
}

export default LoopDiagram;
