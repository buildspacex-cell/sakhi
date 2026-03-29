"use client";

import { useRef } from "react";
import Image from "next/image";
import { motion, useScroll, useTransform } from "framer-motion";
import useStoryFocusOffsets from "@/components/story/useStoryFocusOffsets";

type ProductScene = {
  eyebrow: string;
  title: string;
  description: string;
  caption: string;
  imageSrc: string;
};

type ProductFlowSectionProps = {
  scenes: ReadonlyArray<ProductScene>;
};

function ProductSceneCard({
  scene,
  index,
}: {
  scene: ProductScene;
  index: number;
}) {
  const cardRef = useRef<HTMLElement | null>(null);
  const offsets = useStoryFocusOffsets();
  const { scrollYProgress } = useScroll({
    target: cardRef,
    offset: [...offsets.card],
  });

  const opacity = useTransform(scrollYProgress, [0.04, 0.28, 0.9, 1], [0.2, 1, 1, 0.6]);
  const y = useTransform(scrollYProgress, [0.04, 0.28, 0.9, 1], [36, 0, -10, -18]);
  const imageY = useTransform(scrollYProgress, [0, 1], [52, -52]);
  const glowY = useTransform(scrollYProgress, [0, 1], [24, -20]);

  return (
    <motion.article
      ref={cardRef}
      style={{ opacity, y }}
      className="group overflow-hidden rounded-[32px] border border-white/10 bg-[linear-gradient(180deg,rgba(18,23,33,0.92),rgba(10,13,20,0.96))] shadow-panel"
    >
      <div className="border-b border-white/8 px-6 py-5 sm:px-7">
        <div className="text-[11px] font-semibold uppercase tracking-[0.32em] text-slate-400">
          {scene.eyebrow}
        </div>
        <h3 className="mt-3 text-2xl font-semibold tracking-[-0.04em] text-white sm:text-[2rem]">
          {scene.title}
        </h3>
        <p className="mt-3 max-w-md text-sm leading-7 text-slate-300 sm:text-base">
          {scene.description}
        </p>
      </div>

      <div className="grid gap-5 px-6 py-6 sm:px-7 sm:py-7 md:grid-cols-[minmax(0,188px)_minmax(0,1fr)] md:items-center">
        <div className="relative mx-auto w-full max-w-[188px]">
          <motion.div
            style={{ y: glowY }}
            className="absolute inset-0 rounded-[32px] bg-[#89a6ff]/12 blur-2xl"
          />
          <motion.div
            style={{ y: imageY }}
            className="relative overflow-hidden rounded-[32px] border border-white/10 bg-[#0a0d13] p-2 shadow-[0_36px_90px_rgba(0,0,0,0.48)]"
          >
            <div className="rounded-[24px] border border-white/6 bg-[#05070b] p-1">
              <Image
                src={scene.imageSrc}
                alt={scene.title}
                width={432}
                height={874}
                className="h-auto w-full rounded-[20px]"
                priority={index < 2}
              />
            </div>
          </motion.div>
        </div>

        <div className="space-y-4">
          <div className="inline-flex items-center rounded-full border border-[#90a8ff]/20 bg-[#90a8ff]/8 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.28em] text-[#c8d6ff]">
            Product frame {String(index + 1).padStart(2, "0")}
          </div>
          <p className="max-w-sm text-base leading-8 text-slate-200 sm:text-lg">
            {scene.caption}
          </p>
        </div>
      </div>
    </motion.article>
  );
}

export default function ProductFlowSection({
  scenes,
}: ProductFlowSectionProps) {
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      {scenes.map((scene, index) => (
        <ProductSceneCard key={scene.title} scene={scene} index={index} />
      ))}
    </div>
  );
}
