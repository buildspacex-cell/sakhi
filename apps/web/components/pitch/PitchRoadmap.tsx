"use client";

import { FadeIn } from "@/components/pitch/FadeIn";

type PhaseStatus = "COMPLETE" | "IN PROGRESS" | "NEXT" | "PLANNED" | "FUTURE";

const phases: {
  num: string;
  title: string;
  bullets: string[];
  status: PhaseStatus;
}[] = [
  {
    num: "Phase 01",
    title: "Continuity Foundation",
    bullets: ["Topic threads and arc building", "Deep Reflect journeys", "Kala governance engine"],
    status: "COMPLETE",
  },
  {
    num: "Phase 02",
    title: "Intelligence Layer",
    bullets: ["Intent detection and probing", "Context shaping and response control", "Structured prompt orchestration"],
    status: "IN PROGRESS",
  },
  {
    num: "Phase 03",
    title: "Execution Layer",
    bullets: ["LLM aggregation and routing", "Structured prompt orchestration", "Turn-by-turn execution pipeline"],
    status: "NEXT",
  },
  {
    num: "Phase 04",
    title: "Outcome Capture",
    bullets: ["Track actions and decisions after the turn", "Feedback signal collection", "Outcome-linked continuity"],
    status: "PLANNED",
  },
  {
    num: "Phase 05",
    title: "Learning System",
    bullets: ["Behavior pattern detection", "Success and failure learning", "Adaptive response evolution"],
    status: "PLANNED",
  },
  {
    num: "Phase 06",
    title: "Expansion Layer",
    bullets: ["Health, finance, decision systems", "Sakhi Network for shared context", "API layer for continuity developers"],
    status: "FUTURE",
  },
];

function statusStyles(status: PhaseStatus) {
  switch (status) {
    case "COMPLETE":
      return { card: "border-[#8ab0ff]/30 bg-[#8ab0ff]/[0.06]", badge: "bg-[#8ab0ff]/20 text-[#8ab0ff]" };
    case "IN PROGRESS":
      return { card: "border-white/15 bg-white/[0.04]", badge: "bg-white/10 text-white/80" };
    case "NEXT":
      return { card: "border-white/[0.08] bg-white/[0.02]", badge: "bg-white/[0.08] text-white/60" };
    default:
      return { card: "border-white/[0.08] bg-transparent opacity-75", badge: "bg-white/[0.06] text-white/40" };
  }
}

export function PitchRoadmap() {
  return (
    <section id="roadmap" className="py-32 px-8 sm:px-16 lg:px-24 bg-[#020617]">
      <div className="mx-auto max-w-6xl">
        <FadeIn>
          <p className="text-[10px] sm:text-[11px] font-semibold uppercase tracking-[0.3em] text-[#8ab0ff]/80">
            Roadmap
          </p>
        </FadeIn>
        <FadeIn delay={100}>
          <h2 className="mt-5 font-semibold text-white max-w-[20ch] leading-[1.08] -tracking-[0.04em]" style={{ fontSize: "clamp(2.5rem, 5vw, 4.5rem)" }}>
            Six moves to build the continuity layer.
          </h2>
        </FadeIn>
        <FadeIn delay={200}>
          <p className="mt-6 text-xl text-white/60 max-w-2xl leading-relaxed">
            Each phase adds a new capability to the loop.
          </p>
        </FadeIn>
        <div className="mt-16 grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {phases.map((phase, i) => {
            const styles = statusStyles(phase.status);
            return (
              <FadeIn key={phase.num} delay={300 + i * 80}>
                <div className={`rounded-[28px] border px-7 py-8 h-full flex flex-col ${styles.card}`}>
                  <p className="text-[10px] font-semibold uppercase tracking-[0.25em] text-white/30">
                    {phase.num}
                  </p>
                  <h3 className="mt-3 text-base font-semibold text-white leading-snug">
                    {phase.title}
                  </h3>
                  <ul className="mt-4 flex-1 space-y-2">
                    {phase.bullets.map((bullet) => (
                      <li key={bullet} className="text-sm text-white/44 leading-snug flex gap-2">
                        <span className="mt-1.5 h-1 w-1 flex-shrink-0 rounded-full bg-white/20" />
                        {bullet}
                      </li>
                    ))}
                  </ul>
                  <div className="mt-6 flex justify-end">
                    <span className={`rounded-full px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] ${styles.badge}`}>
                      {phase.status}
                    </span>
                  </div>
                </div>
              </FadeIn>
            );
          })}
        </div>
      </div>
    </section>
  );
}
