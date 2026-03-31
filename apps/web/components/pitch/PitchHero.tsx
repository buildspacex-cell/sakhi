"use client";

import { useEffect, useRef, useState } from "react";
import StoryContainer from "@/components/story/StoryContainer";

export function PitchHero() {
  const [started, setStarted] = useState(false);
  const [showSkip, setShowSkip] = useState(false);
  const sectionRef = useRef<HTMLElement>(null);
  const skipTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleWatch = () => {
    setStarted(true);
    const playBtn = sectionRef.current?.querySelector<HTMLButtonElement>(
      '[aria-label="Play story"]'
    );
    if (playBtn) playBtn.click();
    skipTimerRef.current = setTimeout(() => setShowSkip(true), 5000);
  };

  const handleScrollDeck = () => {
    document.getElementById("problem")?.scrollIntoView({ behavior: "smooth" });
  };

  const handleSkip = () => {
    setShowSkip(false);
    document.getElementById("problem")?.scrollIntoView({ behavior: "smooth" });
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
      className="relative h-[100svh] w-full overflow-hidden bg-[#030b18]"
    >
      {/* StoryContainer — hidden until Watch is clicked */}
      <div
        className={`absolute inset-0 transition-opacity duration-700 [&_[aria-label='Play\\_story']]:hidden ${
          started ? "opacity-100" : "opacity-0 pointer-events-none"
        }`}
      >
        <StoryContainer />
      </div>

      {/* Hero — visible until Watch is clicked */}
      <div
        className={`absolute inset-0 z-10 flex flex-col items-center justify-center transition-opacity duration-700 ${
          started ? "opacity-0 pointer-events-none" : "opacity-100"
        }`}
      >
        {/* Background radial glow */}
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_80%_70%_at_50%_46%,rgba(30,50,100,0.55),rgba(3,11,24,0.0)_68%)]" />

        {/* Orb */}
        <div className="relative mb-28 flex items-center justify-center sm:mb-32">
          {/* Outermost ring */}
          <div className="absolute h-[460px] w-[460px] rounded-full border border-white/[0.04]" />
          {/* Middle ring */}
          <div className="absolute h-[360px] w-[360px] rounded-full border border-white/[0.07]" />
          {/* Inner ring */}
          <div className="absolute h-[270px] w-[270px] rounded-full border border-white/[0.10]" />
          {/* Core */}
          <div className="relative flex h-[196px] w-[196px] items-center justify-center rounded-full border border-[#8ab0ff]/25 bg-[radial-gradient(circle_at_38%_32%,rgba(140,183,255,0.22),rgba(80,120,210,0.14)_48%,rgba(3,11,24,0.85)_78%)] shadow-[0_0_80px_rgba(100,148,255,0.18),0_0_160px_rgba(80,120,255,0.08)]">
            {/* Inner core border */}
            <div className="pointer-events-none absolute inset-[14%] rounded-full border border-white/[0.09]" />
            <span className="relative z-10 text-[13px] font-semibold tracking-[0.42em] text-[#8ab0ff]/90">
              SAKHI
            </span>
          </div>
        </div>

        {/* Tagline */}
        <div className="relative z-10 flex flex-col items-center gap-5 px-6 text-center">
          {/* CTAs */}
          <div className="mt-5 flex flex-col items-center gap-3 sm:mt-6 sm:flex-row">
            <button
              onClick={handleWatch}
              className="flex items-center gap-2.5 rounded-full border border-white/18 bg-white/8 px-7 py-3.5 text-[13px] font-semibold text-white backdrop-blur-md transition hover:bg-white/14 hover:border-white/26"
            >
              <svg viewBox="0 0 24 24" className="h-3.5 w-3.5 translate-x-px fill-white">
                <path d="M8 6.5v11l9-5.5-9-5.5Z" />
              </svg>
              Watch the story
            </button>
            <button
              onClick={handleScrollDeck}
              className="flex items-center gap-2 rounded-full border border-white/8 bg-transparent px-7 py-3.5 text-[13px] font-semibold text-white/45 backdrop-blur-md transition hover:border-white/16 hover:text-white/75"
            >
              Scroll the deck
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

      {/* Skip to deck — appears 5s into watching */}
      <div
        className={`absolute bottom-[4.8rem] right-6 z-[100] transition-all duration-500 sm:bottom-[5.2rem] sm:right-8 ${
          started && showSkip
            ? "opacity-100 pointer-events-auto"
            : "opacity-0 pointer-events-none"
        }`}
      >
        <button
          onClick={handleSkip}
          className="flex items-center gap-2 rounded-full border border-white/10 bg-black/30 px-5 py-2.5 text-[12px] font-medium text-white/45 backdrop-blur-md transition hover:text-white/75 hover:border-white/18"
        >
          Skip to deck
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
