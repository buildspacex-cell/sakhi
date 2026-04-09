"use client";

const pillars = [
  "Keeps the thread, not just the prompt.",
  "Makes your life visible across time.",
  "Helps your thinking compound.",
] as const;

export default function Scene3Reveal() {
  return (
    <div className="relative h-full overflow-hidden px-8 py-10 sm:px-12 lg:px-16 xl:px-24">
      <div className="sakhi-stage absolute inset-0 flex items-center justify-center px-8 py-10 sm:px-12 lg:px-16 xl:px-24">
        <div className="w-full max-w-6xl text-center">
          <div className="sakhi-headline mx-auto max-w-[11ch] text-balance text-5xl font-semibold leading-[0.98] tracking-[-0.06em] text-white drop-shadow-[0_0_20px_rgba(255,255,255,0.08)] sm:text-6xl lg:text-8xl">
            Sakhi keeps it all connected.
          </div>
        </div>
      </div>

      <div className="sakhi-bridge absolute inset-0 flex items-center justify-center px-8 py-10 opacity-0 sm:px-12 lg:px-16 xl:px-24">
        <div className="mx-auto max-w-4xl text-center">
          <p className="sakhi-bridge-line sakhi-bridge-line-1 text-balance text-[1.35rem] leading-[1.38] tracking-[-0.03em] text-[#d5ddf4] sm:text-[1.65rem]">
            You do not have to be driven by your thoughts.
          </p>
          <p className="sakhi-bridge-line sakhi-bridge-line-2 mt-5 text-balance text-[1.18rem] leading-[1.5] tracking-[-0.025em] text-slate-300 sm:text-[1.35rem]">
            You can shape them.
          </p>
        </div>
      </div>

      <div className="intro-sequence absolute inset-0 flex items-center justify-center px-8 py-10 opacity-0 sm:px-12 lg:px-16 xl:px-24">
        <div className="mx-auto flex w-full max-w-6xl flex-col items-center text-center">
          <div className="w-full max-w-5xl">
            <div className="text-[clamp(4.2rem,10vw,8rem)] font-semibold leading-[0.92] tracking-[-0.075em] text-white">
              <div className="intro-line-1 text-white/84">Stop reacting.</div>
              <div className="intro-line-2 mt-1 text-white/14">Start shaping.</div>
            </div>
          </div>

          <div className="intro-explainer mt-14 w-full max-w-3xl">
            <p className="mx-auto max-w-2xl text-[clamp(1.2rem,2.1vw,1.7rem)] leading-[1.5] tracking-[-0.03em] text-slate-300">
              Sakhi keeps the thread, so your thinking becomes clearer over time.
            </p>
          </div>

          <div className="intro-system mt-8 w-full">
            <div className="mx-auto max-w-4xl">
              <div className="relative min-h-[7rem] overflow-hidden sm:min-h-[8rem] lg:min-h-[9rem]">
                {pillars.map((pillar, index) => (
                  <div
                    key={pillar}
                    className={`intro-active intro-active-${index + 1} absolute inset-0 flex items-center justify-center opacity-0`}
                  >
                    <p className="mx-auto max-w-[16ch] text-center text-[clamp(2.1rem,4vw,3.7rem)] font-medium leading-[1.06] tracking-[-0.055em] text-white">
                      {pillar}
                    </p>
                  </div>
                ))}

                <div className="intro-resolved absolute inset-0 flex items-center justify-center opacity-0">
                  <div className="grid w-full max-w-5xl grid-cols-1 gap-6 md:grid-cols-[1fr_1.15fr_1fr] md:items-center">
                    {pillars.map((pillar, index) => (
                      <div
                        key={`${pillar}-resolved`}
                        className={
                          index === 0
                            ? "text-left"
                            : index === 1
                              ? "text-center"
                              : "text-right"
                        }
                      >
                        <div className={`intro-resolved-item intro-resolved-item-${index + 1}`}>
                          <p className="text-balancetext-[clamp(1.15rem,1.55vw,1.65rem)] leading-[1.2] tracking-[-0.03em] text-slate-100/88">
                            {pillar}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div className="intro-progress-wrap mt-4 flex items-center justify-center gap-3">
                {pillars.map((pillar, index) => (
                  <div
                    key={`${pillar}-progress`}
                    className="h-[2px] w-14 overflow-hidden rounded-full bg-white/10"
                  >
                    <div
                      className={`intro-progress intro-progress-${index + 1} h-full origin-left rounded-full bg-[#c7d3ff] scale-x-[0.3]`}
                    />
                  </div>
                ))}
              </div>

              <div className="intro-parked-row mt-3 grid grid-cols-1 gap-4 md:grid-cols-[1fr_1.15fr_1fr] md:items-start">
                {pillars.map((pillar, index) => (
                  <div
                    key={`${pillar}-parked`}
                    className={
                      index === 0
                        ? "text-left"
                        : index === 1
                          ? "text-center"
                          : "text-right"
                    }
                  >
                    <div className={`intro-parked intro-parked-${index + 1} opacity-0`}>
                      <p className="text-balancetext-[clamp(0.95rem,1.15vw,1.2rem)] leading-[1.25] tracking-[-0.025em] text-slate-200/72">
                        {pillar}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
