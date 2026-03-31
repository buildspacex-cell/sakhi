"use client";

import { motion } from "framer-motion";

import Section from "@/components/cinematic/Section";

type StorySectionData = {
  id: string;
  label: string;
  eyebrow: string;
  title: string;
  description: string;
  body: string;
  points: ReadonlyArray<string>;
};

type StorySectionProps = {
  section: StorySectionData;
  reverse?: boolean;
};

const cinematicEase = [0.22, 1, 0.36, 1] as const;

export default function StorySection({
  section,
  reverse = false,
}: StorySectionProps) {
  return (
    <Section id={section.id} label={section.label}>
      <div
        className={`grid gap-8 lg:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)] lg:items-center ${
          reverse ? "lg:[&>*:first-child]:order-2" : ""
        }`}
      >
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.72, ease: cinematicEase }}
          viewport={{ once: true, amount: 0.35 }}
          className="rounded-[34px] border border-white/10 bg-[linear-gradient(180deg,rgba(18,23,32,0.88),rgba(10,13,18,0.94))] p-7 shadow-panel sm:p-9"
        >
          <div className="text-[11px] font-semibold uppercase tracking-[0.34em] text-slate-400">
            {section.eyebrow}
          </div>
          <h2 className="mt-5 max-w-3xl font-display text-4xl font-semibold tracking-[-0.05em] text-white sm:text-5xl lg:text-6xl">
            {section.title}
          </h2>
          <p className="mt-5 max-w-2xl text-base leading-8 text-slate-300 sm:text-lg">
            {section.description}
          </p>
          <p className="mt-7 max-w-2xl text-sm leading-8 text-slate-300 sm:text-base">
            {section.body}
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 48, scale: 0.98 }}
          whileInView={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.72, delay: 0.08, ease: cinematicEase }}
          viewport={{ once: true, amount: 0.35 }}
          className="relative overflow-hidden rounded-[34px] border border-white/10 bg-white/[0.05] p-6 backdrop-blur-xl sm:p-8"
        >
          <div className="absolute inset-x-8 top-0 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent" />
          <div className="text-[10px] font-semibold uppercase tracking-[0.28em] text-[#c7d4ff]">
            Section frame
          </div>
          <div className="mt-6 grid gap-3">
            {section.points.map((point, index) => (
              <div
                key={point}
                className="rounded-[22px] border border-white/10 bg-[#121722]/78 px-4 py-4"
              >
                <div className="text-[10px] font-semibold uppercase tracking-[0.3em] text-slate-500">
                  {String(index + 1).padStart(2, "0")}
                </div>
                <div className="mt-2 text-sm leading-7 text-slate-200">{point}</div>
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </Section>
  );
}
