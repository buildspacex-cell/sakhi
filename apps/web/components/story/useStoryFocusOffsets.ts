"use client";

import { useEffect, useState } from "react";

type StoryFocusOffsets = {
  intro: StoryOffsetPair;
  scene: StoryOffsetPair;
  card: StoryOffsetPair;
  loop: StoryOffsetPair;
  phase: StoryOffsetPair;
};

type StoryOffsetPair = readonly [`start ${number}%`, `end ${number}%`];

const DESKTOP_OFFSETS = {
  intro: ["start 28%", "end 28%"],
  scene: ["start 70%", "end 34%"],
  card: ["start 72%", "end 34%"],
  loop: ["start 70%", "end 34%"],
  phase: ["start 70%", "end 34%"],
} as const satisfies StoryFocusOffsets;

const TABLET_OFFSETS = {
  intro: ["start 30%", "end 30%"],
  scene: ["start 68%", "end 36%"],
  card: ["start 70%", "end 36%"],
  loop: ["start 68%", "end 36%"],
  phase: ["start 68%", "end 36%"],
} as const satisfies StoryFocusOffsets;

const MOBILE_OFFSETS = {
  intro: ["start 32%", "end 32%"],
  scene: ["start 66%", "end 38%"],
  card: ["start 68%", "end 38%"],
  loop: ["start 66%", "end 38%"],
  phase: ["start 66%", "end 38%"],
} as const satisfies StoryFocusOffsets;

function resolveOffsets(): StoryFocusOffsets {
  if (typeof window === "undefined") {
    return DESKTOP_OFFSETS;
  }

  if (window.matchMedia("(max-width: 767px), (pointer: coarse)").matches) {
    return MOBILE_OFFSETS;
  }

  if (window.matchMedia("(max-width: 1100px)").matches) {
    return TABLET_OFFSETS;
  }

  return DESKTOP_OFFSETS;
}

export default function useStoryFocusOffsets(): StoryFocusOffsets {
  const [offsets, setOffsets] = useState<StoryFocusOffsets>(DESKTOP_OFFSETS);

  useEffect(() => {
    const updateOffsets = () => {
      setOffsets(resolveOffsets());
    };

    updateOffsets();
    window.addEventListener("resize", updateOffsets);

    return () => {
      window.removeEventListener("resize", updateOffsets);
    };
  }, []);

  return offsets;
}
