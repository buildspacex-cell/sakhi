"use client";

import { useEffect, useRef, useState } from "react";

import StoryContainer from "@/components/story/StoryContainer";

export function PitchHero({ onOpenPresentation }: { onOpenPresentation?: () => void }) {
  const sectionRef = useRef<HTMLElement>(null);
  const skipTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [mode, setMode] = useState<"entry" | "video">("entry");
  const [showSkip, setShowSkip] = useState(false);

  const handleWatch = () => {
    setMode("video");
    setShowSkip(false);

    requestAnimationFrame(() => {
      const playBtn = sectionRef.current?.querySelector<HTMLButtonElement>('[aria-label="Play story"]');
      if (playBtn) playBtn.click();
    });

    skipTimerRef.current = setTimeout(() => setShowSkip(true), 5000);
  };

  const handleOpenDeck = () => {
    if (skipTimerRef.current) clearTimeout(skipTimerRef.current);
    setShowSkip(false);
    onOpenPresentation?.();
  };

  const handleSkip = () => {
    if (skipTimerRef.current) clearTimeout(skipTimerRef.current);
    setShowSkip(false);
    onOpenPresentation?.();
  };

  useEffect(() => {
    return () => {
      if (skipTimerRef.current) clearTimeout(skipTimerRef.current);
    };
  }, []);

  return (
    <section
      id="hero"
      ref={sectionRef}
      className="relative h-[100svh] w-full overflow-hidden border-t border-white/[0.06] bg-[#020617]"
    >
      <div
        className={`absolute inset-0 transition-opacity duration-700 [&_[aria-label='Play\\_story']]:hidden ${
          mode === "video" ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
      >
        <StoryContainer />
      </div>

      <div
        className={`absolute inset-0 z-10 flex flex-col items-center justify-center transition-opacity duration-700 ${
          mode === "entry" ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
      >
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_80%_70%_at_50%_46%,rgba(30,50,100,0.55),rgba(3,11,24,0.0)_68%)]" />

        <div className="relative mb-28 flex items-center justify-center sm:mb-32">
          <div className="absolute h-[460px] w-[460px] rounded-full border border-white/[0.04]" />
          <div className="absolute h-[360px] w-[360px] rounded-full border border-white/[0.07]" />
          <div className="absolute h-[270px] w-[270px] rounded-full border border-white/[0.10]" />
          <div className="relative flex h-[196px] w-[196px] items-center justify-center rounded-full border border-[#8ab0ff]/25 bg-[radial-gradient(circle_at_38%_32%,rgba(140,183,255,0.22),rgba(80,120,210,0.14)_48%,rgba(3,11,24,0.85)_78%)] shadow-[0_0_80px_rgba(100,148,255,0.18),0_0_160px_rgba(80,120,255,0.08)]">
            <div className="pointer-events-none absolute inset-[14%] rounded-full border border-white/[0.09]" />
            <span className="relative z-10 text-[13px] font-semibold tracking-[0.42em] text-[#8ab0ff]/90">
              SAKHI
            </span>
          </div>
        </div>

        <div className="relative z-10 flex flex-col items-center gap-5 px-6 text-center">
          <div className="mt-5 flex flex-col items-center gap-3 sm:mt-6 sm:flex-row">
            <button
              type="button"
              onClick={handleWatch}
              className="flex items-center gap-2.5 rounded-full border border-white/18 bg-white/8 px-7 py-3.5 text-[13px] font-semibold text-white backdrop-blur-md transition hover:border-white/26 hover:bg-white/14"
            >
              <svg viewBox="0 0 24 24" className="h-3.5 w-3.5 translate-x-px fill-white">
                <path d="M8 6.5v11l9-5.5-9-5.5Z" />
              </svg>
              Watch the story
            </button>
            <button
              type="button"
              onClick={handleOpenDeck}
              className="flex items-center gap-2 rounded-full border border-white/8 bg-transparent px-7 py-3.5 text-[13px] font-semibold text-white/45 backdrop-blur-md transition hover:border-white/16 hover:text-white/75"
            >
              Open deck
              <svg
                viewBox="0 0 24 24"
                className="h-3.5 w-3.5 fill-none stroke-current"
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M6 9l6 6 6-6" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      <div
        className={`absolute bottom-[4.8rem] right-6 z-[100] transition-all duration-500 sm:bottom-[5.2rem] sm:right-8 ${
          mode === "video" && showSkip ? "pointer-events-auto opacity-100" : "pointer-events-none opacity-0"
        }`}
      >
        <button
          type="button"
          onClick={handleSkip}
          className="flex items-center gap-2 rounded-full border border-white/10 bg-black/30 px-5 py-2.5 text-[12px] font-medium text-white/45 backdrop-blur-md transition hover:border-white/18 hover:text-white/75"
        >
          Open deck
          <svg
            viewBox="0 0 24 24"
            className="h-3.5 w-3.5 fill-none stroke-current"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M6 9l6 6 6-6" />
          </svg>
        </button>
      </div>
    </section>
  );
}
