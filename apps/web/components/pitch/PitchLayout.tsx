"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { PitchNav, pitchSections } from "@/components/pitch/PitchNav";
import { PitchHero } from "@/components/pitch/PitchHero";
import { PitchPresentation } from "@/components/pitch/PitchPresentation";
import { PitchProblem } from "@/components/pitch/PitchProblem";
import { PitchSolution } from "@/components/pitch/PitchSolution";
import { PitchContinuity } from "@/components/pitch/PitchContinuity";
import { PitchProduct } from "@/components/pitch/PitchProduct";
import { PitchVision } from "@/components/pitch/PitchVision";
import { PitchFounderBridge } from "@/components/pitch/PitchFounderBridge";
import { PitchTeam } from "@/components/pitch/PitchTeam";
import { PitchAsk } from "@/components/pitch/PitchAsk";

export function PitchLayout() {
  const [activeId, setActiveId] = useState<string>("hero");
  const [isPresentationOpen, setIsPresentationOpen] = useState(false);

  useEffect(() => {
    const observers: IntersectionObserver[] = [];
    const visibilityMap: Record<string, number> = {};

    pitchSections.forEach(({ id }) => {
      const element = document.getElementById(id);
      if (!element) return;

      const observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            visibilityMap[id] = entry.intersectionRatio;
          });

          let maxRatio = 0;
          let mostVisible = "hero";
          for (const [sectionId, ratio] of Object.entries(visibilityMap)) {
            if (ratio > maxRatio) {
              maxRatio = ratio;
              mostVisible = sectionId;
            }
          }

          setActiveId(mostVisible);
        },
        {
          threshold: [0, 0.1, 0.25, 0.5, 0.75, 1],
          rootMargin: "-10% 0px -10% 0px",
        },
      );

      observer.observe(element);
      observers.push(observer);
    });

    return () => {
      observers.forEach((observer) => observer.disconnect());
    };
  }, []);

  const scrollToSection = useCallback((id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
  }, []);

  const activeIndex = useMemo(
    () => Math.max(0, pitchSections.findIndex((section) => section.id === activeId)),
    [activeId],
  );

  const goPrevious = useCallback(() => {
    if (activeIndex <= 0) return;
    scrollToSection(pitchSections[activeIndex - 1].id);
  }, [activeIndex, scrollToSection]);

  const goNext = useCallback(() => {
    if (activeIndex >= pitchSections.length - 1) return;
    scrollToSection(pitchSections[activeIndex + 1].id);
  }, [activeIndex, scrollToSection]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        goPrevious();
      }

      if (event.key === "ArrowRight") {
        event.preventDefault();
        goNext();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [goNext, goPrevious]);

  return (
    <div className="relative bg-[#020617] text-white [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
      <PitchNav activeId={activeId} onSelect={scrollToSection} />
      <PitchHero onOpenPresentation={() => setIsPresentationOpen(true)} />
      <PitchPresentation open={isPresentationOpen} onClose={() => setIsPresentationOpen(false)} />
      <PitchProblem />
      <PitchSolution />
      <PitchContinuity />
      <PitchProduct />
      <PitchVision />
      <PitchFounderBridge />
      <PitchTeam />
      <PitchAsk />
      <button
        type="button"
        onClick={goPrevious}
        aria-label="Previous section"
        disabled={activeIndex === 0}
        className={`fixed bottom-5 left-5 z-[70] flex h-14 w-14 items-center justify-center rounded-full border backdrop-blur-md transition sm:bottom-7 sm:left-7 ${
          activeIndex === 0
            ? "cursor-not-allowed border-white/8 bg-[#020617]/30 text-white/20"
            : "border-white/12 bg-[#020617]/76 text-white/78 shadow-[0_18px_40px_rgba(0,0,0,0.28)] hover:border-white/20 hover:bg-[#08111f]/92 hover:text-white"
        }`}
      >
        <svg
          aria-hidden="true"
          viewBox="0 0 24 24"
          className="h-5 w-5 fill-none stroke-current"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M15 18l-6-6 6-6" />
        </svg>
      </button>
      <button
        type="button"
        onClick={goNext}
        aria-label="Next section"
        disabled={activeIndex === pitchSections.length - 1}
        className={`fixed bottom-5 right-5 z-[70] flex h-14 w-14 items-center justify-center rounded-full border backdrop-blur-md transition sm:bottom-7 sm:right-7 ${
          activeIndex === pitchSections.length - 1
            ? "cursor-not-allowed border-white/8 bg-[#020617]/30 text-white/20"
            : "border-white/12 bg-[#020617]/76 text-white/78 shadow-[0_18px_40px_rgba(0,0,0,0.28)] hover:border-white/20 hover:bg-[#08111f]/92 hover:text-white"
        }`}
      >
        <svg
          aria-hidden="true"
          viewBox="0 0 24 24"
          className="h-5 w-5 fill-none stroke-current"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M9 6l6 6-6 6" />
        </svg>
      </button>
    </div>
  );
}
