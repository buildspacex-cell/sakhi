"use client";

import type { ReactNode } from "react";
import { useRef } from "react";

import { motion, useScroll, useTransform } from "framer-motion";
import useStoryFocusOffsets from "@/components/story/useStoryFocusOffsets";

type ScrollSceneProps = {
  children: ReactNode;
  className?: string;
  fromY?: number;
  toY?: number;
};

export default function ScrollScene({
  children,
  className = "",
  fromY = 52,
  toY = -34,
}: ScrollSceneProps) {
  const ref = useRef<HTMLDivElement | null>(null);
  const offsets = useStoryFocusOffsets();
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: [...offsets.scene],
  });

  const opacity = useTransform(
    scrollYProgress,
    [0, 0.18, 0.78, 1],
    [0.12, 1, 1, 0.16],
  );
  const y = useTransform(
    scrollYProgress,
    [0, 0.2, 0.8, 1],
    [fromY, 0, toY * 0.45, toY],
  );
  const scale = useTransform(
    scrollYProgress,
    [0, 0.2, 0.8, 1],
    [0.988, 1, 1, 0.994],
  );

  return (
    <motion.div ref={ref} style={{ opacity, y, scale }} className={className}>
      {children}
    </motion.div>
  );
}
