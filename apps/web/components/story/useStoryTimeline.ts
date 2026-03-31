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

export const useStoryTimeline = (
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
      gsap.set("#scene-1", { opacity: 1 });
      gsap.set(["#scene-2", "#scene-3", "#scene-4", "#scene-5", "#scene-6", "#scene-7", "#scene-8", "#scene-9", "#scene-10"], {
        opacity: 0,
      });
      gsap.set(".thought-field", { opacity: 0.42, scale: 0.96 });
      gsap.set(".thought-vignette", { opacity: 0.92 });
      gsap.set(".thought", { opacity: 0, scale: 0.75, filter: "blur(0px)" });
      gsap.set(".thought-transient", { opacity: 0, y: 12, scale: 0.94 });
      gsap.set(".blip-marker", { scale: 0.5, opacity: 0 });
      gsap.set(".intro-sequence", { opacity: 0 });
      gsap.set(".sakhi-bridge", { opacity: 0 });
      gsap.set(".sakhi-bridge-line", { opacity: 0, y: 18 });
      gsap.set(".intro-line-1", { opacity: 0, y: 0, scale: 1 });
      gsap.set(".intro-line-2", { opacity: 0, y: 24, scale: 0.982 });
      gsap.set(".intro-explainer", { opacity: 0, y: 28 });
      gsap.set(".intro-system", { opacity: 0, y: 28 });
      gsap.set(".intro-active", { opacity: 0, scale: 0.992, x: "3vw" });
      gsap.set(".intro-parked", { opacity: 0, y: 10, scale: 0.985 });
      gsap.set(".intro-parked-row", { opacity: 1, y: 0 });
      gsap.set(".intro-progress-wrap", { opacity: 1, y: 0 });
      gsap.set(".intro-progress", { scaleX: 0.3 });
      gsap.set(".intro-resolved", { opacity: 0.18, y: 110, scale: 0.94 });
      gsap.set(".intro-resolved-item", { opacity: 0.45, y: 0 });
      gsap.set(".continuity-copy", { opacity: 0, y: 24 });
      gsap.set(".continuity-visual", { opacity: 1, scale: 1 });
      gsap.set(".continuity-noise-field", { opacity: 1 });
      gsap.set(".continuity-noise-item", {
        x: (_index, element) => Number((element as HTMLElement).dataset.x || 0),
        y: (_index, element) => Number((element as HTMLElement).dataset.y || 0),
        opacity: 0.88,
        scale: 1,
      });
      gsap.set(".continuity-core-wrap", { opacity: 1 });
      gsap.set(".continuity-core-shell", { opacity: 0, scale: 0.72 });
      gsap.set(".continuity-core-ring", { opacity: 0.18, scale: 0.76, transformOrigin: "center center" });
      gsap.set(".continuity-core-label", { opacity: 0, y: 10 });
      gsap.set(".continuity-output-stage", { opacity: 0, y: 26 });
      gsap.set(".continuity-occupancy-board", { opacity: 0, y: 26, scale: 0.97 });
      gsap.set(".continuity-occupancy-header", { opacity: 0, y: 12 });
      gsap.set(".continuity-occupancy-shell", { opacity: 0, y: 16 });
      gsap.set(".continuity-occupancy-copy", { opacity: 0, y: 12 });
      gsap.set(".continuity-occupancy-bubble", { opacity: 0, y: 18, scale: 0.76, transformOrigin: "center center" });
      gsap.set(".continuity-startup-arc-stage", { opacity: 0 });
      gsap.set(".continuity-startup-arc-shell", { opacity: 0, y: 24, scale: 0.97 });
      gsap.set(".continuity-startup-kicker", { opacity: 0, y: 12 });
      gsap.set(".continuity-startup-zigzag", { strokeDasharray: 1, strokeDashoffset: 1 });
      gsap.set(".continuity-startup-node", { opacity: 0, scale: 0.72, transformOrigin: "center center" });
      gsap.set(".continuity-startup-card", { opacity: 0, y: 16 });
      gsap.set(".email-copy", { opacity: 0, y: 24 });
      gsap.set(".product-intro", { opacity: 0, y: 18 });
      gsap.set(".product-panel", { opacity: 0 });
      gsap.set(".product-panel-copy", { opacity: 0, x: -30 });
      gsap.set(".product-panel-phone", {
        opacity: 0,
        x: 28,
        scale: 0.96,
        filter: "blur(2px)",
      });
      gsap.set(".product-panel-caption", { opacity: 0, y: 14 });
      gsap.set(".vision-promise-line-1", { opacity: 0, y: 0, scale: 1 });
      gsap.set(".vision-promise-line-2", { opacity: 0, y: 24, scale: 0.982 });
      gsap.set(".vision-pillars-stage", { opacity: 0, y: 20 });
      gsap.set(".vision-pillar-card", { opacity: 0, y: 18 });
      gsap.set(".vision-pillar-voice", {
        opacity: 0,
        y: 0,
        scale: 0.42,
        filter: "blur(10px)",
        transformOrigin: "center center",
      });
      gsap.set(".vision-signoff", { opacity: 0, y: 20 });
      gsap.set(".builders-bridge-kicker", { opacity: 0, y: 14 });
      gsap.set(".builders-bridge-line", { opacity: 0, y: 22, scale: 0.985 });
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
      /* health arc gsap.set — parked with scene
      gsap.set(".health-occupancy-board", { opacity: 0, y: 26, scale: 0.97 });
      gsap.set(".health-occupancy-shell", { opacity: 0, y: 16 });
      gsap.set(".health-occupancy-copy", { opacity: 0, y: 12 });
      gsap.set(".health-occupancy-bubble", { opacity: 0, y: 18, scale: 0.76, transformOrigin: "center center" });
      gsap.set(".health-arc-stage", { opacity: 0 });
      gsap.set(".health-arc-shell", { opacity: 0, y: 24, scale: 0.97 });
      gsap.set(".health-arc-kicker", { opacity: 0, y: 12 });
      gsap.set(".health-arc-zigzag", { strokeDasharray: 1, strokeDashoffset: 1 });
      gsap.set(".health-arc-node", { opacity: 0, scale: 0.72, transformOrigin: "center center" });
      gsap.set(".health-arc-card", { opacity: 0, y: 16 });
      gsap.set(".health-output-stage", { opacity: 0, y: 26 });
      */

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
      // duration only available after timeline is built
      requestAnimationFrame(() => setDuration(tl.duration()));

      const createProductPanelTimeline = (panelIndex: number, hold = 1.05, narrateText?: string) => {
        const panelSelector = `.product-panel-${panelIndex}`;
        const copySelector = `.product-panel-copy-${panelIndex}`;
        const phoneSelector = `.product-panel-phone-${panelIndex}`;
        const captionSelector = `.product-panel-caption-${panelIndex}`;

        return gsap.timeline()
          .to(panelSelector, { opacity: 1, duration: 0.18 })
          .call(() => { if (narrateText) narrate(narrateText); }, undefined, "<")
          .to(copySelector, { opacity: 1, x: 0, duration: 0.72 }, "<")
          .to(
            phoneSelector,
            {
              opacity: 1,
              x: 0,
              scale: 1,
              filter: "blur(0px)",
              duration: 0.78,
            },
            "<+0.08",
          )
          .to(captionSelector, { opacity: 1, y: 0, duration: 0.48 }, "-=0.36")
          .to({}, { duration: hold })
          .to(copySelector, { opacity: 0, x: -24, duration: 0.42 })
          .to(phoneSelector, { opacity: 0, x: 22, scale: 0.98, duration: 0.46 }, "<")
          .to(captionSelector, { opacity: 0, y: 10, duration: 0.3 }, "<")
          .to(panelSelector, { opacity: 0, duration: 0.22 }, "-=0.12");
      };

      const createVisionVoiceReveal = (beatIndex: number) => {
        const voiceSelector = `.vision-pillar-voice-${beatIndex}`;
        const centerOffsets: Record<number, string> = {
          1: "22vw",
          2: "0vw",
          3: "-22vw",
        };

        return gsap.timeline()
          .fromTo(
            voiceSelector,
            {
              opacity: 0,
              x: centerOffsets[beatIndex] ?? "0vw",
              scale: 0.42,
              filter: "blur(10px)",
            },
            {
              opacity: 1,
              x: "0vw",
              scale: 1,
              filter: "blur(0px)",
              duration: 0.86,
              ease: "back.out(1.55)",
            },
          );
      };

      tl.to("#scene-1", { opacity: 1, duration: PACE.sceneFade })
        .from(".line-1", { opacity: 0, y: 40, duration: 0.95 })
        .call(() => narrate("There's a conversation happening in your head."), undefined, "<")
        .to({}, { duration: 2.2 })
        .from(".line-2", { opacity: 0, y: 30, duration: PACE.lineRevealLong }, "<")
        .call(() => narrate("It never really stops."), undefined, "<")
        .to({}, { duration: 2.0 })
        .from(".line-3a", { opacity: 0, y: 30, duration: PACE.lineRevealLong }, "<")
        .call(() => narrate("And it doesn't carry forward."), undefined, "<")
        .to({}, { duration: 2.0 })
        .from(".line-3b", { opacity: 0, y: 30, duration: PACE.lineRevealLong }, "<")
        .call(() => narrate("Nothing actually holds it together."), undefined, "<")
        .to({}, { duration: 2.0 })
        .to(
          ".thought-field",
          {
            opacity: 1,
            scale: 1,
            duration: 0.8,
          },
          "<",
        )
        .to(
          ".thought-persistent",
          {
            opacity: 0.72,
            scale: 1,
            stagger: 0.06,
            duration: 0.68,
          },
          "-=0.18",
        )
        .to(
          ".scene-1-copy",
          {
            opacity: 0,
            y: -32,
            duration: PACE.lineReveal,
          },
          "+=0.08",
        )
        .to(
          ".thought-transient",
          {
            opacity: 0.96,
            y: -4,
            scale: 1.04,
            stagger: 0.06,
            duration: 0.22,
          },
          "-=0.08",
        )
        .to(
          ".blip-marker",
          {
            opacity: 1,
            scale: 1.28,
            stagger: 0.06,
            duration: 0.1,
          },
          "<",
        )
        .to(
          ".blip-marker",
          {
            scale: 1,
            duration: 0.12,
            stagger: 0.06,
          },
          ">-0.02",
        )
        .to(
          ".thought-transient",
          {
            opacity: 0,
            y: -12,
            scale: 0.98,
            stagger: 0.06,
            duration: 0.22,
          },
          ">-0.02",
        )
        .to(
          ".blip-marker",
          {
            opacity: 0,
            scale: 0.7,
            stagger: 0.06,
            duration: 0.14,
          },
          "<",
        )
        .to(".thought-persistent", {
          x: "random(-220,220)",
          y: "random(-180,180)",
          opacity: 0.28,
          duration: 0.7,
          stagger: 0.02,
        })
        .to(
          ".thought-vignette",
          {
            opacity: 0.45,
            duration: 0.82,
          },
          "<",
        )
        .to(".line-1, .line-2, .line-3a, .line-3b", { opacity: 0, duration: 0.5 }, "-=0.28")
        // Boost thoughts to full visibility before the per-group dissolution begins
        .to(".thought-persistent", { opacity: 0.55, duration: 0.5, ease: "power1.out" }, "+=0.1")
        // Scene 2 cross-fades in as the thought field is still alive
        .to("#scene-2", { opacity: 1, duration: 2.6, ease: "power1.inOut" }, "+=0.2")

        // "You wind down for the day" — general thoughts start a slow ambient drift
        .from(".bridge-1", { opacity: 0, y: 18, duration: PACE.lineReveal }, "<+0.4")
        .call(() => narrate("You wind down for the day."), undefined, "<")
        .to(".thought-persistent:not(.thought-signal):not(.thought-thread):not(.thought-idea)", {
          y: "+=45", opacity: 0.22, duration: 2.4,
          stagger: { each: 0.04, from: "random" }, ease: "power1.inOut",
        }, "<+0.1")

        // "The signal fades with it" — signal thoughts blur and fade
        .from(".bridge-2", { opacity: 0, y: 18, duration: PACE.lineReveal }, "+=2.0")
        .call(() => narrate("The signal fades with it."), undefined, "<")
        .to(".thought-signal", {
          opacity: 0, filter: "blur(10px)", y: "+=30", scale: 0.88, duration: 1.4,
          stagger: { each: 0.12, from: "random" }, ease: "power2.in",
        }, "<+0.05")

        // "By morning, the thread is gone" — thread thoughts stretch then vanish
        .from(".bridge-3", { opacity: 0, y: 18, duration: PACE.lineRevealLong }, "+=2.0")
        .call(() => narrate("By morning, the thread is gone."), undefined, "<")
        .to(".thought-thread", {
          scaleX: 2.4, opacity: 0, filter: "blur(8px)", duration: 1.6,
          stagger: { each: 0.14, from: "random" }, ease: "power2.in",
        }, "<+0.05")

        // "Thoughts reset" — remaining general thoughts scatter and fall
        .from(".break-1", { opacity: 0, y: 20, duration: PACE.lineRevealLong }, "+=2.0")
        .call(() => narrate("Thoughts reset."), undefined, "<")
        .to(".thought-persistent:not(.thought-signal):not(.thought-thread):not(.thought-idea)", {
          y: "+=150", opacity: 0, filter: "blur(8px)", scale: 0.82, duration: 2.0,
          stagger: { each: 0.06, from: "random" }, ease: "power2.in",
        }, "<+0.05")

        // "Good ideas die" — amber idea sparks implode dramatically
        .from(".break-2", { opacity: 0, y: 20, duration: PACE.lineRevealLong }, "+=2.0")
        .call(() => narrate("Good ideas die."), undefined, "<")
        .to(".thought-idea", {
          scale: 0, opacity: 0, filter: "blur(14px)", duration: 1.2,
          stagger: { each: 0.12, from: "random" }, ease: "back.in(1.2)",
        }, "<+0.05")

        // "Continuity is lost" — vignette clears, scene-1 shell fades
        .from(".break-3", { opacity: 0, y: 20, duration: PACE.lineRevealLong }, "+=2.0")
        .call(() => narrate("Continuity is lost."), undefined, "<")
        .to(".thought-vignette", { opacity: 0, duration: 1.8, ease: "power1.in" }, "<")
        .to("#scene-1", { opacity: 0, duration: 1.0, ease: "power1.in" }, "<+0.9")

        .to("#scene-2", { opacity: 0, duration: PACE.sceneFadeLong, delay: PACE.mediumHold })
        .to("#scene-3", { opacity: 1, duration: PACE.sceneFade }, "-=0.14")
        .from(".sakhi-headline", {
          opacity: 0,
          y: 18,
          scale: 0.95,
          duration: 1,
        })
        .call(() => narrate("Sakhi makes it all come together."), undefined, "<")
        .to(".sakhi-headline", {
          opacity: 0,
          y: -18,
          scale: 0.985,
          duration: 0.68,
        }, "+=2.6")
        .to(".sakhi-bridge", {
          opacity: 1,
          duration: 0.35,
        }, "-=0.08")
        .to(".sakhi-bridge-line-1", {
          opacity: 1,
          y: 0,
          duration: PACE.lineReveal,
        }, "<")
        .call(() => narrate("You do not have to be driven by your thoughts."), undefined, "<")
        .to({}, { duration: 2.2 })
        .to(".sakhi-bridge-line-2", {
          opacity: 1,
          y: 0,
          duration: PACE.lineReveal,
        }, "<")
        .call(() => narrate("You can shape them."), undefined, "<")
        .to(".sakhi-bridge", {
          opacity: 0,
          duration: 0.52,
        }, "+=2.2")
        .to(".intro-sequence", {
          opacity: 1,
          duration: 0.35,
        }, "-=0.1")
        .to(".intro-line-1", {
          opacity: 1,
          duration: PACE.lineReveal,
        }, "<")
        .call(() => narrate("Stop reacting."), undefined, "<")
        .to(".intro-line-1", {
          opacity: 0,
          y: -30,
          scale: 0.984,
          duration: 0.65,
        }, "+=1.8")
        .to(".intro-line-2", {
          opacity: 1,
          y: 0,
          scale: 1,
          duration: PACE.lineRevealLong,
        }, "-=0.24")
        .call(() => narrate("Start shaping."), undefined, "<")
        .to({}, { duration: 2.0 })
        .to(".intro-explainer", {
          opacity: 1,
          y: 0,
          duration: PACE.lineReveal,
        })
        .call(() => narrate("Sakhi learns how you think and evolves with you."), undefined, "<")
        .to({}, { duration: 3.2 })
        .to(".intro-system", {
          opacity: 1,
          y: 0,
          duration: PACE.lineReveal,
        })
        .to(".intro-active-1", {
          opacity: 1,
          x: "0vw",
          scale: 1,
          duration: PACE.lineReveal,
        }, "-=0.14")
        .call(() => narrate("Builds a living model of you. It evolves over time."), undefined, "<")
        .to(".intro-progress-1", {
          scaleX: 1,
          duration: 0.48,
        }, "<")
        .to(".intro-active-1", {
          opacity: 0,
          x: "-10vw",
          scale: 0.984,
          duration: 0.58,
        }, "+=2.6")
        .to(".intro-parked-1", {
          opacity: 0.62,
          y: 0,
          scale: 1,
          duration: 0.42,
        }, "<")
        .to(".intro-active-2", {
          opacity: 1,
          x: "0vw",
          scale: 1,
          duration: PACE.lineReveal,
        }, "-=0.14")
        .call(() => narrate("Makes your life visible. Across time, as a whole."), undefined, "<")
        .to(".intro-progress-2", {
          scaleX: 1,
          duration: 0.48,
        }, "<")
        .to(".intro-active-2", {
          opacity: 0,
          x: "0vw",
          scale: 0.986,
          duration: 0.58,
        }, "+=2.6")
        .to(".intro-parked-2", {
          opacity: 0.92,
          y: 0,
          scale: 1,
          duration: 0.42,
        }, "<")
        .to(".intro-active-3", {
          opacity: 1,
          x: "0vw",
          scale: 1,
          duration: PACE.lineReveal,
        }, "-=0.14")
        .call(() => narrate("Helps you act decisively. It learns from what follows."), undefined, "<")
        .to(".intro-progress-3", {
          scaleX: 1,
          duration: 0.48,
        }, "<")
        .to(".intro-active-3", {
          opacity: 0,
          x: "10vw",
          scale: 0.984,
          duration: 0.58,
        }, "+=2.6")
        .to(".intro-parked-3", {
          opacity: 0.68,
          y: 0,
          scale: 1,
          duration: 0.42,
        }, "<")
        .to(".intro-explainer", {
          opacity: 0.2,
          y: -12,
          duration: 0.7,
        }, `+=${PACE.shortHold}`)
        .to(".intro-progress-wrap", {
          opacity: 0,
          y: -18,
          duration: 0.7,
        }, "<")
        .to(".intro-parked-row", {
          opacity: 0,
          y: -92,
          duration: 0.8,
          ease: "power2.inOut",
        }, "<")
        .to(".intro-resolved", {
          opacity: 1,
          y: 0,
          scale: 1,
          duration: 0.82,
          ease: "power2.inOut",
        }, "<")
        .to(".intro-resolved-item", {
          opacity: 1,
          y: 0,
          stagger: 0.08,
          duration: 0.5,
        }, "<+0.04")
        .to("#scene-3", { opacity: 0, duration: PACE.sceneFadeLong, delay: 2.5 })
        .to("#scene-4", { opacity: 1, duration: PACE.sceneFade }, "-=0.12")
        .to(".continuity-core-shell", {
          opacity: 1,
          scale: 1,
          duration: 0.62,
          ease: "power2.out",
        }, "<")
        .to(".continuity-core-label", {
          opacity: 1,
          y: 0,
          duration: 0.4,
        }, "-=0.28")
        .to(".continuity-core-ring", {
          opacity: 0.36,
          scale: 1,
          stagger: 0.04,
          duration: 0.54,
        }, "<")
        .to({}, { duration: 0.22 })
        .to(".continuity-noise-item", {
          x: 0,
          y: 0,
          opacity: 0,
          scale: 0.26,
          stagger: {
            each: 0.025,
            from: "random",
          },
          duration: 0.5,
          ease: "power3.in",
        })
        .to(".continuity-core-shell", {
          scale: 1.08,
          boxShadow: "0 0 110px rgba(136,160,255,0.26)",
          duration: 0.36,
          ease: "power2.out",
        }, "-=0.32")
        .to(".continuity-core-wrap", {
          opacity: 0,
          duration: 0.3,
          ease: "power2.out",
        }, "-=0.04")
        .to(".continuity-output-stage", {
          opacity: 1,
          y: 0,
          duration: 0.42,
        }, "-=0.02")
        .to(".continuity-occupancy-board", {
          opacity: 1,
          y: 0,
          scale: 1,
          duration: 0.54,
        }, "<+0.02")
        .to(".continuity-occupancy-header", {
          opacity: 1,
          y: 0,
          duration: 0.34,
        }, "-=0.06")
        .to(".continuity-occupancy-shell", {
          opacity: 1,
          y: 0,
          duration: 0.36,
        }, "-=0.22")
        .to(".continuity-occupancy-copy", {
          opacity: 1,
          y: 0,
          duration: 0.28,
        }, "-=0.22")
        .to(".continuity-occupancy-bubble", {
          opacity: 1,
          scale: 1,
          y: 0,
          stagger: {
            each: 0.08,
            from: "center",
          },
          duration: 0.44,
          ease: "back.out(1.32)",
        }, "-=0.06")
        .to({}, { duration: 4.5 })
        .to(".continuity-occupancy-bubble:not(.continuity-startup-bubble)", {
          opacity: 0.14,
          scale: 0.84,
          stagger: 0.03,
          duration: 0.32,
        })
        .to(".continuity-startup-bubble", {
          scale: 1.18,
          duration: 0.34,
          ease: "power2.out",
        }, "<")
        .to(".continuity-occupancy-board", {
          opacity: 0,
          scale: 1.02,
          duration: 0.38,
        }, "+=0.04")
        .to(".continuity-startup-arc-stage", {
          opacity: 1,
          duration: 0.18,
        }, "-=0.12")
        .to(".continuity-startup-arc-shell", {
          opacity: 1,
          y: 0,
          scale: 1,
          duration: 0.46,
        }, "<")
        .to(".continuity-startup-kicker", {
          opacity: 1,
          y: 0,
          duration: 0.28,
        }, "-=0.26")
        .to(".continuity-startup-zigzag", {
          strokeDashoffset: 0,
          duration: 0.9,
          ease: "power2.inOut",
        }, "<+0.06")
        .to(".continuity-startup-node", {
          opacity: 1,
          scale: 1,
          stagger: 0.12,
          duration: 0.24,
          ease: "back.out(1.6)",
        }, "<+0.12")
        .to(".continuity-startup-card", {
          opacity: 1,
          y: 0,
          stagger: 0.12,
          duration: 0.34,
        }, "<+0.04")
        .to({}, { duration: 5.0 })
        .to(".continuity-visual", {
          opacity: 0,
          scale: 1.02,
          duration: 0.68,
        })
        .to({}, { duration: 0.15 })
        .to(".continuity-copy", {
          opacity: 1,
          y: 0,
          duration: 0.78,
        })
        .call(() => narrate("Your life, connected across time."), undefined, "<")
        .from(".continuity-line", {
          opacity: 0,
          y: 18,
          stagger: 3.0,
          duration: PACE.lineReveal,
        }, "<+0.04")
        .to("#scene-4", { opacity: 0, duration: PACE.sceneFadeLong, delay: 4.5 })
        /* ── Scene 4b: Health Signal Arc — parked ───────────────────────
        .to("#scene-4b", { opacity: 1, duration: PACE.sceneFade }, "-=0.12")
        .to(".health-output-stage", { opacity: 1, y: 0, duration: 0.42 }, "<")
        .to(".health-occupancy-board", { opacity: 1, y: 0, scale: 1, duration: 0.54 }, "<+0.02")
        .to(".health-occupancy-shell", { opacity: 1, y: 0, duration: 0.36 }, "-=0.06")
        .to(".health-occupancy-copy", { opacity: 1, y: 0, duration: 0.28 }, "-=0.22")
        .to(".health-occupancy-bubble", {
          opacity: 1, scale: 1, y: 0,
          stagger: { each: 0.08, from: "center" },
          duration: 0.44, ease: "back.out(1.32)",
        }, "-=0.06")
        .to({}, { duration: 2.2 })
        .to(".health-main-bubble", { scale: 1.08, duration: 0.34, ease: "power2.out" })
        .to(".health-occupancy-bubble:not(.health-main-bubble)", {
          opacity: 0.14, scale: 0.84, stagger: 0.03, duration: 0.32,
        }, "<")
        .to(".health-occupancy-board", { opacity: 0, scale: 1.02, duration: 0.38 }, "+=0.04")
        .to(".health-arc-stage", { opacity: 1, duration: 0.18 }, "-=0.12")
        .to(".health-arc-shell", { opacity: 1, y: 0, scale: 1, duration: 0.46 }, "<")
        .to(".health-arc-kicker", { opacity: 1, y: 0, duration: 0.28 }, "-=0.26")
        .to(".health-arc-zigzag", { strokeDashoffset: 0, duration: 0.9, ease: "power2.inOut" }, "<+0.06")
        .to(".health-arc-node", {
          opacity: 1, scale: 1, stagger: 0.12, duration: 0.24, ease: "back.out(1.6)",
        }, "<+0.12")
        .to(".health-arc-card", { opacity: 1, y: 0, stagger: 0.12, duration: 0.34 }, "<+0.04")
        .to({}, { duration: 2.8 })
        .to("#scene-4b", { opacity: 0, duration: PACE.sceneFadeLong })
        ── end health arc ── */
        .to("#scene-5", { opacity: 1, duration: PACE.sceneFade }, "-=0.12")
        .to(".product-intro", {
          opacity: 1,
          y: 0,
          duration: PACE.lineRevealLong,
        })
        .call(() => narrate("First expression of Sakhi."), undefined, "<")
        .to({}, { duration: 2.2 })
        .to(".product-intro", {
          opacity: 0,
          y: -18,
          duration: 0.45,
        })
        .add(createProductPanelTimeline(1, 5.0, "Start talking. Sakhi does the rest."))
        .add(createProductPanelTimeline(2, 5.0, "Your life becomes visible."))
        .add(createProductPanelTimeline(3, 5.0, "Your story starts to take shape."))
        .add(createProductPanelTimeline(4, 5.0, "What you share stays yours."))
        .to(".product-stage", {
          opacity: 0,
          scale: 0.975,
          duration: PACE.sceneFadeLong,
        })
        .to("#scene-5", { opacity: 0, duration: PACE.sceneFadeLong, delay: PACE.shortHold })
        .to("#scene-6", { opacity: 1, duration: PACE.sceneFade }, "-=0.15")
        .to(".vision-promise-line-1", {
          opacity: 1,
          y: 0,
          duration: 0.82,
        })
        .call(() => narrate("Sakhi makes your life seen,"), undefined, "<")
        .to({}, { duration: 2.0 })
        .to(".vision-promise-line-2", {
          opacity: 1,
          y: 0,
          scale: 1,
          duration: PACE.lineRevealLong,
        })
        .call(() => narrate("understood, and actionable."), undefined, "<")
        .to({}, { duration: 2.0 })
        .to(".vision-pillars-stage", {
          opacity: 1,
          y: 0,
          duration: 0.4,
        }, "-=0.12")
        .to(".vision-pillar-card", {
          opacity: 1,
          y: 0,
          stagger: 0.12,
          duration: 0.62,
        }, "<+0.06")
        .to({}, { duration: 2.0 })
        // Voice lines pop in per column — connection to each pillar is explicit
        .add(createVisionVoiceReveal(1))
        .call(() => narrate("I see you."), undefined, "<")
        .to({}, { duration: 1.8 })
        .add(createVisionVoiceReveal(2))
        .call(() => narrate("I understand you."), undefined, "<")
        .to({}, { duration: 1.8 })
        .add(createVisionVoiceReveal(3))
        .call(() => narrate("I act for you."), undefined, "<")
        .to({}, { duration: 2.2 })
        .to(".vision-signoff", { opacity: 1, y: 0, duration: 0.72 })
        .to({}, { duration: 2.5 })
        .to("#scene-6", { opacity: 0, duration: PACE.sceneFadeLong })
        .to("#scene-7", { opacity: 1, duration: PACE.sceneFade }, "-=0.15")
        .to(".builders-bridge-kicker", {
          opacity: 1,
          y: 0,
          duration: 0.5,
        })
        .to(".builders-bridge-line", {
          opacity: 1,
          y: 0,
          scale: 1,
          duration: 0.9,
        }, "-=0.18")
        .call(() => narrate("The minds behind."), undefined, "<")
        .to({}, { duration: 3.0 })
        .to("#scene-7", { opacity: 0, duration: PACE.sceneFadeLong })
        .to("#scene-8", { opacity: 1, duration: PACE.sceneFade }, "-=0.15")
        .to(".founder-portrait", {
          opacity: 1,
          y: 0,
          scale: 1,
          duration: 0.75,
        })
        .to(".founder-meta", {
          opacity: 1,
          y: 0,
          duration: 0.6,
        }, "-=0.42")
        .to(".founder-opening", {
          opacity: 1,
          y: 0,
          duration: 0.95,
        }, "-=0.2")
        .call(() => narrate("I've spent 20 years helping organizations make better decisions. I realized we haven't solved this for individuals."), undefined, "<")
        .to({}, { duration: 5.0 })
        .to(".founder-opening", {
          opacity: 0,
          duration: 0.5,
        })
        .to(".founder-detail-kicker", {
          opacity: 1,
          y: 0,
          duration: 0.55,
        }, "-=0.15")
        .to(".founder-arc-shell", {
          opacity: 1,
          y: 0,
          scale: 1,
          duration: 0.72,
        }, "-=0.08")
        .to(".founder-arc-glow", {
          opacity: 0.32,
          scaleX: 1,
          duration: 0.9,
        }, "-=0.38")
        .to(".founder-arc-mobile-line", {
          opacity: 0.72,
          scaleY: 1,
          duration: 0.82,
        }, "<+0.08")
        .to(".founder-arc-head-1", {
          opacity: 1,
          y: 0,
          filter: "blur(0px)",
          duration: 0.52,
        }, "-=0.5")
        .call(() => narrate("Operator at Scale."), undefined, "<")
        .to(".founder-arc-step-1", {
          opacity: 1,
          y: 0,
          duration: 0.4,
        }, "-=0.28")
        .to(".founder-arc-body-1", {
          opacity: 1,
          y: 0,
          duration: 0.56,
        }, "-=0.12")
        .call(() => narrate("Worked alongside CEOs and COOs, building systems that turned ambiguity into structured decisions."), undefined, "<")
        .to(".founder-arc-link-1", {
          opacity: 0.92,
          scaleX: 1,
          duration: 0.42,
        }, "+=4.5")
        .to(".founder-arc-head-2", {
          opacity: 1,
          y: 0,
          filter: "blur(0px)",
          duration: 0.52,
        }, "-=0.08")
        .call(() => narrate("Personal Inflection Point."), undefined, "<")
        .to(".founder-arc-step-2", {
          opacity: 1,
          y: 0,
          duration: 0.4,
        }, "-=0.2")
        .to(".founder-arc-body-2", {
          opacity: 1,
          y: 0,
          duration: 0.56,
        }, "-=0.12")
        .call(() => narrate("In 2024, caregiving, leadership, and life complexity collided. What was missing was continuity at the level of a real human life."), undefined, "<")
        .to(".founder-arc-link-2", {
          opacity: 0.92,
          scaleX: 1,
          duration: 0.42,
        }, "+=4.5")
        .to(".founder-arc-head-3", {
          opacity: 1,
          y: 0,
          filter: "blur(0px)",
          duration: 0.52,
        }, "-=0.08")
        .call(() => narrate("Insight to Sakhi."), undefined, "<")
        .to(".founder-arc-step-3", {
          opacity: 1,
          y: 0,
          duration: 0.4,
        }, "-=0.2")
        .to(".founder-arc-body-3", {
          opacity: 1,
          y: 0,
          duration: 0.56,
        }, "-=0.12")
        .call(() => narrate("Small, personalized interventions changed everything. The question became: can this be built as a system?"), undefined, "<")
        .to(".founder-final", {
          opacity: 1,
          y: 0,
          duration: 0.8,
        }, "+=4.5")
        .call(() => narrate("Sakhi is the system I wish existed when I needed it most."), undefined, "<")
        .to({}, { duration: 3.5 })
        .to("#scene-8", { opacity: 0, duration: PACE.sceneFadeLong, delay: PACE.shortHold })
        .to("#scene-9", { opacity: 1, duration: PACE.sceneFade }, "-=0.15")
        .to(".ravi-visual", {
          opacity: 1,
          y: 0,
          scale: 1,
          duration: 0.75,
        })
        .to(".ravi-meta", {
          opacity: 1,
          y: 0,
          duration: 0.6,
        }, "-=0.42")
        .to(".ravi-opening", {
          opacity: 1,
          y: 0,
          duration: 1,
        }, "-=0.2")
        .call(() => narrate("I'm a systems thinker at heart, grounded in deep technical expertise and driven to simplify complexity."), undefined, "<")
        .to({}, { duration: 5.0 })
        .to(".ravi-opening", {
          opacity: 0,
          duration: 0.5,
        })
        .to(".ravi-detail-kicker", {
          opacity: 1,
          y: 0,
          duration: 0.55,
        }, "-=0.15")
        .to(".ravi-arc-shell", {
          opacity: 1,
          y: 0,
          scale: 1,
          duration: 0.72,
        }, "-=0.08")
        .to(".ravi-arc-glow", {
          opacity: 0.32,
          scaleX: 1,
          duration: 0.9,
        }, "-=0.38")
        .to(".ravi-arc-mobile-line", {
          opacity: 0.72,
          scaleY: 1,
          duration: 0.82,
        }, "<+0.08")
        .to(".ravi-arc-head-1", {
          opacity: 1,
          y: 0,
          filter: "blur(0px)",
          duration: 0.52,
        }, "-=0.5")
        .call(() => narrate("Evolution."), undefined, "<")
        .to(".ravi-arc-step-1", {
          opacity: 1,
          y: 0,
          duration: 0.4,
        }, "-=0.28")
        .to(".ravi-arc-body-1", {
          opacity: 1,
          y: 0,
          duration: 0.56,
        }, "-=0.12")
        .call(() => narrate("I started with engineering, building systems and applications, then kept moving closer to the question of what actually makes systems work."), undefined, "<")
        .to(".ravi-arc-link-1", {
          opacity: 0.92,
          scaleX: 1,
          duration: 0.42,
        }, "+=4.5")
        .to(".ravi-arc-head-2", {
          opacity: 1,
          y: 0,
          filter: "blur(0px)",
          duration: 0.52,
        }, "-=0.08")
        .call(() => narrate("Realization."), undefined, "<")
        .to(".ravi-arc-step-2", {
          opacity: 1,
          y: 0,
          duration: 0.4,
        }, "-=0.2")
        .to(".ravi-arc-body-2", {
          opacity: 1,
          y: 0,
          duration: 0.56,
        }, "-=0.12")
        .call(() => narrate("Systems do not succeed just because they are built well. They succeed because people understand them, trust them, and use them."), undefined, "<")
        .to(".ravi-arc-link-2", {
          opacity: 0.92,
          scaleX: 1,
          duration: 0.42,
        }, "+=4.5")
        .to(".ravi-arc-head-3", {
          opacity: 1,
          y: 0,
          filter: "blur(0px)",
          duration: 0.52,
        }, "-=0.08")
        .call(() => narrate("Expansion."), undefined, "<")
        .to(".ravi-arc-step-3", {
          opacity: 1,
          y: 0,
          duration: 0.4,
        }, "-=0.2")
        .to(".ravi-arc-body-3", {
          opacity: 1,
          y: 0,
          duration: 0.56,
        }, "-=0.12")
        .call(() => narrate("That pulled me across engineering, product, and product marketing, while yoga and meditation deepened how I think about human behavior over time."), undefined, "<")
        .to(".ravi-arc-link-3", {
          opacity: 0.92,
          scaleX: 1,
          duration: 0.42,
        }, "+=4.5")
        .to(".ravi-arc-head-4", {
          opacity: 1,
          y: 0,
          filter: "blur(0px)",
          duration: 0.52,
        }, "-=0.08")
        .call(() => narrate("Convergence."), undefined, "<")
        .to(".ravi-arc-step-4", {
          opacity: 1,
          y: 0,
          duration: 0.4,
        }, "-=0.2")
        .to(".ravi-arc-body-4", {
          opacity: 1,
          y: 0,
          duration: 0.56,
        }, "-=0.08")
        .call(() => narrate("Technical depth, systems thinking, product narrative, and lived understanding of people now converge in building Sakhi."), undefined, "<")
        .to(".ravi-final", {
          opacity: 1,
          y: 0,
          duration: 0.8,
        }, "+=4.8")
        .call(() => narrate("That gives me the clarity to build Sakhi."), undefined, "<")
        .to({}, { duration: 3.5 })
        .to("#scene-9", { opacity: 0, duration: PACE.sceneFadeLong, delay: PACE.shortHold })
        .to("#scene-10", { opacity: 1, duration: PACE.sceneFade }, "-=0.15")
        .from(".close-line", {
          opacity: 0,
          y: 20,
          scale: 0.98,
          stagger: 1.8,
          duration: PACE.lineRevealLong,
        })
        .call(() => narrate("This is just the beginning. If this resonates, let's build this together."), undefined, "<")
        .from(".card", {
          opacity: 0,
          y: 30,
          stagger: 0.18,
          duration: PACE.lineRevealLong,
        });
    }, containerRef);

    return () => {
      timelineRef.current = null;
      ctx.revert();
    };
  }, [containerRef, speechRef]);

  const togglePlayback = useCallback(() => {
    const timeline = timelineRef.current;
    if (!timeline) {
      return;
    }

    if (isComplete || timeline.progress() >= 1) {
      timeline.pause(0);
      timeline.play();
      setIsComplete(false);
      setIsPaused(false);
      setProgress(0);
      return;
    }

    if (timeline.paused()) {
      timeline.play();
      setIsPaused(false);
      return;
    }

    timeline.pause();
    setIsPaused(true);
  }, [isComplete]);

  const restart = useCallback(() => {
    const timeline = timelineRef.current;
    if (!timeline) {
      return;
    }

    timeline.pause(0);
    timeline.play();
    setIsComplete(false);
    setIsPaused(false);
    setProgress(0);
  }, []);

  const seekTo = useCallback((nextProgress: number) => {
    const timeline = timelineRef.current;
    if (!timeline) {
      return;
    }

    const clamped = Math.max(0, Math.min(1, nextProgress));
    timeline.pause();
    timeline.progress(clamped, false);
    setProgress(clamped);
    setIsPaused(true);
    setIsComplete(clamped >= 1);
  }, []);

  return {
    isPaused,
    isComplete,
    progress,
    duration,
    togglePlayback,
    restart,
    seekTo,
  };
};
