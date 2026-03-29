"use client";

import { useRef } from "react";

import { motion, useReducedMotion, useScroll, useTransform } from "framer-motion";

import useStoryFocusOffsets from "@/components/story/useStoryFocusOffsets";

type ResetCollapseSceneProps = {
  lines: readonly string[];
};

const fragments = [
  { text: "what if", left: "10%", top: "18%", x: 38, y: 20 },
  { text: "later tonight", left: "64%", top: "20%", x: -56, y: 24 },
  { text: "did I miss something", left: "22%", top: "38%", x: 44, y: -12 },
  { text: "call her back", left: "68%", top: "48%", x: -40, y: -10 },
  { text: "I should remember this", left: "18%", top: "70%", x: 46, y: -38 },
  { text: "what am I missing", left: "58%", top: "82%", x: -34, y: -42 },
  { text: "don't forget", left: "52%", top: "58%", x: -28, y: -18 },
  { text: "again?", left: "36%", top: "26%", x: 18, y: 18 },
] as const;

const threads = [
  { left: "16%", top: "24%", width: "30%", rotate: "10deg" },
  { left: "50%", top: "26%", width: "24%", rotate: "-8deg" },
  { left: "26%", top: "60%", width: "30%", rotate: "14deg" },
  { left: "52%", top: "74%", width: "18%", rotate: "-14deg" },
] as const;

const nodes = [
  { left: "22%", top: "22%", delay: 0.1 },
  { left: "54%", top: "34%", delay: 0.5 },
  { left: "72%", top: "50%", delay: 0.8 },
  { left: "34%", top: "66%", delay: 0.2 },
  { left: "60%", top: "78%", delay: 1.1 },
] as const;

const reboundThoughts = [
  { text: "and then again", left: "16%", top: "18%", delay: 0.4 },
  { text: "something else", left: "66%", top: "26%", delay: 1.1 },
  { text: "later", left: "24%", top: "74%", delay: 0.8 },
  { text: "one more thing", left: "58%", top: "80%", delay: 1.5 },
] as const;

function CollapseThread({
  progress,
  thread,
}: {
  progress: ReturnType<typeof useScroll>["scrollYProgress"];
  thread: (typeof threads)[number];
}) {
  const lineScale = useTransform(progress, [0.2, 0.48], [1, 0.22]);
  const lineOpacity = useTransform(progress, [0.1, 0.46], [0.16, 0]);

  return (
    <motion.div
      style={{
        left: thread.left,
        top: thread.top,
        width: thread.width,
        transform: `rotate(${thread.rotate})`,
        transformOrigin: "center center",
        scaleX: lineScale,
        opacity: lineOpacity,
      }}
      className="absolute h-px origin-center rounded-full bg-gradient-to-r from-transparent via-white/16 to-transparent"
    />
  );
}

function CollapseNode({
  progress,
  node,
  reduceMotion,
}: {
  progress: ReturnType<typeof useScroll>["scrollYProgress"];
  node: (typeof nodes)[number];
  reduceMotion: boolean | null;
}) {
  const nodeScale = useTransform(progress, [0.12, 0.46], [1, 0.42]);
  const nodeOpacity = useTransform(progress, [0.12, 0.46], [0.88, 0.1]);

  return (
    <motion.div
      animate={
        reduceMotion
          ? undefined
          : {
              scale: [1, 1.24, 1],
              opacity: [0.48, 0.9, 0.48],
            }
      }
      transition={{
        duration: 4.2,
        repeat: Number.POSITIVE_INFINITY,
        ease: "easeInOut",
        delay: node.delay,
      }}
      style={{ left: node.left, top: node.top, scale: nodeScale, opacity: nodeOpacity }}
      className="absolute h-2.5 w-2.5 rounded-full bg-[#d8e1ff]"
    />
  );
}

function CollapsingFragment({
  progress,
  fragment,
}: {
  progress: ReturnType<typeof useScroll>["scrollYProgress"];
  fragment: (typeof fragments)[number];
}) {
  const fragmentOpacity = useTransform(progress, [0.08, 0.34, 0.52], [0.72, 0.9, 0]);
  const fragmentX = useTransform(progress, [0.22, 0.52], [0, fragment.x]);
  const fragmentY = useTransform(progress, [0.22, 0.52], [0, fragment.y]);

  return (
    <motion.div
      style={{
        left: fragment.left,
        top: fragment.top,
        opacity: fragmentOpacity,
        x: fragmentX,
        y: fragmentY,
      }}
      className="absolute max-w-[12rem] text-[1rem] font-medium leading-[1.2] tracking-[-0.02em] text-slate-100/85 [text-shadow:0_0_18px_rgba(8,10,18,0.42)]"
    >
      {fragment.text}
    </motion.div>
  );
}

function ReboundThought({
  opacity,
  fragment,
  reduceMotion,
}: {
  opacity: ReturnType<typeof useScroll>["scrollYProgress"];
  fragment: (typeof reboundThoughts)[number];
  reduceMotion: boolean | null;
}) {
  return (
    <motion.div
      animate={
        reduceMotion
          ? undefined
          : {
              opacity: [0.16, 0.36, 0.16],
            }
      }
      transition={{
        duration: 6.5,
        repeat: Number.POSITIVE_INFINITY,
        ease: "easeInOut",
        delay: fragment.delay,
      }}
      style={{ left: fragment.left, top: fragment.top, opacity }}
      className="absolute text-[0.86rem] font-medium leading-[1.2] tracking-[-0.015em] text-slate-300/60"
    >
      {fragment.text}
    </motion.div>
  );
}

function CollapseLine({
  progress,
  index,
  text,
}: {
  progress: ReturnType<typeof useScroll>["scrollYProgress"];
  index: number;
  text: string;
}) {
  const start = 0.42 + index * 0.08;
  const end = start + 0.12;
  const opacity = useTransform(progress, [start, end], [0, 1]);
  const y = useTransform(progress, [start, end], [20, 0]);
  const width = ["w-[84%]", "w-[68%]", "w-[54%]"][index]!;
  const tone = ["text-white", "text-slate-300", "text-slate-500"][index]!;

  return (
    <motion.div
      style={{ opacity, y }}
      className={`relative mx-auto ${width} max-w-2xl text-center`}
    >
      <div className="absolute left-0 right-0 top-1/2 h-px -translate-y-1/2 bg-gradient-to-r from-transparent via-white/10 to-transparent" />
      <div className="relative inline-flex items-center justify-center bg-[#0f1115] px-4 sm:px-6">
        <span className={`text-[1.45rem] font-medium leading-none tracking-[-0.035em] sm:text-[2.05rem] ${tone}`}>
          {text}
        </span>
      </div>
    </motion.div>
  );
}

export default function ResetCollapseScene({ lines }: ResetCollapseSceneProps) {
  const ref = useRef<HTMLDivElement | null>(null);
  const offsets = useStoryFocusOffsets();
  const reduceMotion = useReducedMotion();
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: [...offsets.scene],
  });

  const fieldScale = useTransform(scrollYProgress, [0, 0.24, 0.5], [0.94, 1.06, 0.84]);
  const fieldOpacity = useTransform(scrollYProgress, [0, 0.24, 0.52, 0.78], [0.35, 1, 0.52, 0.18]);
  const fieldY = useTransform(scrollYProgress, [0, 0.24, 0.52], [36, 0, -18]);
  const headlineOpacity = useTransform(scrollYProgress, [0, 0.14, 0.36], [0.2, 1, 0.96]);
  const headlineY = useTransform(scrollYProgress, [0, 0.18], [20, 0]);
  const reboundOpacity = useTransform(scrollYProgress, [0.76, 0.94], [0, 0.42]);
  const centerBurstOpacity = useTransform(scrollYProgress, [0.28, 0.52], [0, 0.55]);
  const centerBurstScale = useTransform(scrollYProgress, [0.28, 0.52], [0.4, 1.4]);

  return (
    <div ref={ref} className="mx-auto flex w-full max-w-6xl flex-col items-center text-center">
      <motion.h2
        style={{ opacity: headlineOpacity, y: headlineY }}
        className="mx-auto max-w-[12ch] text-4xl font-semibold leading-[1.02] tracking-[-0.05em] text-white sm:text-5xl lg:text-6xl"
      >
        So everything resets.
      </motion.h2>

      <motion.div
        style={{ opacity: fieldOpacity, scale: fieldScale, y: fieldY }}
        className="relative mt-12 w-full max-w-5xl will-change-transform"
      >
        <div className="relative mx-auto aspect-[16/10] w-full overflow-hidden rounded-[44px] bg-[radial-gradient(circle_at_20%_20%,rgba(95,118,180,0.16),transparent_36%),radial-gradient(circle_at_80%_16%,rgba(184,201,255,0.08),transparent_28%),linear-gradient(180deg,rgba(14,17,24,0.82),rgba(10,12,18,0.92))]">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,transparent_48%,rgba(7,9,14,0.28)_76%,rgba(7,9,14,0.7)_100%)]" />

          {threads.map((thread) => (
            <CollapseThread
              key={`${thread.left}-${thread.top}`}
              progress={scrollYProgress}
              thread={thread}
            />
          ))}

          {nodes.map((node) => (
            <CollapseNode
              key={`${node.left}-${node.top}`}
              progress={scrollYProgress}
              node={node}
              reduceMotion={reduceMotion}
            />
          ))}

          {fragments.map((fragment) => (
            <CollapsingFragment
              key={fragment.text}
              progress={scrollYProgress}
              fragment={fragment}
            />
          ))}

          <motion.div
            style={{ opacity: centerBurstOpacity, scale: centerBurstScale }}
            className="absolute left-1/2 top-1/2 h-48 w-48 -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/10 bg-white/[0.02] blur-[1px]"
          />

          <div className="absolute inset-0 flex flex-col items-center justify-center gap-8 px-8">
            {lines.map((line, index) => (
              <CollapseLine key={line} progress={scrollYProgress} index={index} text={line} />
            ))}
          </div>

          {reboundThoughts.map((fragment) => (
            <ReboundThought
              key={fragment.text}
              opacity={reboundOpacity}
              fragment={fragment}
              reduceMotion={reduceMotion}
            />
          ))}
        </div>
      </motion.div>
    </div>
  );
}
