import type { ReactNode } from "react";

export type SlideProps = {
  id?: string;
  label?: string;
  eyebrow?: string;
  title: string;
  description?: string;
  children?: ReactNode;
  className?: string;
  titleClassName?: string;
  descriptionClassName?: string;
};

export function Slide({
  id,
  label,
  eyebrow,
  title,
  description,
  children,
  className = "",
  titleClassName = "",
  descriptionClassName = "",
}: SlideProps) {
  return (
    <section
      id={id}
      data-story-section="true"
      data-story-label={label}
      className={`flex min-h-[100svh] snap-start items-center ${className}`}
    >
      <div className="grid w-full gap-6 rounded-[32px] border border-white/10 bg-[linear-gradient(180deg,rgba(20,25,34,0.92),rgba(14,17,23,0.94))] p-6 shadow-panel sm:p-8 lg:grid-cols-[minmax(0,1.08fr)_minmax(0,0.92fr)] lg:p-10">
        <div className="flex flex-col justify-between gap-6">
          <div className="space-y-5">
            {eyebrow ? (
              <div className="text-[11px] font-semibold uppercase tracking-[0.32em] text-slate-400">
                {eyebrow}
              </div>
            ) : null}
            <div className="space-y-4">
              <h2
                className={`max-w-xl font-display text-4xl font-semibold tracking-[-0.04em] text-white sm:text-5xl ${titleClassName}`}
              >
                {title}
              </h2>
              {description ? (
                <p
                  className={`max-w-2xl text-lg leading-8 text-slate-300 sm:text-[1.4rem] sm:leading-9 ${descriptionClassName}`}
                >
                  {description}
                </p>
              ) : null}
            </div>
            <div className="space-y-4">
              <p className="max-w-xl text-[11px] font-medium uppercase tracking-[0.22em] text-slate-400 sm:text-[12px]">
                Not memory. Not chat. A continuous intelligence layer.
              </p>
              <div className="text-[10px] font-semibold uppercase tracking-[0.32em] text-slate-500">
                Thesis
              </div>
              <div className="max-w-[11ch] text-[1.95rem] font-display font-semibold tracking-[-0.055em] text-white sm:text-[2.7rem] sm:leading-[1.02]">
                Most AI answers a prompt. Sakhi builds continuity.
              </div>
              <div className="max-w-2xl space-y-4">
                <p className="text-sm leading-7 text-slate-300 sm:text-[15px] sm:leading-7">
                  Today&apos;s AI resets every conversation.
                </p>
                <p className="text-base font-medium leading-8 text-white sm:text-[1.65rem] sm:leading-[1.12]">
                  Sakhi does not.
                </p>
                <p className="text-sm leading-7 text-slate-300 sm:text-[15px] sm:leading-7">
                  It connects decisions across time, learns from real outcomes,
                  and continuously updates its understanding of you.
                </p>
                <p className="text-sm leading-7 text-slate-300 sm:text-[15px] sm:leading-7">
                  This creates a closed loop:
                </p>
                <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#c7d4ff] sm:text-[12px]">
                  understanding -&gt; action -&gt; outcome -&gt; learning
                </p>
                <p className="text-sm leading-7 text-slate-200 sm:text-[15px] sm:leading-7">
                  The more it is used, the more grounded, personal, and useful
                  it becomes.
                </p>
              </div>
            </div>
          </div>

          <div className="h-px w-full bg-white/10" />
        </div>

        {children ? <div className="flex items-start lg:pt-3">{children}</div> : null}
      </div>
    </section>
  );
}

export default Slide;
