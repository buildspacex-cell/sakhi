"use client";

import { motion } from "framer-motion";

type LoopStep = {
  title: string;
  detail: string;
};

type AnimatedLoopProps = {
  title: string;
  description?: string;
  steps: ReadonlyArray<LoopStep>;
};

const cinematicEase = [0.22, 1, 0.36, 1] as const;

const containerVariants = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.08,
    },
  },
};

const cardVariants = {
  hidden: { opacity: 0, y: 34, scale: 0.97 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      duration: 0.68,
      ease: cinematicEase,
    },
  },
};

export default function AnimatedLoop({
  title,
  description,
  steps,
}: AnimatedLoopProps) {
  return (
    <div className="rounded-[36px] border border-white/10 bg-[linear-gradient(180deg,rgba(16,20,27,0.9),rgba(11,14,20,0.96))] p-6 shadow-panel sm:p-8 lg:p-10">
      <div className="mx-auto max-w-3xl text-center">
        <div className="text-[11px] font-semibold uppercase tracking-[0.32em] text-slate-400">
          Operating loop
        </div>
        <h2 className="mt-4 font-display text-3xl font-semibold tracking-[-0.04em] text-white sm:text-4xl lg:text-5xl">
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

        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.25 }}
          className="grid gap-4 md:grid-cols-2 xl:grid-cols-7"
        >
          {steps.map((step, index) => (
            <motion.article
              key={step.title}
              variants={cardVariants}
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

              {index < steps.length - 1 ? (
                <div className="mt-5 text-xs font-semibold uppercase tracking-[0.28em] text-[#8fa8ff] xl:hidden">
                  Next
                </div>
              ) : (
                <div className="mt-5 text-xs font-semibold uppercase tracking-[0.28em] text-emerald-300/80">
                  Compounds
                </div>
              )}
            </motion.article>
          ))}
        </motion.div>
      </div>
    </div>
  );
}
