"use client";

import { motion } from "framer-motion";

type GlassCardProps = {
  title: string;
  description: string;
  eyebrow?: string;
  index?: number;
};

const cinematicEase = [0.22, 1, 0.36, 1] as const;

export default function GlassCard({
  title,
  description,
  eyebrow,
  index = 0,
}: GlassCardProps) {
  return (
    <motion.article
      initial={{ opacity: 0, y: 40, scale: 0.98 }}
      whileInView={{ opacity: 1, y: 0, scale: 1 }}
      transition={{
        duration: 0.62,
        delay: index * 0.06,
        ease: cinematicEase,
      }}
      viewport={{ once: true, amount: 0.25 }}
      className="relative overflow-hidden rounded-[28px] border border-white/10 bg-white/[0.06] p-5 backdrop-blur-xl"
    >
      <div className="absolute inset-x-5 top-0 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent" />

      <div className="flex items-center justify-between gap-4">
        <div className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-500">
          Phase {String(index + 1).padStart(2, "0")}
        </div>
        {eyebrow ? (
          <div className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.26em] text-[#c7d4ff]">
            {eyebrow}
          </div>
        ) : null}
      </div>

      <h3 className="mt-5 font-display text-2xl font-semibold tracking-[-0.03em] text-white">
        {title}
      </h3>
      <p className="mt-3 text-sm leading-7 text-slate-300">{description}</p>
    </motion.article>
  );
}
