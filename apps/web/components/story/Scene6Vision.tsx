"use client";

const pillarLines = [
  "Build a living model of you evolving over time.",
  "Make your life visible across time, as a whole.",
  "Help you act decisively and learn from what follows.",
] as const;

const voiceLines = ["I see you.", "I understand you.", "I act for you."] as const;

export default function Scene6Vision() {
  return (
    <div className="relative flex h-full w-full items-center overflow-hidden px-6 pb-[calc(env(safe-area-inset-bottom)+4.75rem)] pt-[calc(env(safe-area-inset-top)+5.75rem)] sm:px-10 sm:pb-[calc(env(safe-area-inset-bottom)+4.75rem)] sm:pt-[calc(env(safe-area-inset-top)+5rem)] lg:px-16 lg:pb-24 lg:pt-24 xl:px-24">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_18%,rgba(162,179,255,0.16),transparent_24%),radial-gradient(circle_at_20%_70%,rgba(108,128,255,0.1),transparent_28%),radial-gradient(circle_at_78%_72%,rgba(112,205,255,0.08),transparent_30%)]" />

      <div className="relative mx-auto flex w-full max-w-6xl flex-col items-center text-center">
        {/* Small supporting headline */}
        <div className="vision-promise w-full">
          <div className="text-[clamp(1.5rem,2.4vw,2.4rem)] font-medium leading-[1.3] tracking-[-0.03em] text-slate-300/80">
            <div className="vision-promise-line-1">Sakhi makes your life seen,</div>
            <div className="vision-promise-line-2">understood, and actionable.</div>
          </div>
        </div>

        <div className="vision-pillars-stage mt-10 w-full max-w-5xl">
          <div className="grid gap-5 md:grid-cols-[1fr_1.15fr_1fr] md:items-stretch">
            {pillarLines.map((line, index) => (
              <div
                key={line}
                className={
                  index === 0
                    ? "text-left"
                    : index === 1
                      ? "text-center"
                      : "text-right"
                }
              >
                <div className={`vision-pillar-card vision-pillar-card-${index + 1} flex h-full flex-col`}>
                  {/* Voice line — big, dominant */}
                  <p className={`vision-pillar-voice vision-pillar-voice-${index + 1} text-[clamp(2.4rem,4vw,4.2rem)] font-semibold leading-[1.06] tracking-[-0.055em] text-white opacity-0`}>
                    {voiceLines[index]}
                  </p>
                  {/* Pillar description — small, supporting */}
                  <p className="vision-pillar-desc mt-4 text-pretty text-[clamp(0.92rem,1.18vw,1.15rem)] leading-[1.4] tracking-[-0.02em] text-slate-300/72">
                    {line}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="vision-signoff mt-10 opacity-0">
          <p className="vision-signoff-label text-[0.95rem] font-medium uppercase tracking-[0.28em] text-[#c8d4ff]/78">
            - Sakhi
          </p>
        </div>
      </div>
    </div>
  );
}
