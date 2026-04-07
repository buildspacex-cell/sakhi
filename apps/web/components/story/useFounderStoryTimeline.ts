"use client";

import { useCallback, useEffect, useRef, useState, type RefObject } from "react";

import gsap from "gsap";

const PACE = {
  sceneFade: 0.55,
  sceneFadeLong: 0.75,
  bridgeHold: 1.2,
  lineReveal: 0.72,
  lineRevealLong: 0.82,
  shortHold: 0.75,
  mediumHold: 1.6,
  longHold: 2.4,
} as const;

export const useFounderStoryTimeline = (
  containerRef: RefObject<HTMLDivElement | null>,
  speechRef?: RefObject<((text: string) => void) | null>,
) => {
  const timelineRef = useRef<gsap.core.Timeline | null>(null);
  const [isPaused, setIsPaused] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);

  useEffect(() => {
    if (!containerRef.current) {
      return;
    }

    const ctx = gsap.context(() => {
      // Scene 7 (bridge) starts visible; 8–10 hidden
      gsap.set("#scene-7", { opacity: 1 });
      gsap.set(["#scene-8", "#scene-9"], { opacity: 0 });

      // Element initial states — founders bridge
      gsap.set(".builders-bridge-kicker", { opacity: 0, y: 14 });
      gsap.set(".builders-bridge-line", { opacity: 0, y: 22, scale: 0.985 });

      // Vidhya
      gsap.set(".founder-opening", { opacity: 0, y: 24 });
      gsap.set(".founder-detail-kicker", { opacity: 0, y: 16 });
      gsap.set(".founder-portrait", { opacity: 0, y: 20, scale: 0.98 });
      gsap.set(".founder-meta", { opacity: 0, y: 14 });
      gsap.set(".founder-arc-shell", { opacity: 0, y: 22, scale: 0.985 });
      gsap.set(".founder-arc-glow", { opacity: 0.06, scaleX: 0, transformOrigin: "left center" });
      gsap.set(".founder-arc-link", { opacity: 0.18, scaleX: 0, transformOrigin: "left center" });
      gsap.set(".founder-arc-mobile-line", { opacity: 0.08, scaleY: 0, transformOrigin: "center top" });
      gsap.set(".founder-arc-head", { opacity: 0, y: 18, filter: "blur(6px)" });
      gsap.set(".founder-arc-body", { opacity: 0, y: 18 });
      gsap.set(".founder-arc-step", { opacity: 0, y: 24 });
      gsap.set(".founder-final", { opacity: 0, y: 20 });

      // Ravi
      gsap.set(".ravi-opening", { opacity: 0, y: 24 });
      gsap.set(".ravi-detail-kicker", { opacity: 0, y: 16 });
      gsap.set(".ravi-visual", { opacity: 0, y: 20, scale: 0.98 });
      gsap.set(".ravi-meta", { opacity: 0, y: 14 });
      gsap.set(".ravi-arc-shell", { opacity: 0, y: 22, scale: 0.985 });
      gsap.set(".ravi-arc-glow", { opacity: 0.06, scaleX: 0, transformOrigin: "left center" });
      gsap.set(".ravi-arc-link", { opacity: 0.18, scaleX: 0, transformOrigin: "left center" });
      gsap.set(".ravi-arc-mobile-line", { opacity: 0.08, scaleY: 0, transformOrigin: "center top" });
      gsap.set(".ravi-arc-head", { opacity: 0, y: 18, filter: "blur(6px)" });
      gsap.set(".ravi-arc-body", { opacity: 0, y: 18 });
      gsap.set(".ravi-arc-step", { opacity: 0, y: 24 });
      gsap.set(".ravi-final", { opacity: 0, y: 20 });

      const prevPausedRef = { current: false };
      const narrate = (text: string) => {
        speechRef?.current?.(text);
      };

      const tl = gsap.timeline({
        paused: true,
        defaults: { ease: "power2.out" },
        onUpdate: () => {
          const nowPaused = tl.paused();
          if (nowPaused && !prevPausedRef.current && typeof window !== "undefined") {
            window.speechSynthesis?.cancel();
          }
          prevPausedRef.current = nowPaused;
          setProgress(tl.progress());
          setIsPaused(nowPaused);
          setIsComplete(tl.progress() >= 1);
        },
        onComplete: () => {
          setIsComplete(true);
          setIsPaused(true);
          setProgress(1);
        },
      });
      timelineRef.current = tl;
      setIsPaused(true);
      setIsComplete(false);
      setProgress(0);
      requestAnimationFrame(() => setDuration(tl.duration()));

      // ── Scene 7: Founders bridge ────────────────────────────────────────────
      tl
        .to(".builders-bridge-kicker", { opacity: 1, y: 0, duration: 0.5 })
        .to(".builders-bridge-line", { opacity: 1, y: 0, scale: 1, duration: 0.9 }, "-=0.18")
        .call(() => narrate("The minds behind."), undefined, "<")
        .to({}, { duration: 3.0 })

        // ── Scene 8: Vidhya ─────────────────────────────────────────────────
        .to("#scene-7", { opacity: 0, duration: PACE.sceneFadeLong })
        .to("#scene-8", { opacity: 1, duration: PACE.sceneFade }, "-=0.15")
        .to(".founder-portrait", { opacity: 1, y: 0, scale: 1, duration: 0.75 })
        .to(".founder-meta", { opacity: 1, y: 0, duration: 0.6 }, "-=0.42")
        .to(".founder-opening", { opacity: 1, y: 0, duration: 0.95 }, "-=0.2")
        .call(() => narrate("I've spent 20 years helping organizations make better decisions. I realized we haven't solved this for individuals."), undefined, "<")
        .to({}, { duration: 5.0 })
        .to(".founder-opening", { opacity: 0, duration: 0.5 })
        .to(".founder-detail-kicker", { opacity: 1, y: 0, duration: 0.55 }, "-=0.15")
        .to(".founder-arc-shell", { opacity: 1, y: 0, scale: 1, duration: 0.72 }, "-=0.08")
        .to(".founder-arc-glow", { opacity: 0.32, scaleX: 1, duration: 0.9 }, "-=0.38")
        .to(".founder-arc-mobile-line", { opacity: 0.72, scaleY: 1, duration: 0.82 }, "<+0.08")
        .to(".founder-arc-head-1", { opacity: 1, y: 0, filter: "blur(0px)", duration: 0.52 }, "-=0.5")
        .call(() => narrate("Operator at Scale."), undefined, "<")
        .to(".founder-arc-step-1", { opacity: 1, y: 0, duration: 0.4 }, "-=0.28")
        .to(".founder-arc-body-1", { opacity: 1, y: 0, duration: 0.56 }, "-=0.12")
        .call(() => narrate("Worked alongside CEOs and COOs, building systems that turned ambiguity into structured decisions."), undefined, "<")
        .to(".founder-arc-link-1", { opacity: 0.92, scaleX: 1, duration: 0.42 }, "+=4.5")
        .to(".founder-arc-head-2", { opacity: 1, y: 0, filter: "blur(0px)", duration: 0.52 }, "-=0.08")
        .call(() => narrate("Personal Inflection Point."), undefined, "<")
        .to(".founder-arc-step-2", { opacity: 1, y: 0, duration: 0.4 }, "-=0.2")
        .to(".founder-arc-body-2", { opacity: 1, y: 0, duration: 0.56 }, "-=0.12")
        .call(() => narrate("In 2024, caregiving, leadership, and life complexity collided. What was missing was continuity at the level of a real human life."), undefined, "<")
        .to(".founder-arc-link-2", { opacity: 0.92, scaleX: 1, duration: 0.42 }, "+=4.5")
        .to(".founder-arc-head-3", { opacity: 1, y: 0, filter: "blur(0px)", duration: 0.52 }, "-=0.08")
        .call(() => narrate("Insight to Sakhi."), undefined, "<")
        .to(".founder-arc-step-3", { opacity: 1, y: 0, duration: 0.4 }, "-=0.2")
        .to(".founder-arc-body-3", { opacity: 1, y: 0, duration: 0.56 }, "-=0.12")
        .call(() => narrate("Small, personalized interventions changed everything. The question became: can this be built as a system?"), undefined, "<")
        .to(".founder-final", { opacity: 1, y: 0, duration: 0.8 }, "+=4.5")
        .call(() => narrate("Sakhi is the system I wish existed when I needed it most."), undefined, "<")
        .to({}, { duration: 3.5 })

        // ── Scene 9: Ravi ────────────────────────────────────────────────────
        .to("#scene-8", { opacity: 0, duration: PACE.sceneFadeLong, delay: PACE.shortHold })
        .to("#scene-9", { opacity: 1, duration: PACE.sceneFade }, "-=0.15")
        .to(".ravi-visual", { opacity: 1, y: 0, scale: 1, duration: 0.75 })
        .to(".ravi-meta", { opacity: 1, y: 0, duration: 0.6 }, "-=0.42")
        .to(".ravi-opening", { opacity: 1, y: 0, duration: 1 }, "-=0.2")
        .call(() => narrate("I'm a systems thinker at heart, grounded in deep technical expertise and driven to simplify complexity."), undefined, "<")
        .to({}, { duration: 5.0 })
        .to(".ravi-opening", { opacity: 0, duration: 0.5 })
        .to(".ravi-detail-kicker", { opacity: 1, y: 0, duration: 0.55 }, "-=0.15")
        .to(".ravi-arc-shell", { opacity: 1, y: 0, scale: 1, duration: 0.72 }, "-=0.08")
        .to(".ravi-arc-glow", { opacity: 0.32, scaleX: 1, duration: 0.9 }, "-=0.38")
        .to(".ravi-arc-mobile-line", { opacity: 0.72, scaleY: 1, duration: 0.82 }, "<+0.08")
        .to(".ravi-arc-head-1", { opacity: 1, y: 0, filter: "blur(0px)", duration: 0.52 }, "-=0.5")
        .call(() => narrate("Evolution."), undefined, "<")
        .to(".ravi-arc-step-1", { opacity: 1, y: 0, duration: 0.4 }, "-=0.28")
        .to(".ravi-arc-body-1", { opacity: 1, y: 0, duration: 0.56 }, "-=0.12")
        .call(() => narrate("I started with engineering, building systems and applications, then kept moving closer to the question of what actually makes systems work."), undefined, "<")
        .to(".ravi-arc-link-1", { opacity: 0.92, scaleX: 1, duration: 0.42 }, "+=4.5")
        .to(".ravi-arc-head-2", { opacity: 1, y: 0, filter: "blur(0px)", duration: 0.52 }, "-=0.08")
        .call(() => narrate("Realization."), undefined, "<")
        .to(".ravi-arc-step-2", { opacity: 1, y: 0, duration: 0.4 }, "-=0.2")
        .to(".ravi-arc-body-2", { opacity: 1, y: 0, duration: 0.56 }, "-=0.12")
        .call(() => narrate("Systems do not succeed just because they are built well. They succeed because people understand them, trust them, and use them."), undefined, "<")
        .to(".ravi-arc-link-2", { opacity: 0.92, scaleX: 1, duration: 0.42 }, "+=4.5")
        .to(".ravi-arc-head-3", { opacity: 1, y: 0, filter: "blur(0px)", duration: 0.52 }, "-=0.08")
        .call(() => narrate("Expansion."), undefined, "<")
        .to(".ravi-arc-step-3", { opacity: 1, y: 0, duration: 0.4 }, "-=0.2")
        .to(".ravi-arc-body-3", { opacity: 1, y: 0, duration: 0.56 }, "-=0.12")
        .call(() => narrate("That pulled me across engineering, product, and product marketing, while yoga and meditation deepened how I think about human behavior over time."), undefined, "<")
        .to(".ravi-arc-link-3", { opacity: 0.92, scaleX: 1, duration: 0.42 }, "+=4.5")
        .to(".ravi-arc-head-4", { opacity: 1, y: 0, filter: "blur(0px)", duration: 0.52 }, "-=0.08")
        .call(() => narrate("Convergence."), undefined, "<")
        .to(".ravi-arc-step-4", { opacity: 1, y: 0, duration: 0.4 }, "-=0.2")
        .to(".ravi-arc-body-4", { opacity: 1, y: 0, duration: 0.56 }, "-=0.08")
        .call(() => narrate("Technical depth, systems thinking, product narrative, and lived understanding of people now converge in building Sakhi."), undefined, "<")
        .to(".ravi-final", { opacity: 1, y: 0, duration: 0.8 }, "+=4.8")
        .call(() => narrate("That gives me the clarity to build Sakhi."), undefined, "<")
        .to({}, { duration: 3.5 });
    }, containerRef);

    return () => {
      timelineRef.current = null;
      ctx.revert();
    };
  }, [containerRef, speechRef]);

  const togglePlayback = useCallback(() => {
    const timeline = timelineRef.current;
    if (!timeline) return;
    if (timeline.progress() >= 1) {
      timeline.restart();
      setIsComplete(false);
    } else {
      timeline.paused() ? timeline.play() : timeline.pause();
    }
    setIsPaused(timeline.paused());
  }, []);

  const restart = useCallback(() => {
    const timeline = timelineRef.current;
    if (!timeline) return;
    timeline.restart();
    setIsComplete(false);
    setIsPaused(false);
  }, []);

  const seekTo = useCallback((progress: number) => {
    const timeline = timelineRef.current;
    if (!timeline) return;
    timeline.progress(progress);
    if (timeline.paused()) {
      setProgress(progress);
    }
  }, []);

  return { isPaused, isComplete, progress, duration, togglePlayback, restart, seekTo };
};
