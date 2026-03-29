"use client";

import { useRef } from "react";

import { motion, useScroll, useTransform } from "framer-motion";
import useStoryFocusOffsets from "@/components/story/useStoryFocusOffsets";

type LoopStep = {
  title: string;
  detail: string;
};

type AnimatedLoopProps = {
  title: string;
  description?: string;
  steps: ReadonlyArray<LoopStep>;
};

function LoopCard({
  progress,
  step,
  index,
}: {
  progress: ReturnType<typeof useScroll>["scrollYProgress"];
  step: LoopStep;
  index: number;
}) {
  const activeStart = 0.08 + index * 0.12;
  const activePeak = activeStart + 0.14;
  const activeEnd = activePeak + 0.12;

  const opacity = useTransform(progress, [activeStart, activePeak, activeEnd, 1], [0.22, 1, 1, 0.7]);
  const y = useTransform(progress, [activeStart, activePeak, activeEnd], [34, 0, -10]);
  const glow = useTransform(
    progress,
    [activeStart, activePeak, activeEnd],
    [
      "0 0 0 rgba(120,160,255,0)",
      "0 0 12px rgba(120,160,255,0.5)",
      "0 0 0 rgba(120,160,255,0)",
    ],
  );

  return (
    <motion.article
      style={{ opacity, y, boxShadow: glow }}
      className="group relative overflow-hidden rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(20,25,36,0.92),rgba(13,16,22,0.96))] p-5"
    >
      <div className="absolute inset-x-5 top-0 h-px bg-gradient-to-r from-transparent via-white/18 to-transparent" />
      <div className="flex items-center justify-between gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-full border border-[#9fb9ff]/25 bg-[#17202f] text-xs font-semibold tracking-[0.24em] text-[#c9d6ff]">
          {String(index + 1).padStart(2, "0")}
        </div>
        <div className="text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-500">
          Stage
        </div>
      </div>

      <div className="mt-6 text-lg font-medium text-white">{step.title}</div>
      <p className="mt-3 text-sm leading-6 text-slate-300">{step.detail}</p>
    </motion.article>
  );
}

export default function AnimatedLoop({
  title,
  description,
  steps,
}: AnimatedLoopProps) {
  const ref = useRef<HTMLDivElement | null>(null);
  const offsets = useStoryFocusOffsets();
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: [...offsets.loop],
  });

  const wrapperOpacity = useTransform(scrollYProgress, [0, 0.18, 0.86, 1], [0.16, 1, 1, 0.36]);
  const wrapperY = useTransform(scrollYProgress, [0, 0.18, 0.86, 1], [32, 0, -8, -18]);

  return (
    <motion.div
      ref={ref}
      style={{ opacity: wrapperOpacity, y: wrapperY }}
      className="rounded-[36px] border border-white/10 bg-[linear-gradient(180deg,rgba(16,20,27,0.9),rgba(11,14,20,0.96))] p-6 shadow-panel sm:p-8 lg:p-10"
    >
      <div className="mx-auto max-w-3xl text-center">
        <div className="text-[11px] font-semibold uppercase tracking-[0.32em] text-slate-400">
          Operating loop
        </div>
        <h2 className="mt-4 text-3xl font-semibold tracking-[-0.04em] text-white sm:text-4xl lg:text-5xl">
          {title}
        </h2>
        {description ? (
          <p className="mx-auto mt-4 max-w-2xl text-sm leading-7 text-slate-300 sm:text-base">
            {description}
          </p>
        ) : null}
      </div>

      <div className="relative mt-10">
        <div className="pointer-events-none absolute left-10 right-10 top-8 hidden h-px bg-gradient-to-r from-transparent via-white/12 to-transparent xl:block" />

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {steps.map((step, index) => (
            <LoopCard
              key={step.title}
              progress={scrollYProgress}
              step={step}
              index={index}
            />
          ))}
        </div>
      </div>
    </motion.div>
  );
}
