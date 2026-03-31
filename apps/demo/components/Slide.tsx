import type { ReactNode } from "react";

export type SlideProps = {
  eyebrow?: string;
  title: string;
  description?: string;
  children?: ReactNode;
  className?: string;
};

export function Slide({
  eyebrow,
  title,
  description,
  children,
  className = "",
}: SlideProps) {
  return (
    <section
      className={`grid gap-6 rounded-[32px] border border-white/10 bg-[linear-gradient(180deg,rgba(20,25,34,0.92),rgba(14,17,23,0.94))] p-6 shadow-panel sm:p-8 lg:grid-cols-[minmax(0,1.08fr)_minmax(0,0.92fr)] lg:p-10 ${className}`}
    >
      <div className="flex flex-col justify-between gap-6">
        <div className="space-y-5">
          {eyebrow ? (
            <div className="text-[11px] font-semibold uppercase tracking-[0.32em] text-slate-400">
              {eyebrow}
            </div>
          ) : null}
          <div className="space-y-4">
            <h2 className="max-w-xl font-display text-4xl font-semibold tracking-[-0.04em] text-white sm:text-5xl">
              {title}
            </h2>
            {description ? (
              <p className="max-w-2xl text-base leading-8 text-slate-300 sm:text-lg">
                {description}
              </p>
            ) : null}
          </div>
        </div>

        <div className="h-px w-full bg-white/10" />
      </div>

      {children ? <div className="lg:pt-1">{children}</div> : null}
    </section>
  );
}

export default Slide;
