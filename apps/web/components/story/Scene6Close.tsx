"use client";

import Image from "next/image";

export default function Scene6Founder() {
  const arcSteps = [
    {
      label: "Operator at Scale",
      titleLines: ["Operator", "at", "Scale"],
      body:
        "Worked alongside CEOs and COOs, building systems that turned ambiguity into structured decisions.",
    },
    {
      label: "Personal Inflection Point",
      titleLines: ["Personal", "Inflection", "Point"],
      body:
        "In 2024, caregiving, leadership, and life complexity collided. What was missing was continuity at the level of a real human life.",
    },
    {
      label: "Insight to Sakhi",
      titleLines: ["Insight", "to", "Sakhi"],
      body:
        "Small, personalized interventions changed everything. Timing and personalization mattered more than generic advice. The question became: can this be built as a system?",
    },
  ];

  return (
    <div className="relative flex h-full w-full items-center overflow-hidden px-6 pb-[calc(env(safe-area-inset-bottom)+4.75rem)] pt-[calc(env(safe-area-inset-top)+5.75rem)] sm:px-10 sm:pb-[calc(env(safe-area-inset-bottom)+4.75rem)] sm:pt-[calc(env(safe-area-inset-top)+5rem)] lg:px-16 lg:pb-24 lg:pt-24 xl:px-24">
      <div className="mx-auto grid w-full max-w-[92rem] items-center gap-8 lg:grid-cols-[minmax(14.5rem,0.6fr)_minmax(0,1.4fr)] lg:items-center lg:gap-10 xl:gap-14">

        {/* Portrait — persistent, stays through both content phases */}
        <div className="founder-portrait-wrap relative mx-auto w-[15.5rem] lg:mx-0 lg:w-[16.5rem]">
          <div className="absolute inset-0 rounded-[34px] bg-[radial-gradient(circle_at_50%_18%,rgba(150,174,255,0.16),transparent_38%)] blur-2xl" />
          <div className="founder-portrait relative rounded-[34px] border border-white/10 bg-white/[0.03] p-3 shadow-[0_36px_90px_rgba(0,0,0,0.42)] backdrop-blur-md">
            <div className="relative aspect-[3/4] overflow-hidden rounded-[26px]">
              <Image
                src="/story/v-pic-20260327.png"
                alt="Vidhya portrait"
                fill
                sizes="(max-width: 1024px) 18rem, 19rem"
                className="object-cover object-center"
                priority={false}
              />
            </div>
            <div className="founder-meta mt-3 rounded-[20px] border border-white/10 bg-[linear-gradient(180deg,rgba(7,11,18,0.66),rgba(4,7,14,0.84))] px-4 py-3 text-left backdrop-blur-md">
              <div className="text-sm font-semibold tracking-[0.02em] text-white">
                Vidhya
              </div>
              <div className="mt-1 text-[11px] font-medium uppercase tracking-[0.18em] text-[#c4d2ff]/72">
                Co-Founder &amp; CEO
              </div>
              <div className="mt-2 text-[13px] leading-5 text-white/62">
                Built systems for companies. Now building one for humans.
              </div>
            </div>
          </div>
        </div>

        {/* Right column — two content panels share this space */}
        <div className="relative text-center lg:text-left">

          {/* Phase 1: Opening quote — absolute overlay, fades out on transition */}
          <div className="pointer-events-none absolute inset-0 flex items-center">
            <h2 className="founder-opening mx-auto max-w-[15ch] text-balance text-[2.6rem] font-semibold leading-[0.96] tracking-[-0.06em] text-white sm:max-w-[16ch] sm:text-[3.3rem] lg:mx-0 lg:max-w-[15ch] lg:text-left lg:text-[4.1rem] xl:text-[5rem]">
              I&apos;ve spent 20+ years helping organizations make better
              decisions. I realized we haven&apos;t solved this for individuals.
            </h2>
          </div>

          {/* Phase 2: Detail arc content — fades in after quote fades out */}
          <div>
            <div className="founder-detail-kicker text-[11px] font-semibold uppercase tracking-[0.34em] text-[#c4d2ff]">
              Building From Lived Experience
            </div>

            <div className="founder-arc-shell relative mt-5 overflow-hidden rounded-[34px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.05),rgba(255,255,255,0.018))] px-5 py-6 shadow-[0_30px_90px_rgba(0,0,0,0.26)] backdrop-blur-xl sm:px-6 sm:py-7 lg:min-h-[29rem] lg:px-8 lg:py-9">
              <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(190,208,255,0.14),transparent_34%),radial-gradient(circle_at_82%_32%,rgba(135,156,255,0.1),transparent_28%)]" />
              <div className="founder-arc-mobile-line absolute bottom-8 left-[1.2rem] top-14 w-px origin-top bg-[linear-gradient(180deg,rgba(196,210,255,0.12),rgba(196,210,255,0.78),rgba(196,210,255,0.18))] lg:hidden" />
              <div className="founder-arc-glow pointer-events-none absolute left-10 right-10 top-[5.2rem] hidden h-[10px] rounded-full bg-[linear-gradient(90deg,rgba(196,210,255,0.06),rgba(196,210,255,0.28),rgba(196,210,255,0.08))] blur-md lg:block" />

              <div className="relative flex flex-col gap-6 lg:flex lg:min-h-[23rem] lg:flex-col lg:justify-center">
                <div className="hidden lg:grid lg:grid-cols-[minmax(0,1fr)_minmax(2.8rem,0.3fr)_minmax(0,1.24fr)_minmax(2.8rem,0.3fr)_minmax(0,1fr)] lg:items-center lg:gap-4">
                  {arcSteps.map((step, index) => (
                    <div key={step.label} className="contents">
                      <div
                        className={`founder-arc-head founder-arc-head-${index + 1} flex items-start justify-center gap-4 opacity-0`}
                      >
                        <div className="founder-arc-stop mt-1 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-[#d7e2ff]/60 bg-[#c9d6ff]/18 shadow-[0_0_24px_rgba(196,210,255,0.3)]">
                          <div className="h-1.5 w-1.5 rounded-full bg-[#eef3ff]" />
                        </div>
                        <div
                          className={`founder-arc-title founder-arc-title-${index + 1} flex flex-col gap-1 text-left text-[1.24rem] font-semibold leading-[0.9] tracking-[-0.05em] text-white xl:text-[1.42rem]`}
                        >
                          {step.titleLines.map((line) => (
                            <span key={line} className="block">
                              {line}
                            </span>
                          ))}
                        </div>
                      </div>
                      {index < arcSteps.length - 1 ? (
                        <div
                          className={`founder-arc-link founder-arc-link-${index + 1} h-px origin-left scale-x-0 border-t border-dashed border-[#c4d2ff]/58 opacity-0`}
                        />
                      ) : null}
                    </div>
                  ))}
                </div>

                <div className="relative flex flex-col gap-6 lg:hidden">
                  {arcSteps.map((step, index) => (
                    <article
                      key={step.label}
                      className={`founder-arc-step founder-arc-step-${index + 1} relative pl-8 text-left`}
                    >
                      <div
                        className={`founder-arc-head founder-arc-head-${index + 1} flex items-start gap-4 opacity-0`}
                      >
                        <div className="founder-arc-stop absolute left-0 top-2 flex h-4 w-4 items-center justify-center rounded-full border border-[#d7e2ff]/60 bg-[#c9d6ff]/18 shadow-[0_0_24px_rgba(196,210,255,0.3)]">
                          <div className="h-1.5 w-1.5 rounded-full bg-[#eef3ff]" />
                        </div>
                        <div
                          className={`founder-arc-title founder-arc-title-${index + 1} flex flex-col gap-1 text-[1.3rem] font-semibold leading-[0.92] tracking-[-0.05em] text-white sm:text-[1.55rem]`}
                        >
                          {step.titleLines.map((line) => (
                            <span key={line} className="block">
                              {line}
                            </span>
                          ))}
                        </div>
                      </div>
                      <p
                        className={`founder-arc-body founder-arc-body-${index + 1} mt-3 max-w-none text-sm leading-6 text-white/72 opacity-0 sm:text-[0.98rem]`}
                      >
                        {step.body}
                      </p>
                    </article>
                  ))}
                </div>

                <div className="hidden lg:grid lg:grid-cols-3 lg:gap-10 lg:pt-14">
                  {arcSteps.map((step, index) => (
                    <article
                      key={step.label}
                      className={`founder-arc-step founder-arc-step-${index + 1} text-left`}
                    >
                      <p
                        className={`founder-arc-body founder-arc-body-${index + 1} max-w-none text-[1rem] leading-7 text-white/72 opacity-0 xl:text-[1.04rem]`}
                      >
                        {step.body}
                      </p>
                    </article>
                  ))}
                </div>
              </div>
            </div>

            <p className="founder-final mt-6 max-w-3xl text-balance text-[1.05rem] font-medium leading-7 tracking-[-0.03em] text-white sm:text-[1.2rem]">
              Sakhi is the system I wish existed when I needed it most.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
