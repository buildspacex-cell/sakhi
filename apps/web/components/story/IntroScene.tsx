"use client";

import { useRef } from "react";

import { motion, useScroll, useTransform } from "framer-motion";

type IntroStat = {
  value: string;
};

type IntroSceneProps = {
  stats: readonly IntroStat[];
};

type StatementTimeline = {
  points: number[];
  opacity: number[];
  x: string[];
  scale: number[];
  bright: number[];
};

type RevealWindow = {
  points: number[];
  opacity: number[];
};

function ActiveStatement({
  progress,
  index,
  value,
}: IntroStat & {
  progress: ReturnType<typeof useScroll>["scrollYProgress"];
  index: number;
}) {
  const timelines: StatementTimeline[] = [
    {
      points: [0.36, 0.42, 0.5, 0.58],
      opacity: [0, 1, 1, 0],
      x: ["3vw", "0vw", "0vw", "-10vw"],
      scale: [0.992, 1, 1, 0.984],
      bright: [0.86, 1, 1, 0.76],
    },
    {
      points: [0.5, 0.56, 0.64, 0.7],
      opacity: [0, 1, 1, 0],
      x: ["3vw", "0vw", "0vw", "0vw"],
      scale: [0.992, 1, 1, 0.986],
      bright: [0.86, 1, 1, 0.8],
    },
    {
      points: [0.66, 0.72, 0.8, 0.88],
      opacity: [0, 1, 1, 0],
      x: ["3vw", "0vw", "0vw", "10vw"],
      scale: [0.992, 1, 1, 0.984],
      bright: [0.86, 1, 1, 0.8],
    },
  ];

  const timeline = timelines[index];
  const opacity = useTransform(progress, timeline.points, timeline.opacity);
  const x = useTransform(progress, timeline.points, timeline.x);
  const scale = useTransform(progress, timeline.points, timeline.scale);
  const brightness = useTransform(progress, timeline.points, timeline.bright);

  return (
    <motion.div
      style={{ opacity, x, scale }}
      className="absolute inset-0 flex items-center justify-center will-change-transform"
    >
      <motion.p
        style={{ opacity: brightness }}
        className="mx-auto max-w-[16ch] text-center text-[clamp(2.1rem,4vw,3.7rem)] font-medium leading-[1.06] tracking-[-0.055em] text-white"
      >
        {value}
      </motion.p>
    </motion.div>
  );
}

function ParkedStatement({
  progress,
  index,
  value,
}: IntroStat & {
  progress: ReturnType<typeof useScroll>["scrollYProgress"];
  index: number;
}) {
  const revealWindows: RevealWindow[] = [
    { points: [0.52, 0.6], opacity: [0, 0.62] },
    { points: [0.84, 0.92], opacity: [0, 0.92] },
    { points: [0.8, 0.88], opacity: [0, 0.68] },
  ];

  const window = revealWindows[index];
  const opacity = useTransform(progress, window.points, window.opacity);
  const y = useTransform(progress, window.points, [10, 0]);
  const scale = useTransform(progress, window.points, [0.985, 1]);

  return (
    <motion.div style={{ opacity, y, scale }} className="will-change-transform">
      <p className="text-pretty text-[clamp(0.95rem,1.15vw,1.2rem)] leading-[1.25] tracking-[-0.025em] text-slate-200/72">
        {value}
      </p>
    </motion.div>
  );
}

function StatementProgress({
  progress,
  index,
}: {
  progress: ReturnType<typeof useScroll>["scrollYProgress"];
  index: number;
}) {
  const start = 0.36 + index * 0.18;
  const enter = start + 0.06;
  const settle = enter + 0.16;
  const opacity = useTransform(progress, [start - 0.04, start, settle], [0.18, 0.32, 1]);
  const scaleX = useTransform(progress, [start, settle], [0.3, 1]);

  return (
    <motion.div
      style={{ opacity }}
      className="h-[2px] w-14 overflow-hidden rounded-full bg-white/10"
    >
      <motion.div
        style={{ scaleX }}
        className="h-full origin-left rounded-full bg-[#c7d3ff]"
      />
    </motion.div>
  );
}

export default function IntroScene({ stats }: IntroSceneProps) {
  const ref = useRef<HTMLDivElement | null>(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start 32%", "end 32%"],
  });

  const lineOneOpacity = useTransform(scrollYProgress, [0, 0.1, 0.18], [1, 1, 0]);
  const lineOneY = useTransform(scrollYProgress, [0, 0.1, 0.18], [0, 0, -30]);
  const lineOneScale = useTransform(scrollYProgress, [0, 0.1, 0.18], [1, 1, 0.984]);
  const lineOneBrightness = useTransform(
    scrollYProgress,
    [0, 0.1, 0.18],
    [1, 1, 0.76],
  );

  const lineTwoOpacity = useTransform(scrollYProgress, [0.12, 0.22, 0.32], [0, 1, 1]);
  const lineTwoY = useTransform(scrollYProgress, [0.12, 0.22, 0.32], [24, 0, 0]);
  const lineTwoScale = useTransform(scrollYProgress, [0.12, 0.22, 0.32], [0.982, 1, 1]);
  const lineTwoBrightness = useTransform(
    scrollYProgress,
    [0.12, 0.22, 0.32],
    [0.82, 1, 1],
  );

  const explanationOpacity = useTransform(scrollYProgress, [0.24, 0.38], [0, 1]);
  const explanationY = useTransform(scrollYProgress, [0.24, 0.38], [28, 0]);
  const explanationBrightness = useTransform(
    scrollYProgress,
    [0.24, 0.38],
    [0.84, 1],
  );

  const systemOpacity = useTransform(scrollYProgress, [0.34, 0.48], [0, 1]);
  const systemY = useTransform(scrollYProgress, [0.34, 0.48], [28, 0]);
  const systemBrightness = useTransform(
    scrollYProgress,
    [0.34, 0.48],
    [0.84, 1],
  );

  return (
    <div ref={ref} className="mx-auto flex w-full max-w-6xl flex-col items-center text-center">
      <div className="w-full max-w-5xl">
        <h1 className="text-[clamp(4.2rem,10vw,8rem)] font-semibold leading-[0.92] tracking-[-0.075em] text-white">
          <motion.span
            style={{
              opacity: lineOneOpacity,
              y: lineOneY,
              scale: lineOneScale,
            }}
            className="block will-change-transform"
          >
            <motion.span style={{ opacity: lineOneBrightness }} className="block">
              Stop reacting.
            </motion.span>
          </motion.span>
          <motion.span
            style={{
              opacity: lineTwoOpacity,
              y: lineTwoY,
              scale: lineTwoScale,
            }}
            className="block will-change-transform"
          >
            <motion.span style={{ opacity: lineTwoBrightness }} className="block">
              Start shaping.
            </motion.span>
          </motion.span>
        </h1>
      </div>

      <motion.div
        style={{
          opacity: explanationOpacity,
          y: explanationY,
        }}
        className="mt-14 w-full max-w-3xl will-change-transform"
      >
        <motion.p
          style={{ opacity: explanationBrightness }}
          className="mx-auto max-w-2xl text-[clamp(1.2rem,2.1vw,1.7rem)] leading-[1.5] tracking-[-0.03em] text-slate-300"
        >
          Sakhi learns how you think and evolves with you, so your decisions
          become clearer over time.
        </motion.p>
      </motion.div>

      <motion.div
        style={{ opacity: systemOpacity, y: systemY }}
        className="mt-16 w-full will-change-transform"
      >
        <motion.div style={{ opacity: systemBrightness }} className="mx-auto max-w-5xl">
          <div className="mx-auto max-w-4xl">
            <div className="relative min-h-[9rem] overflow-hidden sm:min-h-[10rem] lg:min-h-[11rem]">
              {stats.map((stat, index) => (
                <ActiveStatement
                  key={stat.value}
                  progress={scrollYProgress}
                  index={index}
                  {...stat}
                />
              ))}
            </div>

            <div className="mt-8 flex items-center justify-center gap-3">
              {stats.map((stat, index) => (
                <StatementProgress
                  key={`${stat.value}-progress`}
                  progress={scrollYProgress}
                  index={index}
                />
              ))}
            </div>

            <div className="mt-8 grid gap-4 md:grid-cols-[1fr_1.15fr_1fr] md:items-start">
              {stats.map((stat, index) => (
                <div
                  key={`${stat.value}-parked`}
                  className={
                    index === 0
                      ? "text-left"
                      : index === 1
                        ? "text-center"
                        : "text-right"
                  }
                >
                  <ParkedStatement
                    progress={scrollYProgress}
                    index={index}
                    {...stat}
                  />
                </div>
              ))}
            </div>
          </div>
        </motion.div>
      </motion.div>
    </div>
  );
}
