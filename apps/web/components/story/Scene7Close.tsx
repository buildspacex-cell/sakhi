"use client";

import Image from "next/image";

export default function Scene7Founder() {
  const arcSteps = [
    {
      label: "Evolution",
      body:
        "I started with engineering, building systems and applications, then kept moving closer to the question of what actually makes systems work.",
    },
    {
      label: "Realization",
      body:
        "Systems do not succeed just because they are built well. They succeed because people understand them, trust them, and use them.",
    },
    {
      label: "Expansion",
      body:
        "That pulled me across engineering, product, and product marketing, while yoga and meditation deepened how I think about human behavior over time.",
    },
    {
      label: "Convergence",
      body:
        "Technical depth, systems thinking, product narrative, and lived understanding of people now converge in building Sakhi.",
    },
  ];

  return (
    <div className="relative flex h-full w-full items-center overflow-hidden px-6 pb-[calc(env(safe-area-inset-bottom)+4.75rem)] pt-[calc(env(safe-area-inset-top)+5.75rem)] sm:px-10 sm:pb-[calc(env(safe-area-inset-bottom)+4.75rem)] sm:pt-[calc(env(safe-area-inset-top)+5rem)] lg:px-16 lg:pb-24 lg:pt-24 xl:px-24">
      <div className="mx-auto grid w-full max-w-[92rem] items-center gap-8 lg:grid-cols-[minmax(14.5rem,0.6fr)_minmax(0,1.4fr)] lg:items-center lg:gap-10 xl:gap-14">

        {/* Portrait — persistent, stays through both content phases */}
        <div className="ravi-visual-wrap relative mx-auto w-[15.5rem] lg:mx-0 lg:w-[16.5rem]">
          <div className="absolute inset-0 rounded-[34px] bg-[radial-gradient(circle_at_50%_18%,rgba(138,210,255,0.16),transparent_40%)] blur-2xl" />
          <div className="ravi-visual relative rounded-[34px] border border-[#9cd7ff]/12 bg-[linear-gradient(180deg,rgba(10,16,29,0.92),rgba(5,9,18,0.96))] p-3 shadow-[0_36px_90px_rgba(0,0,0,0.42)] backdrop-blur-md">
            <div className="relative aspect-[3/4] overflow-hidden rounded-[26px]">
              <Image
                src="/story/r-pic.png"
                alt="Ravi portrait"
                fill
                sizes="(max-width: 1024px) 18rem, 19rem"
                className="object-cover object-[50%_24%]"
                priority={false}
              />
            </div>
            <div className="ravi-meta mt-3 rounded-[20px] border border-[#9cd7ff]/10 bg-[linear-gradient(180deg,rgba(7,11,18,0.68),rgba(4,7,14,0.86))] px-4 py-3 text-left backdrop-blur-md">
              <div className="text-sm font-semibold tracking-[0.02em] text-white">
                Ravi Shankar
              </div>
              <div className="mt-1 text-[13px] leading-5 text-white/62">
                Built systems across engineering, product, and AI. Now
                building one for the self.
              </div>
            </div>
          </div>
        </div>

        {/* Right column — two content panels share this space */}
        <div className="relative text-center lg:text-left">

          {/* Phase 1: Opening quote — absolute overlay, fades out on transition */}
          <div className="pointer-events-none absolute inset-0 flex items-center">
            <h2 className="ravi-opening mx-auto max-w-[16ch] text-balance text-[2.55rem] font-semibold leading-[0.96] tracking-[-0.06em] text-white sm:max-w-[17ch] sm:text-[3.15rem] lg:mx-0 lg:max-w-[14ch] lg:text-left lg:text-[3.95rem] xl:text-[4.85rem]">
              <span className="block">
                I&apos;m a systems thinker at heart, grounded in deep technical
                expertise and driven to simplify complexity.
              </span>
            </h2>
          </div>

          {/* Phase 2: Detail arc content — fades in after quote fades out */}
          <div>
            <div className="ravi-detail-kicker text-[11px] font-semibold uppercase tracking-[0.34em] text-[#bfe3ff]">
              Building From Lived Experience
            </div>

            <div className="ravi-arc-shell relative mt-5 px-1 py-3 sm:px-2 sm:py-4 lg:min-h-[29rem] lg:py-5">
              <div className="ravi-arc-mobile-line absolute bottom-8 left-[1.2rem] top-14 w-px origin-top bg-[linear-gradient(180deg,rgba(191,227,255,0.14),rgba(191,227,255,0.8),rgba(191,227,255,0.18))] lg:hidden" />
              <div className="ravi-arc-glow pointer-events-none absolute left-6 right-6 top-[3.5rem] hidden h-[10px] rounded-full bg-[linear-gradient(90deg,rgba(191,227,255,0.04),rgba(191,227,255,0.2),rgba(191,227,255,0.06))] blur-md lg:block" />

              <div className="relative flex flex-col gap-6 lg:flex lg:min-h-[23rem] lg:flex-col lg:justify-center">
                <div className="hidden lg:grid lg:grid-cols-[minmax(0,1fr)_minmax(2rem,0.24fr)_minmax(0,1fr)_minmax(2rem,0.24fr)_minmax(0,1fr)_minmax(2rem,0.24fr)_minmax(0,1fr)] lg:items-center lg:gap-4">
                  {arcSteps.map((step, index) => (
                    <div key={step.label} className="contents">
                      <div
                        className={`ravi-arc-head ravi-arc-head-${index + 1} flex items-center justify-center gap-4 opacity-0`}
                      >
                        <div className="ravi-arc-stop flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-[#bfe3ff]/60 bg-[#bfe3ff]/16 shadow-[0_0_22px_rgba(138,210,255,0.24)]">
                          <div className="h-1.5 w-1.5 rounded-full bg-[#eef8ff]" />
                        </div>
                        <div
                          className={`ravi-arc-title ravi-arc-title-${index + 1} text-left text-[1.22rem] font-semibold leading-[0.92] tracking-[-0.05em] text-white xl:text-[1.38rem]`}
                        >
                          {step.label}
                        </div>
                      </div>
                      {index < arcSteps.length - 1 ? (
                        <div
                          className={`ravi-arc-link ravi-arc-link-${index + 1} h-px origin-left scale-x-0 border-t border-dashed border-[#bfe3ff]/58 opacity-0`}
                        />
                      ) : null}
                    </div>
                  ))}
                </div>

                <div className="relative flex flex-col gap-6 lg:hidden">
                  {arcSteps.map((step, index) => (
                    <article
                      key={step.label}
                      className={`ravi-arc-step ravi-arc-step-${index + 1} relative pl-8 text-left`}
                    >
                      <div
                        className={`ravi-arc-head ravi-arc-head-${index + 1} flex items-center gap-4 opacity-0`}
                      >
                        <div className="ravi-arc-stop absolute left-0 top-2 flex h-4 w-4 items-center justify-center rounded-full border border-[#bfe3ff]/60 bg-[#bfe3ff]/16 shadow-[0_0_22px_rgba(138,210,255,0.24)]">
                          <div className="h-1.5 w-1.5 rounded-full bg-[#eef8ff]" />
                        </div>
                        <div
                          className={`ravi-arc-title ravi-arc-title-${index + 1} text-[1.3rem] font-semibold leading-[0.92] tracking-[-0.05em] text-white sm:text-[1.55rem]`}
                        >
                          {step.label}
                        </div>
                      </div>
                      <p
                        className={`ravi-arc-body ravi-arc-body-${index + 1} mt-3 max-w-none text-sm leading-6 text-white/72 opacity-0 sm:text-[0.98rem]`}
                      >
                        {step.body}
                      </p>
                    </article>
                  ))}
                </div>

                <div className="hidden lg:grid lg:grid-cols-4 lg:gap-8 lg:pt-14">
                  {arcSteps.map((step, index) => (
                    <article
                      key={step.label}
                      className={`ravi-arc-step ravi-arc-step-${index + 1} text-left`}
                    >
                      <p
                        className={`ravi-arc-body ravi-arc-body-${index + 1} max-w-none text-[0.98rem] leading-7 text-white/72 opacity-0 xl:text-[1.02rem]`}
                      >
                        {step.body}
                      </p>
                    </article>
                  ))}
                </div>
              </div>
            </div>

            <p className="ravi-final mt-6 max-w-3xl text-balance text-[1.05rem] font-medium leading-7 tracking-[-0.03em] text-white sm:text-[1.2rem]">
              That gives me the clarity to build Sakhi.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
