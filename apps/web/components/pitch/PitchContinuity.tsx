"use client";

import { FadeIn } from "@/components/pitch/FadeIn";

const occupancyBubbles = [
  { label: "Start up",   share: "65%", moments: "28 moments", size: "lg",  accent: true  },
  { label: "Family",     share: "14%", moments: "6 moments",  size: "md",  accent: false },
  { label: "Caregiving", share: "7%",  moments: "3 moments",  size: "sm",  accent: false },
  { label: "Career",     share: "7%",  moments: "3 moments",  size: "sm",  accent: false },
  { label: "Self Care",  share: "7%",  moments: "3 moments",  size: "sm",  accent: false },
];

const arcPhases = [
  { label: "Where It Began", title: "An idea with ache",       body: "The thread began with one question: was this passing frustration, or the start of something to build?", meta: "Day 12",                major: true  },
  { label: "Phase 1",        title: "Founder question",        body: "Could this become real?",                                                                                meta: "Day 16",               major: false },
  { label: "Phase 2",        title: "Rhythm clicked",          body: "Rhythm, not remedies.",                                                                                  meta: "Day 19",               major: false },
  { label: "Phase 3",        title: "RAG felt brittle",        body: "The obvious path felt thin.",                                                                            meta: "Day 24",               major: false },
  { label: "Phase 4",        title: "Knowledge graph",         body: "Slower, more respectful.",                                                                               meta: "Day 28",               major: false },
  { label: "Phase 5",        title: "Still uneasy",            body: "Correct, but not personal.",                                                                             meta: "Day 35",               major: false },
  { label: "Phase 6",        title: "Clarity surfaced",        body: "Reflection became the job.",                                                                             meta: "Day 41",               major: false },
  { label: "Phase 7",        title: "Validation pressure",     body: "External pressure sharpened it.",                                                                        meta: "Day 58",               major: false },
  { label: "Phase 8",        title: "Build, not pitch",        body: "Usage had to prove it.",                                                                                 meta: "Day 66",               major: false },
  { label: "Phase 9",        title: "Continuity core",         body: "The thread became the product.",                                                                         meta: "Day 72",               major: false },
  { label: "Phase 10",       title: "Product shape",           body: "The path finally had form.",                                                                             meta: "Day 115",              major: false },
  { label: "Where It Is Now",title: "A visible direction",     body: "The thread is no longer abstract. It now has form, continuity, and a next step people can feel.",        meta: "104 days of continuity", major: true },
];

const desktopArcOrder = [0, 1, 2, 3, 7, 6, 5, 4, 8, 9, 10, 11] as const;

const continuityLines = [
  "Noise becomes pattern.",
  "Pattern becomes readable occupancy.",
  "The system gathers scattered moments and returns which threads have actually occupied your life.",
  "So it shows not just what is happening now, but what has been taking up space across time.",
  "This is where scattered life becomes coherent.",
];

export function PitchContinuity() {
  const renderArcCard = (phase: (typeof arcPhases)[number]) => (
    <div
      key={`${phase.label}-${phase.title}`}
      className={`rounded-[20px] border px-4 py-4 ${
        phase.major
          ? "border-[#8cb7ff]/25 bg-[#8cb7ff]/[0.06]"
          : "border-white/[0.07] bg-white/[0.02]"
      }`}
    >
      <div
        className={`text-[8px] font-semibold uppercase tracking-[0.2em] ${
          phase.major ? "text-[#8cb7ff]/70" : "text-white/28"
        }`}
      >
        {phase.label}
      </div>
      <div
        className={`mt-1.5 font-semibold tracking-[-0.04em] text-white ${
          phase.major ? "text-[1rem]" : "text-[0.85rem]"
        }`}
      >
        {phase.title}
      </div>
      <p
        className={`mt-1.5 leading-[1.4] ${
          phase.major ? "text-[0.78rem] text-white/68" : "text-[0.7rem] text-white/40"
        }`}
      >
        {phase.body}
      </p>
      <div
        className={`mt-2 text-[8px] font-semibold uppercase tracking-[0.2em] ${
          phase.major ? "text-[#8cb7ff]/80" : "text-[#8cb7ff]/50"
        }`}
      >
        {phase.meta}
      </div>
    </div>
  );

  return (
    <section id="continuity" className="overflow-hidden border-t border-white/[0.06] bg-[#020617] scroll-mt-16">

      {/* Life Occupancy */}
      <div className="px-8 sm:px-12 lg:px-16 xl:px-24 py-24">
        <FadeIn>
          <div className="relative mx-auto w-full max-w-[62rem] overflow-hidden rounded-[40px] border border-white/[0.09] bg-[linear-gradient(158deg,rgba(12,17,30,0.98),rgba(7,10,20,0.96))] shadow-[0_52px_160px_rgba(0,0,0,0.52)] backdrop-blur-2xl">
            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_60%_50%_at_15%_10%,rgba(110,148,230,0.14),transparent),radial-gradient(ellipse_50%_45%_at_88%_92%,rgba(105,78,55,0.12),transparent)]" />

            {/* Header */}
            <div className="relative z-10 flex items-start justify-between gap-5 border-b border-white/[0.06] px-7 pb-5 pt-6 sm:px-9 sm:pt-7">
              <div>
                <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-[9px] font-semibold uppercase tracking-[0.28em] text-white/40">
                  <span className="h-1.5 w-1.5 rounded-full bg-[#8cb7ff]/70" />
                  Vidhya · Profile
                </div>
                <div className="mt-3 text-[1.85rem] font-semibold tracking-[-0.055em] text-white sm:text-[2rem]">Life Occupancy</div>
                <p className="mt-1.5 max-w-[30rem] text-[0.9rem] leading-[1.65] tracking-[-0.015em] text-white/44">
                  Bubble size reflects how much each thread has occupied your attention.
                </p>
              </div>
              <div className="shrink-0 rounded-2xl border border-white/[0.09] bg-white/[0.03] px-4 py-3 text-right backdrop-blur-sm">
                <div className="text-[9px] font-semibold uppercase tracking-[0.26em] text-white/30">Active</div>
                <div className="mt-1.5 text-[1.05rem] font-semibold tracking-[-0.04em] text-white/82">5 threads</div>
              </div>
            </div>

            {/* Bubble cloud */}
            <div className="relative h-[28rem] overflow-visible px-2">
              {occupancyBubbles.map((b, i) => {
                const positions = [
                  { left: "31%", top: "50%" },
                  { left: "72%", top: "28%" },
                  { left: "52%", top: "74%" },
                  { left: "70%", top: "62%" },
                  { left: "86%", top: "44%" },
                ];
                const sizes = { lg: { w: "19rem", h: "19rem" }, md: { w: "11rem", h: "11rem" }, sm: { w: "8.8rem", h: "8.8rem" } };
                const sz = sizes[b.size as "lg" | "md" | "sm"];
                const pos = positions[i];
                return (
                  <div
                    key={b.label}
                    className={`absolute flex -translate-x-1/2 -translate-y-1/2 flex-col items-center justify-center rounded-full text-center ${
                      b.accent
                        ? "border border-[#dce8ff]/50 bg-[radial-gradient(circle_at_36%_28%,rgba(235,242,255,0.19),rgba(165,190,235,0.26)_48%,rgba(55,72,108,0.38)_100%)] shadow-[0_0_80px_rgba(148,178,255,0.16)]"
                        : "border border-white/[0.11] bg-[radial-gradient(circle_at_36%_28%,rgba(255,255,255,0.08),rgba(255,255,255,0.022)_72%)] backdrop-blur-sm"
                    }`}
                    style={{ width: sz.w, height: sz.h, left: pos.left, top: pos.top, zIndex: b.accent ? 4 : 2 }}
                  >
                    <div className={`font-semibold tracking-[-0.03em] text-white/88 ${b.accent ? "text-[1.1rem]" : "text-[0.88rem]"}`}>{b.label}</div>
                    <div className={`leading-none tracking-[-0.07em] text-white ${b.accent ? "mt-1 text-[3.8rem] font-bold" : "mt-1 text-[2.4rem] font-bold"}`}>{b.share}</div>
                    <div className={`tracking-[-0.01em] ${b.accent ? "mt-2 text-[0.92rem] text-white/55" : "mt-1.5 text-[0.78rem] text-white/40"}`}>{b.moments}</div>
                  </div>
                );
              })}
            </div>
          </div>
        </FadeIn>
      </div>

      {/* Continuity Arc */}
      <div className="px-8 sm:px-12 lg:px-16 xl:px-24 pb-24">
        <FadeIn delay={100}>
          <div className="relative w-full max-w-[72rem] mx-auto overflow-hidden rounded-[36px] border border-[#8cb7ff]/10 bg-[linear-gradient(158deg,rgba(11,17,32,0.97),rgba(7,10,20,0.96))] px-6 py-5 shadow-[0_44px_130px_rgba(0,0,0,0.42)] backdrop-blur-xl sm:px-8 sm:py-6">
            <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-[linear-gradient(90deg,transparent,rgba(140,183,255,0.35)_30%,rgba(180,210,255,0.5)_50%,rgba(140,183,255,0.35)_70%,transparent)]" />
            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_60%_45%_at_15%_0%,rgba(108,145,225,0.14),transparent)]" />

            <div className="relative z-10 mb-5">
              <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-[9px] font-semibold uppercase tracking-[0.28em] text-white/40">
                <span className="h-1.5 w-1.5 rounded-full bg-[#8cb7ff]/70" />
                Start up
              </div>
              <div className="mt-3 text-[1.6rem] font-semibold tracking-[-0.05em] text-white sm:text-[1.85rem]">Continuity Arc</div>
            </div>

            <div className="grid grid-cols-2 gap-5 sm:grid-cols-3 lg:hidden">
              {arcPhases.map((phase) => renderArcCard(phase))}
            </div>

            <div className="relative hidden lg:block">
              <div className="pointer-events-none absolute inset-0 z-0">
                {/*
                  viewBox 0 0 100 100, preserveAspectRatio=none.
                  Grid has px-6 (≈2.1 units each side in viewBox space).
                  Column gaps (gap-5 ≈ 1.74 units): centres at ~25.6, ~50, ~74.4
                  Row centres (3 equal rows): 16.7, 50, 83.3
                  Turns live in the px-6 margins: right side x>97.9, left side x<2.1
                */}
                <svg
                  viewBox="0 0 100 100"
                  preserveAspectRatio="none"
                  className="h-full w-full"
                  aria-hidden="true"
                >
                  {[
                    // Row 0 — column gap connectors (L→R)
                    "M24.7 16.7 L26.5 16.7",
                    "M49.1 16.7 L50.9 16.7",
                    "M73.5 16.7 L75.3 16.7",
                    // Right-side U-turn: row 0 → row 1
                    "M97.9 16.7 L99.4 16.7 L99.4 50 L97.9 50",
                    // Row 1 — column gap connectors (R→L)
                    "M75.3 50 L73.5 50",
                    "M50.9 50 L49.1 50",
                    "M26.5 50 L24.7 50",
                    // Left-side U-turn: row 1 → row 2
                    "M2.1 50 L0.6 50 L0.6 83.3 L2.1 83.3",
                    // Row 2 — column gap connectors (L→R)
                    "M24.7 83.3 L26.5 83.3",
                    "M49.1 83.3 L50.9 83.3",
                    "M73.5 83.3 L75.3 83.3",
                  ].map((d, i) => (
                    <g key={i}>
                      <path d={d} fill="none" stroke="rgba(140,183,255,0.18)" strokeWidth="1.1" strokeLinecap="round" strokeLinejoin="round" />
                      <path d={d} fill="none" stroke="rgba(180,210,255,0.6)" strokeWidth="0.45" strokeDasharray="1.2 1.5" strokeLinecap="round" strokeLinejoin="round" />
                    </g>
                  ))}
                </svg>
              </div>

              <div className="relative z-10 grid grid-cols-4 gap-5 px-6">
                {desktopArcOrder.map((index) => renderArcCard(arcPhases[index]))}
              </div>
            </div>
          </div>
        </FadeIn>
      </div>

      {/* "Your life, connected across time." */}
      <div className="px-8 sm:px-16 lg:px-24 py-32">
        <div className="max-w-4xl">
          <FadeIn>
            <div className="mb-6 text-xs tracking-[0.3em] text-white/40">CONTINUITY</div>
          </FadeIn>
          <FadeIn delay={100}>
            <h2
              className="font-semibold text-white leading-[1.02] -tracking-[0.055em]"
              style={{ fontSize: "clamp(3rem, 7vw, 6rem)" }}
            >
              Your life, connected across time.
            </h2>
          </FadeIn>
          <div className="mt-10 space-y-5 text-lg leading-relaxed text-white/60">
            {continuityLines.map((line, i) => (
              <FadeIn key={line} delay={200 + i * 150}>
                <p className={i === continuityLines.length - 1 ? "text-white/80 font-medium" : ""}>{line}</p>
              </FadeIn>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
