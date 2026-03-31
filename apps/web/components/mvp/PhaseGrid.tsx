"use client";

import { useRef } from "react";

import { motion, useScroll, useTransform } from "framer-motion";
import useStoryFocusOffsets from "@/components/story/useStoryFocusOffsets";

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

function PhaseCard({
  progress,
  phase,
  index,
}: {
  progress: ReturnType<typeof useScroll>["scrollYProgress"];
  phase: PhaseItem;
  index: number;
}) {
  const cardStart = 0.06 + index * 0.05;
  const cardPeak = Math.min(0.86, cardStart + 0.14);
  const cardEnd = Math.min(1, cardPeak + 0.1);

  const opacity = useTransform(progress, [cardStart, cardPeak, cardEnd, 1], [0.18, 1, 1, 0.72]);
  const y = useTransform(progress, [cardStart, cardPeak, cardEnd], [28, 0, -8]);

  return (
    <motion.article
      style={{ opacity, y }}
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
      <p className="mt-3 text-sm leading-7 text-slate-300">{phase.detail}</p>
    </motion.article>
  );
}

export function PhaseGrid({
  title,
  description,
  phases,
  className = "",
}: PhaseGridProps) {
  const ref = useRef<HTMLElement | null>(null);
  const offsets = useStoryFocusOffsets();
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: [...offsets.phase],
  });

  const opacity = useTransform(scrollYProgress, [0, 0.16, 0.9, 1], [0.18, 1, 1, 0.7]);
  const y = useTransform(scrollYProgress, [0, 0.16, 0.9, 1], [24, 0, -8, -16]);

  return (
    <motion.section
      ref={ref}
      style={{ opacity, y }}
      className={`space-y-6 ${className}`}
    >
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
          <PhaseCard
            key={phase.title}
            progress={scrollYProgress}
            phase={phase}
            index={index}
          />
        ))}
      </div>
    </motion.section>
  );
}

export default PhaseGrid;
