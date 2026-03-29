"use client";

import { useRef } from "react";

import { motion, useScroll, useTransform } from "framer-motion";
import ExpandableSection from "@/components/story/ExpandableSection";
import useStoryFocusOffsets from "@/components/story/useStoryFocusOffsets";

type ArchitecturePillar = {
  system: string;
  stage?: string;
  title: string;
  summary: string;
  existsNow: readonly string[];
  visionHolds: readonly string[];
  mvpFeatures: readonly string[];
  visionFeatures: readonly string[];
  captures: readonly string[];
  builds: readonly string[];
  computes: readonly string[];
  surfaces: readonly string[];
  visionOnly?: boolean;
};

type ArchitectureSectionProps = {
  pillars: readonly ArchitecturePillar[];
};

function PresentLayerCard({
  progress,
  pillar,
  index,
}: {
  progress: ReturnType<typeof useScroll>["scrollYProgress"];
  pillar: ArchitecturePillar;
  index: number;
}) {
  const start = 0.02 + index * 0.08;
  const peak = start + 0.14;
  const end = peak + 0.12;

  const opacity = useTransform(progress, [start, peak, end], [0.24, 1, 0.92]);
  const y = useTransform(progress, [start, peak, end], [24, 0, -4]);

  return (
    <motion.article
      style={{ opacity, y }}
      className="rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(18,23,32,0.92),rgba(12,15,22,0.96))] p-6 shadow-panel"
    >
      <div className="text-[11px] font-semibold uppercase tracking-[0.3em] text-slate-400">
        {pillar.system}
      </div>
      {pillar.stage ? (
        <div className="mt-2 text-[10px] font-semibold uppercase tracking-[0.26em] text-[#c4d2ff]">
          {pillar.stage}
        </div>
      ) : null}

      <h3 className="mt-4 max-w-[15ch] text-[1.8rem] font-semibold leading-[1.04] tracking-[-0.045em] text-white">
        {pillar.title}
      </h3>
      <p className="mt-4 max-w-[34ch] text-sm leading-7 text-slate-300">
        {pillar.summary}
      </p>

      <div className="mt-6 border-t border-white/8 pt-5">
        <div className="text-[10px] font-semibold uppercase tracking-[0.26em] text-slate-400">
          In the MVP now
        </div>
        <div className="mt-3 space-y-2">
          {pillar.existsNow.map((item) => (
            <div key={item} className="text-sm leading-6 text-slate-200">
              {item}
            </div>
          ))}
        </div>
      </div>

      <div className="mt-5 rounded-[22px] border border-white/8 bg-white/[0.02] p-4">
        <div className="text-[10px] font-semibold uppercase tracking-[0.26em] text-slate-400">
          Feature layer now
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {pillar.mvpFeatures.map((item) => (
            <div
              key={item}
              className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-[0.8rem] leading-none text-slate-200"
            >
              {item}
            </div>
          ))}
        </div>
      </div>
    </motion.article>
  );
}

function ArchitectureCard({
  progress,
  pillar,
  index,
  visionOnly = false,
}: {
  progress: ReturnType<typeof useScroll>["scrollYProgress"];
  pillar: ArchitecturePillar;
  index: number;
  visionOnly?: boolean;
}) {
  const start = 0.08 + index * 0.1;
  const peak = start + 0.14;
  const end = peak + 0.14;

  const opacity = useTransform(progress, [start, peak, end], [0.18, 1, 0.9]);
  const y = useTransform(progress, [start, peak, end], [26, 0, -6]);

  return (
    <motion.article
      style={{ opacity, y }}
      className="h-full"
    >
      <ExpandableSection
        system={pillar.system}
        stage={pillar.stage}
        title={pillar.title}
        summary={pillar.summary}
        existsNow={pillar.existsNow}
        visionHolds={pillar.visionHolds}
        featureTitle={visionOnly || pillar.visionOnly ? "Feature direction" : "Feature layer"}
        featureItems={visionOnly || pillar.visionOnly ? pillar.visionFeatures : pillar.mvpFeatures}
        visionOnly={visionOnly || pillar.visionOnly}
        details={[
          { title: "Captures", items: pillar.captures },
          { title: "Builds", items: pillar.builds },
          { title: "Understands", items: pillar.computes },
          { title: "Shows", items: pillar.surfaces },
        ]}
      />
    </motion.article>
  );
}

export default function ArchitectureSection({
  pillars,
}: ArchitectureSectionProps) {
  const ref = useRef<HTMLElement | null>(null);
  const offsets = useStoryFocusOffsets();
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: [...offsets.phase],
  });

  const headerOpacity = useTransform(scrollYProgress, [0, 0.16], [0.18, 1]);
  const headerY = useTransform(scrollYProgress, [0, 0.16], [22, 0]);
  const summaryOpacity = useTransform(scrollYProgress, [0.2, 0.4], [0.15, 1]);
  const bridgeOpacity = useTransform(scrollYProgress, [0.28, 0.44], [0.12, 1]);
  const bridgeY = useTransform(scrollYProgress, [0.28, 0.44], [22, 0]);
  const visionOpacity = useTransform(scrollYProgress, [0.42, 0.58], [0.14, 1]);
  const presentPillars = pillars.filter((pillar) => !pillar.visionOnly);

  return (
    <section ref={ref} className="space-y-8">
      <div className="max-w-4xl">
        <motion.div
          style={{ opacity: headerOpacity, y: headerY }}
          className="text-[11px] font-semibold uppercase tracking-[0.32em] text-slate-400"
        >
          Product architecture
        </motion.div>
        <motion.h2
          style={{ opacity: headerOpacity, y: headerY }}
          className="mt-4 max-w-[13ch] text-4xl font-semibold leading-[1.02] tracking-[-0.05em] text-white sm:text-5xl lg:text-6xl"
        >
          Today&apos;s MVP is Sakhi and Kala working together.
        </motion.h2>
        <motion.p
          style={{ opacity: summaryOpacity }}
          className="mt-5 max-w-3xl text-base leading-8 text-slate-300 sm:text-lg"
        >
          The product that exists now is not three disconnected ideas. Sakhi
          listens, converses, senses, and surfaces. Kala connects moments
          across time, preserves continuity, and turns lived history into
          structure. Together, they create the current product.
        </motion.p>
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        {presentPillars.map((pillar, index) => (
          <PresentLayerCard
            key={`${pillar.system}-present`}
            progress={scrollYProgress}
            pillar={pillar}
            index={index}
          />
        ))}
      </div>

      <motion.div
        style={{ opacity: bridgeOpacity, y: bridgeY }}
        className="mx-auto max-w-4xl rounded-[30px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,19,27,0.78),rgba(11,14,20,0.88))] px-6 py-8 text-center"
      >
        <div className="text-[11px] font-semibold uppercase tracking-[0.32em] text-slate-500">
          What this means
        </div>
        <p className="mx-auto mt-4 max-w-3xl text-[1.18rem] leading-8 tracking-[-0.02em] text-slate-100 sm:text-[1.35rem]">
          Sakhi receives and returns the experience. Kala preserves and links
          the life behind it. That is the current MVP. From there, the system
          can expand into a fuller architecture.
        </p>
      </motion.div>

      <div className="max-w-4xl pt-6">
        <motion.div
          style={{ opacity: visionOpacity }}
          className="text-[11px] font-semibold uppercase tracking-[0.32em] text-slate-400"
        >
          Vision direction
        </motion.div>
        <motion.h3
          style={{ opacity: visionOpacity }}
          className="mt-4 max-w-[13ch] text-3xl font-semibold leading-[1.04] tracking-[-0.04em] text-white sm:text-4xl lg:text-5xl"
        >
          Then the system opens into three layers.
        </motion.h3>
        <motion.p
          style={{ opacity: visionOpacity }}
          className="mt-4 max-w-3xl text-base leading-8 text-slate-300 sm:text-lg"
        >
          Once the MVP is understood, the full shape becomes clearer. Sakhi
          remains the listening and sensing layer. Kala remains the continuity
          engine. Karma becomes the action layer that connects outward and
          feeds outcomes back into continuity.
        </motion.p>
      </div>

      <div className="grid gap-5 xl:grid-cols-3">
        {pillars.map((pillar, index) => (
          <ArchitectureCard
            key={pillar.system}
            progress={scrollYProgress}
            pillar={pillar}
            index={index + presentPillars.length}
            visionOnly
          />
        ))}
      </div>
    </section>
  );
}
