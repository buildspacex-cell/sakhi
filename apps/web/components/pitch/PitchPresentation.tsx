"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Image from "next/image";
import gsap from "gsap";
import ThoughtParticle from "@/components/story/ThoughtParticle";

const TOTAL_STEPS = 19;
const FOUNDER_BRIDGE_AUTO_ADVANCE_MS = 1800;

// ── Thought data ──────────────────────────────────────────────────────────────
const TRANSIENT_THOUGHTS = [
  { text: "one more thing",                top: "14%", left: "10%", markerSize: "base" as const },
  { text: "did I say yes?",               top: "24%", left: "28%", markerSize: "base" as const },
  { text: "need to follow up",            top: "44%", left: "14%", markerSize: "base" as const },
  { text: "what did I promise?",          top: "74%", left: "16%", markerSize: "lg"   as const },
  { text: "I forgot again",               top: "10%", left: "48%", markerSize: "base" as const },
  { text: "should I reply now?",          top: "82%", left: "38%", markerSize: "base" as const },
  { text: "did I miss the tone?",         top: "34%", left: "44%", markerSize: "base" as const },
  { text: "follow up tomorrow",           top: "66%", left: "54%", markerSize: "base" as const },
  { text: "not this again",               top: "18%", left: "78%", markerSize: "base" as const },
  { text: "I need to remember",           top: "52%", left: "86%", markerSize: "lg"   as const },
  { text: "this feels urgent",            top: "30%", left: "70%", markerSize: "lg"   as const },
  { text: "not tonight",                  top: "78%", left: "72%", markerSize: "base" as const },
  { text: "say it clearly",               top: "12%", left: "90%", markerSize: "base" as const },
  { text: "I missed that",                top: "60%", left: "66%", markerSize: "base" as const },
  { text: "how do I respond?",            top: "46%", left: "84%", markerSize: "base" as const },
  { text: "did I commit to that?",        top: "68%", left: "34%", markerSize: "base" as const },
  { text: "what do they need from me?",   top: "18%", left: "60%", markerSize: "base" as const },
  { text: "I need to take mom to dentist",top: "12%", left: "22%", markerSize: "lg"   as const },
  { text: "schedule interview",           top: "38%", left: "20%", markerSize: "base" as const },
  { text: "an aha moment...",             top: "72%", left: "46%", markerSize: "lg"   as const },
  { text: "this connects to last week",   top: "28%", left: "52%", markerSize: "base" as const },
  { text: "I keep coming back to this",   top: "80%", left: "58%", markerSize: "base" as const },
] as const;

const THOUGHTS = [
  { text: "did I reply?", top: "12%", left: "56%", type: undefined as "signal"|"thread"|"idea"|undefined },
  { text: "I'll do it later", top: "18%", left: "72%", type: undefined as "signal"|"thread"|"idea"|undefined },
  { text: "what did they say?", top: "14%", left: "40%", type: undefined as "signal"|"thread"|"idea"|undefined },
  { text: "don't forget", top: "56%", left: "74%", type: undefined as "signal"|"thread"|"idea"|undefined },
  { text: "maybe later", top: "30%", left: "82%", type: undefined as "signal"|"thread"|"idea"|undefined },
  { text: "why again?", top: "44%", left: "62%", type: undefined as "signal"|"thread"|"idea"|undefined },
  { text: "call her back", top: "38%", left: "78%", type: undefined as "signal"|"thread"|"idea"|undefined },
  { text: "what now", top: "70%", left: "54%", type: undefined as "signal"|"thread"|"idea"|undefined },
  { text: "not now", top: "26%", left: "64%", type: undefined as "signal"|"thread"|"idea"|undefined },
  { text: "later tonight", top: "14%", left: "84%", type: undefined as "signal"|"thread"|"idea"|undefined },
  { text: "tomorrow", top: "72%", left: "84%", type: undefined as "signal"|"thread"|"idea"|undefined },
  { text: "remember", top: "86%", left: "62%", type: undefined as "signal"|"thread"|"idea"|undefined },
  { text: "respond", top: "50%", left: "90%", type: undefined as "signal"|"thread"|"idea"|undefined },
  { text: "later", top: "8%", left: "70%", type: undefined as "signal"|"thread"|"idea"|undefined },
  { text: "how do I say this?", top: "24%", left: "88%", type: undefined as "signal"|"thread"|"idea"|undefined },
  { text: "did that sound wrong?", top: "34%", left: "68%", type: undefined as "signal"|"thread"|"idea"|undefined },
  { text: "media presentation", top: "22%", left: "18%", type: undefined as "signal"|"thread"|"idea"|undefined },
  { text: "flu shot for the kids", top: "84%", left: "34%", type: undefined as "signal"|"thread"|"idea"|undefined },
  { text: "grocery, I'm out of milk", top: "88%", left: "78%", type: undefined as "signal"|"thread"|"idea"|undefined },
  { text: "pay piano class fee", top: "58%", left: "16%", type: undefined as "signal"|"thread"|"idea"|undefined },
  { text: "say something", top: "62%", left: "48%", type: undefined as "signal"|"thread"|"idea"|undefined },
  { text: "pick up clothes from laundry", top: "64%", left: "8%", type: undefined as "signal"|"thread"|"idea"|undefined },
  { text: "why does this keep repeating", top: "68%", left: "74%", type: "signal" as const },
  { text: "the same pattern again", top: "74%", left: "60%", type: "signal" as const },
  { text: "I should remember this", top: "54%", left: "58%", type: "signal" as const },
  { text: "did I miss something", top: "32%", left: "60%", type: "signal" as const },
  { text: "again?", top: "18%", left: "73%", type: "signal" as const },
  { text: "this thread isn't finished", top: "48%", left: "38%", type: "thread" as const },
  { text: "I said I'd revisit this", top: "40%", left: "50%", type: "thread" as const },
  { text: "I need to get back to them", top: "60%", left: "30%", type: "thread" as const },
  { text: "what did I promise?", top: "42%", left: "26%", type: "thread" as const },
  { text: "what am I missing", top: "80%", left: "70%", type: "thread" as const },
  { text: "✦ what if this changes everything", top: "20%", left: "34%", type: "idea" as const },
  { text: "✦ I just had a breakthrough", top: "50%", left: "20%", type: "idea" as const },
  { text: "✦ this connects it all", top: "66%", left: "44%", type: "idea" as const },
  { text: "✦ an insight that matters", top: "15%", left: "60%", type: "idea" as const },
  { text: "✦ this could work differently", top: "78%", left: "28%", type: "idea" as const },
];

// ── Slide 01 — Chaos ─────────────────────────────────────────────────────────
function Slide01Chaos() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const ctx = gsap.context(() => {
      gsap.set(".s1-line-1,.s1-line-2,.s1-line-3a,.s1-line-3b", { opacity: 0, y: 36 });
      gsap.set(".s1-copy", { opacity: 1 });
      gsap.set(".s1-thought", { opacity: 0 });
      gsap.set(".s1-transient", { opacity: 0, y: 12, scale: 0.94 });
      gsap.set(".s1-transient .blip-marker", { scale: 0.5, opacity: 0 });
      const tl = gsap.timeline({ defaults: { ease: "power2.out" } });
      tl.to(".s1-line-1", { opacity: 1, y: 0, duration: 0.9 }, 0.2)
        .to(".s1-line-2", { opacity: 1, y: 0, duration: 0.72 }, "+=0.6")
        .to(".s1-line-3a", { opacity: 1, y: 0, duration: 0.72 }, "+=0.4")
        .to(".s1-line-3b", { opacity: 1, y: 0, duration: 0.72 }, "+=0.3")
        .to('.s1-thought[data-type="general"]', { opacity: 0.32, stagger: { each: 0.04, from: "random" }, duration: 0.5 }, "+=0.4")
        .to('.s1-thought[data-type="signal"]', { opacity: 0.28, stagger: { each: 0.06 }, duration: 0.5 }, "<+0.2")
        .to('.s1-thought[data-type="thread"]', { opacity: 0.28, stagger: { each: 0.06 }, duration: 0.5 }, "<+0.2")
        .to('.s1-thought[data-type="idea"]', { opacity: 0.72, stagger: { each: 0.07 }, duration: 0.5 }, "<+0.2")
        .to(".s1-copy", { opacity: 0, y: -28, duration: 0.7 }, "+=0.9")
        .to('.s1-thought[data-type="general"]', { opacity: 0.5, stagger: { each: 0.03, from: "random" }, duration: 0.8 }, "<+0.1")
        .to('.s1-thought[data-type="signal"]', { opacity: 0.44, stagger: { each: 0.05 }, duration: 0.8 }, "<")
        .to('.s1-thought[data-type="thread"]', { opacity: 0.44, stagger: { each: 0.05 }, duration: 0.8 }, "<")
        .to('.s1-thought[data-type="idea"]', { opacity: 0.88, stagger: { each: 0.07 }, duration: 0.8 }, "<")
        // transient blips flash in then fade
        .to(".s1-transient",             { opacity: 0.96, y: -4, scale: 1.04, stagger: { each: 0.06 }, duration: 0.22 }, "-=0.08")
        .to(".s1-transient .blip-marker", { opacity: 1, scale: 1.28, stagger: 0.06, duration: 0.1 }, "<")
        .to(".s1-transient .blip-marker", { scale: 1, stagger: 0.06, duration: 0.12 }, ">-0.02")
        .to(".s1-transient",             { opacity: 0, y: -12, scale: 0.98, stagger: 0.06, duration: 0.22 }, ">-0.02")
        .to(".s1-transient .blip-marker", { opacity: 0, scale: 0.7, stagger: 0.06, duration: 0.14 }, "<");
    }, ref);
    return () => ctx.revert();
  }, []);
  return (
    <div ref={ref} className="absolute inset-0 overflow-hidden px-10 py-12 sm:px-14 lg:px-20">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_18%_18%,rgba(138,163,255,0.08),transparent_26%),radial-gradient(circle_at_76%_26%,rgba(138,163,255,0.07),transparent_28%),linear-gradient(180deg,rgba(7,10,16,0.18),rgba(7,10,16,0.74))]" />
      {THOUGHTS.map((t) => (
        <div
          key={t.text}
          data-type={t.type ?? "general"}
          className={`s1-thought absolute whitespace-nowrap font-medium tracking-[-0.02em] ${
            t.type === "idea"
              ? "text-[clamp(0.9rem,1.25vw,1.6rem)] text-[#ffd59a]"
              : "text-[clamp(0.85rem,1.2vw,1.5rem)] text-white/80"
          }`}
          style={{ top: t.top, left: t.left }}
        >
          {t.text}
        </div>
      ))}
      {TRANSIENT_THOUGHTS.map((t) => (
        <ThoughtParticle
          key={t.text}
          text={t.text}
          top={t.top}
          left={t.left}
          blip
          markerSize={t.markerSize}
          className="s1-transient text-[clamp(0.85rem,1.05vw,1.2rem)] font-medium tracking-[-0.02em] text-[#d8e2ff]/0"
        />
      ))}
      <div className="s1-copy relative z-10 flex h-full items-center">
        <div className="max-w-3xl">
          <p className="s1-line-1 text-[clamp(3rem,6vw,5.5rem)] font-semibold leading-[0.98] tracking-[-0.06em] text-white" style={{ maxWidth: "10ch" }}>
            There&apos;s a conversation happening in your head.
          </p>
          <div className="mt-10 space-y-4 text-[clamp(1.1rem,2vw,1.6rem)] leading-[1.45] tracking-[-0.03em]">
            <p className="s1-line-2 text-[#c9d3ea]">It never really stops.</p>
            <p className="s1-line-3a text-[#c9d3ea]">And it doesn&apos;t carry forward.</p>
            <p className="s1-line-3b font-medium text-slate-100">Nothing actually holds it together.</p>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Slide 02 — Breakdown ──────────────────────────────────────────────────────
function Slide02Breakdown() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const ctx = gsap.context(() => {
      // Thoughts start already visible (end-state of Slide01)
      gsap.set(".s2-thought", { opacity: 0.48 });
      gsap.set(".s2-thought-idea", { opacity: 0.78 });
      gsap.set(".s2-bridge-1,.s2-bridge-2,.s2-bridge-3", { opacity: 0, y: 18 });
      gsap.set(".s2-break-1,.s2-break-2,.s2-break-3", { opacity: 0, y: 22, scale: 0.96 });
      const tl = gsap.timeline({ defaults: { ease: "power2.out" } });
      tl.to(".s2-bridge-1", { opacity: 1, y: 0, duration: 0.72 }, 0.3)
        .to(".s2-bridge-2", { opacity: 1, y: 0, duration: 0.72 }, "+=0.45")
        .to(".s2-bridge-3", { opacity: 1, y: 0, duration: 0.72 }, "+=0.45")
        // thoughts begin to drain away
        .to(".s2-thought,.s2-thought-idea", { opacity: 0.18, duration: 1.1, stagger: { each: 0.04, from: "random" }, ease: "power1.in" }, "+=0.3")
        .to(".s2-break-1", { opacity: 1, y: 0, scale: 1, duration: 0.78 }, "+=0.2")
        .to(".s2-thought,.s2-thought-idea", { opacity: 0, duration: 0.9, stagger: { each: 0.03, from: "random" }, ease: "power2.in" }, "<+0.1")
        .to(".s2-break-2", { opacity: 1, y: 0, scale: 1, duration: 0.78 }, "+=0.1")
        .to(".s2-break-3", { opacity: 1, y: 0, scale: 1, duration: 0.82 }, "+=0.38");
    }, ref);
    return () => ctx.revert();
  }, []);
  return (
    <div ref={ref} className="absolute inset-0 overflow-hidden">
      {/* Thought field — same positions as Slide01 */}
      <div className="pointer-events-none absolute inset-0">
        {THOUGHTS.map((t) => (
          <div
            key={t.text}
            className={`absolute whitespace-nowrap font-medium tracking-[-0.02em] ${
              t.type === "idea"
                ? "s2-thought-idea text-[clamp(0.9rem,1.25vw,1.6rem)] text-[#ffd59a]"
                : "s2-thought text-[clamp(0.85rem,1.2vw,1.5rem)] text-white/80"
            }`}
            style={{ top: t.top, left: t.left }}
          >
            {t.text}
          </div>
        ))}
      </div>

      <div className="absolute inset-0 flex flex-col items-center justify-center px-10 text-center">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_85%_75%_at_50%_50%,rgba(2,6,23,0.62),transparent_82%)]" />
        <div className="relative max-w-3xl">
          <div className="space-y-4 text-[clamp(1.2rem,2.2vw,1.75rem)] leading-relaxed tracking-[-0.03em] text-slate-300">
            <p className="s2-bridge-1">You wind down for the day.</p>
            <p className="s2-bridge-2">The signal fades with it.</p>
            <p className="s2-bridge-3 text-slate-100">By morning, the thread is gone.</p>
          </div>
          <div className="mt-14 space-y-5">
            {(["Thoughts reset", "Good ideas die", "Continuity is lost"] as const).map((label, i) => (
              <div
                key={label}
                className={`s2-break-${i + 1} rounded-full border border-white/10 bg-white/[0.05] px-10 py-5 text-[clamp(1.8rem,3.5vw,3rem)] font-medium leading-none tracking-[-0.04em] text-white backdrop-blur-sm`}
              >
                {label}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Slide 03 — Sakhi reveal (thoughts converge into orb) ─────────────────────
function Slide03SakhiReveal() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const ctx = gsap.context(() => {
      gsap.set(".s3-thought", { opacity: 0.42 });
      gsap.set(".s3-orb-ring", { scale: 0.52, opacity: 0 });
      gsap.set(".s3-orb-core", { scale: 0, opacity: 0 });
      gsap.set(".s3-orb-glow", { opacity: 0 });
      gsap.set(".s3-headline", { opacity: 0, y: 18, scale: 0.95 });

      const tl = gsap.timeline({ defaults: { ease: "power2.in" } });
      tl
        // Thoughts converge from all quadrants into orb center
        .to(".s3-tl", { opacity: 0, scale: 0.18, x: 140, y: 90, filter: "blur(8px)", stagger: { each: 0.05, from: "random" }, duration: 1.1 }, 0.2)
        .to(".s3-tr", { opacity: 0, scale: 0.18, x: -140, y: 90, filter: "blur(8px)", stagger: { each: 0.05, from: "random" }, duration: 1.1 }, 0.3)
        .to(".s3-bl", { opacity: 0, scale: 0.18, x: 140, y: -90, filter: "blur(8px)", stagger: { each: 0.05, from: "random" }, duration: 1.1 }, 0.35)
        .to(".s3-br", { opacity: 0, scale: 0.18, x: -140, y: -90, filter: "blur(8px)", stagger: { each: 0.05, from: "random" }, duration: 1.1 }, 0.4)
        // Orb materialises as thoughts arrive
        .to(".s3-orb-glow", { opacity: 1, duration: 0.9, ease: "power2.out" }, 0.55)
        .to(".s3-orb-ring", { scale: 1, opacity: 1, duration: 0.72, stagger: 0.12, ease: "back.out(1.35)" }, 0.65)
        .to(".s3-orb-core", { scale: 1, opacity: 1, duration: 0.85, ease: "back.out(1.2)" }, 0.9)
        // Brief orb pulse on full formation
        .to(".s3-orb-core", { scale: 1.1, duration: 0.28, yoyo: true, repeat: 1, ease: "power1.inOut" }, 1.85)
        // Headline rises
        .to(".s3-headline", { opacity: 1, y: 0, scale: 1, duration: 1.0, ease: "power2.out" }, 2.15)
        // Orb recedes to background as headline owns the stage
        .to(".s3-orb-glow,.s3-orb-ring,.s3-orb-core", { opacity: 0.1, scale: 0.88, duration: 0.85, ease: "power1.in" }, "+=1.4");
    }, ref);
    return () => ctx.revert();
  }, []);

  return (
    <div ref={ref} className="absolute inset-0 overflow-hidden">
      {/* Scattered thoughts field — same positions as Slide01/02 */}
      <div className="pointer-events-none absolute inset-0">
        {THOUGHTS.map((t) => {
          const topVal = parseFloat(t.top);
          const leftVal = parseFloat(t.left);
          const quad = topVal < 50 ? (leftVal < 50 ? "s3-tl" : "s3-tr") : leftVal < 50 ? "s3-bl" : "s3-br";
          return (
            <div
              key={t.text}
              className={`s3-thought ${quad} absolute whitespace-nowrap font-medium tracking-[-0.02em] ${
                t.type === "idea"
                  ? "text-[clamp(0.9rem,1.25vw,1.6rem)] text-[#ffd59a]"
                  : "text-[clamp(0.85rem,1.2vw,1.5rem)] text-white/80"
              }`}
              style={{ top: t.top, left: t.left }}
            >
              {t.text}
            </div>
          );
        })}
      </div>

      {/* Sakhi orb — materialises at center as thoughts converge */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="s3-orb-glow pointer-events-none absolute h-[600px] w-[600px] rounded-full bg-[radial-gradient(circle,rgba(100,148,255,0.16),transparent_62%)]" />
        <div className="relative flex items-center justify-center">
          <div className="s3-orb-ring absolute h-[460px] w-[460px] rounded-full border border-white/[0.04]" />
          <div className="s3-orb-ring absolute h-[360px] w-[360px] rounded-full border border-white/[0.07]" />
          <div className="s3-orb-ring absolute h-[270px] w-[270px] rounded-full border border-white/[0.10]" />
          <div className="s3-orb-core relative flex h-[196px] w-[196px] items-center justify-center rounded-full border border-[#8ab0ff]/25 bg-[radial-gradient(circle_at_38%_32%,rgba(140,183,255,0.22),rgba(80,120,210,0.14)_48%,rgba(3,11,24,0.85)_78%)] shadow-[0_0_80px_rgba(100,148,255,0.22),0_0_160px_rgba(80,120,255,0.1)]">
            <div className="pointer-events-none absolute inset-[14%] rounded-full border border-white/[0.09]" />
            <span className="relative z-10 text-[13px] font-semibold tracking-[0.42em] text-[#8ab0ff]/90">SAKHI</span>
          </div>
        </div>
      </div>

      {/* Vignette + headline */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_62%_62%_at_50%_50%,rgba(2,6,23,0.38),transparent_74%)]" />
      <div className="absolute inset-0 flex items-center justify-center px-10">
        <h1 className="s3-headline relative z-10 max-w-[13ch] text-balance text-center text-[clamp(3.5rem,8vw,7.5rem)] font-semibold leading-[0.94] tracking-[-0.07em] text-white drop-shadow-[0_0_40px_rgba(255,255,255,0.06)]">
          Sakhi makes it all come together.
        </h1>
      </div>
    </div>
  );
}

// ── Slide 04 — Bridge ────────────────────────────────────────────────────────
function Slide04Bridge() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const ctx = gsap.context(() => {
      gsap.set(".s4-line-1,.s4-line-2", { opacity: 0, y: 22 });
      gsap.timeline({ defaults: { ease: "power2.out" } })
        .to(".s4-line-1", { opacity: 1, y: 0, duration: 0.85 }, 0.3)
        .to(".s4-line-2", { opacity: 1, y: 0, duration: 0.85 }, "+=0.6");
    }, ref);
    return () => ctx.revert();
  }, []);
  return (
    <div ref={ref} className="absolute inset-0 flex items-center justify-center px-10 text-center">
      <div className="max-w-4xl">
        <p className="s4-line-1 text-balance text-[clamp(2rem,3.8vw,3.5rem)] font-semibold leading-[1.1] tracking-[-0.04em] text-[#d5ddf4]">
          You do not have to be driven by your thoughts.
        </p>
        <p className="s4-line-2 mt-6 text-balance text-[clamp(1.8rem,3.2vw,3rem)] font-semibold leading-[1.1] tracking-[-0.04em] text-slate-300">
          You can shape them.
        </p>
      </div>
    </div>
  );
}

// ── Slide 05 — Stop reacting → pillars (mirrors Scene3Reveal animation) ──────
const PILLARS = [
  "Builds a living model of you. It evolves over time.",
  "Makes your life visible. Across time, as a whole.",
  "Helps you act decisively. It learns from what follows.",
] as const;

function Slide05StopReacting() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const ctx = gsap.context(() => {
      gsap.set(".s5-line-1", { opacity: 0, y: 0, scale: 1 });
      gsap.set(".s5-line-2", { opacity: 0, y: 24, scale: 0.982 });
      gsap.set(".s5-explainer", { opacity: 0, y: 28 });
      gsap.set(".s5-system", { opacity: 0, y: 28 });
      gsap.set(".s5-active", { opacity: 0, scale: 0.992, x: "3vw" });
      gsap.set(".s5-parked", { opacity: 0, y: 10, scale: 0.985 });
      gsap.set(".s5-parked-row", { opacity: 1, y: 0 });
      gsap.set(".s5-progress-wrap", { opacity: 1, y: 0 });
      gsap.set(".s5-progress", { scaleX: 0.3 });
      gsap.set(".s5-resolved", { opacity: 0.18, y: 110, scale: 0.94 });
      gsap.set(".s5-resolved-item", { opacity: 0.45, y: 0 });

      gsap.timeline({ defaults: { ease: "power2.out" } })
        .to(".s5-line-1", { opacity: 1, duration: 0.72 }, 0.2)
        .to(".s5-line-1", { opacity: 0, y: -30, scale: 0.94, duration: 0.65 }, "+=0.9")
        .to(".s5-line-2", { opacity: 1, y: 0, duration: 0.72 }, "-=0.14")
        .to({}, { duration: 2.0 })
        .to(".s5-explainer", { opacity: 1, y: 0, duration: 0.72 })
        .to({}, { duration: 3.2 })
        .to(".s5-system", { opacity: 1, y: 0, duration: 0.72 })
        .to(".s5-active-1", { opacity: 1, x: "0vw", scale: 1, duration: 0.55 }, "-=0.14")
        .to(".s5-progress-1", { scaleX: 1, duration: 0.48 }, "<")
        .to(".s5-active-1", { opacity: 0, x: "-10vw", scale: 0.96, duration: 0.58 }, "+=2.6")
        .to(".s5-parked-1", { opacity: 0.62, y: 0, scale: 1, duration: 0.42 }, "<")
        .to(".s5-active-2", { opacity: 1, x: "0vw", scale: 1, duration: 0.55 }, "-=0.14")
        .to(".s5-progress-2", { scaleX: 1, duration: 0.48 }, "<")
        .to(".s5-active-2", { opacity: 0, x: "0vw", scale: 0.96, duration: 0.58 }, "+=2.6")
        .to(".s5-parked-2", { opacity: 0.92, y: 0, scale: 1, duration: 0.42 }, "<")
        .to(".s5-active-3", { opacity: 1, x: "0vw", scale: 1, duration: 0.55 }, "-=0.14")
        .to(".s5-progress-3", { scaleX: 1, duration: 0.48 }, "<")
        .to(".s5-active-3", { opacity: 0, x: "10vw", scale: 0.96, duration: 0.58 }, "+=2.6")
        .to(".s5-parked-3", { opacity: 0.68, y: 0, scale: 1, duration: 0.42 }, "<")
        .to(".s5-explainer",    { opacity: 0.2, y: -12, duration: 0.7 }, "+=0.75")
        .to(".s5-progress-wrap", { opacity: 0, y: -18, duration: 0.7 }, "<")
        .to(".s5-parked-row",   { opacity: 0, y: -92, duration: 0.7, ease: "power2.inOut" }, "<")
        .to(".s5-resolved",     { opacity: 1, y: 0, scale: 1, duration: 0.72, ease: "power2.inOut" }, "<")
        .to(".s5-resolved-item", { opacity: 1, y: 0, stagger: 0.1, duration: 0.5 }, "<+0.1");
    }, ref);
    return () => ctx.revert();
  }, []);

  return (
    <div ref={ref} className="absolute inset-0 flex items-center justify-center overflow-hidden px-8 py-10 sm:px-12 lg:px-16 xl:px-20">
      <div className="mx-auto flex w-full max-w-6xl flex-col items-center text-center">
        <div className="w-full max-w-5xl">
          <div className="text-[clamp(4.2rem,10vw,8rem)] font-semibold leading-[0.92] tracking-[-0.075em] text-white">
            <div className="s5-line-1 text-white/84">Stop reacting.</div>
            <div className="s5-line-2 mt-1 text-white/14">Start shaping.</div>
          </div>
        </div>

        <div className="s5-explainer mt-14 w-full max-w-3xl">
          <p className="mx-auto max-w-2xl text-[clamp(1.2rem,2.1vw,1.7rem)] leading-[1.5] tracking-[-0.03em] text-slate-300">
            Sakhi learns how you think and evolves with you, so your decisions become clearer over time.
          </p>
        </div>

        <div className="s5-system mt-8 w-full">
          <div className="mx-auto max-w-4xl">
            <div className="relative min-h-[7rem] overflow-hidden sm:min-h-[8rem] lg:min-h-[9rem]">
              {PILLARS.map((pillar, i) => (
                <div key={pillar} className={`s5-active s5-active-${i + 1} absolute inset-0 flex items-center justify-center opacity-0`}>
                  <p className="mx-auto max-w-[16ch] text-center text-[clamp(2.1rem,4vw,3.7rem)] font-medium leading-[1.06] tracking-[-0.055em] text-white">
                    {pillar}
                  </p>
                </div>
              ))}
              <div className="s5-resolved absolute inset-0 flex items-center justify-center opacity-0">
                <div className="grid w-full max-w-5xl gap-6 md:grid-cols-[1fr_1.15fr_1fr] md:items-center">
                  {PILLARS.map((pillar, i) => (
                    <div key={`${pillar}-r`} className={i === 0 ? "text-left" : i === 1 ? "text-center" : "text-right"}>
                      <div className={`s5-resolved-item s5-resolved-item-${i + 1}`}>
                        <p className="text-pretty text-[clamp(1.15rem,1.55vw,1.65rem)] leading-[1.2] tracking-[-0.03em] text-slate-100/88">{pillar}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="s5-progress-wrap mt-4 flex items-center justify-center gap-3">
              {PILLARS.map((_, i) => (
                <div key={i} className="h-[2px] w-14 overflow-hidden rounded-full bg-white/10">
                  <div className={`s5-progress s5-progress-${i + 1} h-full origin-left rounded-full bg-[#c7d3ff]`} />
                </div>
              ))}
            </div>

            <div className="s5-parked-row mt-3 grid gap-4 md:grid-cols-[1fr_1.15fr_1fr] md:items-start">
              {PILLARS.map((pillar, i) => (
                <div key={`${pillar}-p`} className={i === 0 ? "text-left" : i === 1 ? "text-center" : "text-right"}>
                  <div className={`s5-parked s5-parked-${i + 1} opacity-0`}>
                    <p className="text-pretty text-[clamp(0.95rem,1.15vw,1.2rem)] leading-[1.25] tracking-[-0.025em] text-slate-200/72">{pillar}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Slide 06 — Continuity: noise → orb → occupancy → arc ────────────────────
const ARC_PHASES = [
  { label: "Where It Began", title: "An idea with ache",       body: "The thread began with one question: passing frustration, or something to build?", meta: "Day 12",                major: true  },
  { label: "Phase 1",        title: "Founder question",        body: "Could this become real?",                                                          meta: "Day 16",               major: false },
  { label: "Phase 2",        title: "Rhythm clicked",          body: "Rhythm, not remedies.",                                                            meta: "Day 19",               major: false },
  { label: "Phase 3",        title: "RAG felt brittle",        body: "The obvious path felt thin.",                                                      meta: "Day 24",               major: false },
  { label: "Phase 4",        title: "Knowledge graph",         body: "Slower, more respectful.",                                                         meta: "Day 28",               major: false },
  { label: "Phase 5",        title: "Still uneasy",            body: "Correct, but not personal.",                                                       meta: "Day 35",               major: false },
  { label: "Phase 6",        title: "Clarity surfaced",        body: "Reflection became the job.",                                                       meta: "Day 41",               major: false },
  { label: "Phase 7",        title: "Validation pressure",     body: "External pressure sharpened it.",                                                  meta: "Day 58",               major: false },
  { label: "Phase 8",        title: "Build, not pitch",        body: "Usage had to prove it.",                                                           meta: "Day 66",               major: false },
  { label: "Phase 9",        title: "Continuity core",         body: "The thread became the product.",                                                   meta: "Day 72",               major: false },
  { label: "Phase 10",       title: "Product shape",           body: "The path finally had form.",                                                       meta: "Day 115",              major: false },
  { label: "Where It Is Now",title: "A visible direction",     body: "The thread is no longer abstract. It now has form, continuity, and a next step.",  meta: "104 days of continuity", major: true },
] as const;

const ARC_DESKTOP_ORDER = [0, 1, 2, 3, 7, 6, 5, 4, 8, 9, 10, 11] as const;

const OCCUPANCY = [
  { label: "Start up",   share: "65%", moments: "28 moments", w: "22rem", h: "22rem", l: "28%", t: "55%", accent: true },
  { label: "Family",     share: "14%", moments: "6 moments",  w: "13rem", h: "13rem", l: "68%", t: "30%", accent: false },
  { label: "Caregiving", share: "7%",  moments: "3 moments",  w: "10rem", h: "10rem", l: "52%", t: "72%", accent: false },
  { label: "Career",     share: "7%",  moments: "3 moments",  w: "10rem", h: "10rem", l: "70%", t: "60%", accent: false },
  { label: "Self Care",  share: "7%",  moments: "3 moments",  w: "10rem", h: "10rem", l: "84%", t: "42%", accent: false },
] as const;

const S6_NOISE = [
  { text: "did I reply?",                   x: -610, y: -310, size: "md"  as const },
  { text: "my daughter lost a close game",  x: -420, y: -220, tone: "bright" as const, size: "sm" as const },
  { text: "skip dinner again?",             x: -720, y:  -50, size: "sm"  as const },
  { text: "Dad needs care",                 x: -560, y:   90, tone: "bright" as const, size: "md" as const },
  { text: "work pressure",                  x: -360, y:  240, size: "md"  as const },
  { text: "I forgot yoga",                  x: -670, y:  340, size: "md"  as const },
  { text: "how do I say this clearly?",     x: -110, y: -360, size: "lg"  as const },
  { text: "too many tabs open",             x:   90, y: -250, size: "md"  as const },
  { text: "what keeps repeating?",          x:  330, y: -310, tone: "bright" as const, size: "sm" as const },
  { text: "boardroom intensity",            x:  520, y: -140, size: "md"  as const },
  { text: "call mom back",                  x:  700, y:  -20, size: "sm"  as const },
  { text: "family guilt",                   x:  650, y:  150, size: "sm"  as const },
  { text: "I need to remember this",        x:  470, y:  310, size: "md"  as const },
  { text: "peace is available",             x:  170, y:  360, tone: "bright" as const, size: "sm" as const },
  { text: "what am I missing?",             x:  -50, y:  220, size: "sm"  as const },
  { text: "another meeting",                x:  720, y:  340, size: "sm"  as const },
  { text: "dentist for mom",                x: -760, y: -180, size: "sm"  as const },
  { text: "pitch deck feedback",            x: -250, y: -280, tone: "bright" as const, size: "sm" as const },
  { text: "have I followed up?",            x:  -30, y: -190, size: "sm"  as const },
  { text: "I need a clearer plan",          x:  220, y: -130, tone: "bright" as const, size: "md" as const },
  { text: "missed dinner with family",      x:  770, y:   80, size: "sm"  as const },
  { text: "when do I rest?",                x: -770, y:  220, size: "sm"  as const },
  { text: "motherhood feels like extension",x: -340, y:  175, tone: "bright" as const, size: "sm" as const },
  { text: "too much mental load",           x:   80, y:  290, size: "sm"  as const },
  { text: "I need to get back to them",     x:  260, y:  200, size: "md"  as const },
  { text: "this feels urgent",              x:  520, y:  230, tone: "bright" as const, size: "sm" as const },
  { text: "not another reactive answer",    x: -500, y: -150, size: "sm"  as const },
  { text: "hold it all together",           x: -300, y:  330, size: "sm"  as const },
  { text: "will this actually help?",       x:   10, y:  370, size: "sm"  as const },
  { text: "I said I would revisit this",    x:  690, y: -250, size: "sm"  as const },
  { text: "coming back after a gap",        x:  620, y: -340, size: "sm"  as const },
  { text: "what thread is this really?",    x: -700, y:   10, tone: "bright" as const, size: "sm" as const },
  { text: "emails before sunrise",          x: -290, y: -195, size: "sm"  as const },
  { text: "caregiving softness",            x:  420, y:  110, size: "sm"  as const },
  { text: "short-term clarity",             x:  380, y:  -55, tone: "bright" as const, size: "sm" as const },
  { text: "what did I promise?",            x: -390, y:   30, size: "sm"  as const },
];

function Slide06Continuity() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const ctx = gsap.context(() => {
      gsap.set(".s6-noise-item", {
        x: (_: number, el: Element) => Number((el as HTMLElement).dataset.x ?? 0),
        y: (_: number, el: Element) => Number((el as HTMLElement).dataset.y ?? 0),
        opacity: 0.88,
        scale: 1,
      });
      gsap.set(".s6-orb-shell", { opacity: 0, scale: 0.72 });
      gsap.set(".s6-orb-ring",  { opacity: 0.18, scale: 0.76, transformOrigin: "center center" });
      gsap.set(".s6-orb-label", { opacity: 0, y: 10 });
      gsap.set(".s6-output",    { opacity: 0, y: 26 });
      gsap.set(".s6-board",     { opacity: 0, y: 26, scale: 0.97 });
      gsap.set(".s6-board-shell",{ opacity: 0, y: 16 });
      gsap.set(".s6-board-copy", { opacity: 0, y: 12 });
      gsap.set(".s6-bubble",    { opacity: 0, y: 18, scale: 0.76, transformOrigin: "center center" });
      gsap.set(".s6-arc-stage", { opacity: 0 });
      gsap.set(".s6-arc-shell", { opacity: 0, y: 24, scale: 0.97 });
      gsap.set(".s6-arc-kicker",{ opacity: 0, y: 12 });
      gsap.set(".s6-arc-card",  { opacity: 0, y: 16 });

      gsap.timeline({ defaults: { ease: "power2.out" } })
        .to(".s6-orb-shell", { opacity: 1, scale: 1, duration: 0.62 }, 0)
        .to(".s6-orb-label", { opacity: 1, y: 0, duration: 0.4 }, "-=0.28")
        .to(".s6-orb-ring",  { opacity: 0.36, scale: 1, stagger: 0.04, duration: 0.54 }, "<")
        .to({}, { duration: 0.22 })
        .to(".s6-noise-item", {
          x: 0, y: 0, opacity: 0, scale: 0.52,
          stagger: { each: 0.015, from: "random" },
          duration: 0.5,
          ease: "power3.in",
        })
        .to(".s6-orb-shell", { scale: 1.08, duration: 0.36, ease: "power2.out" }, "-=0.32")
        .to(".s6-orb-shell", { opacity: 0, duration: 0.3, ease: "power2.out" }, "-=0.04")
        .to(".s6-output",    { opacity: 1, y: 0, duration: 0.42 }, "-=0.02")
        .to(".s6-board",     { opacity: 1, y: 0, scale: 1, duration: 0.54 }, "<+0.02")
        .to(".s6-board-shell",{ opacity: 1, y: 0, duration: 0.36 }, "-=0.06")
        .to(".s6-board-copy", { opacity: 1, y: 0, duration: 0.28 }, "-=0.22")
        .to(".s6-bubble", {
          opacity: 1, scale: 1, y: 0,
          stagger: { each: 0.08, from: "center" },
          duration: 0.44,
          ease: "back.out(1.32)",
        }, "-=0.06")
        .to({}, { duration: 3.5 })
        .to(".s6-bubble:not(.s6-startup-bubble)", { opacity: 0.14, scale: 0.84, stagger: 0.03, duration: 0.32 })
        .to(".s6-startup-bubble", { scale: 1.18, duration: 0.34, ease: "power2.out" }, "<")
        .to(".s6-board",     { opacity: 0, scale: 1.02, duration: 0.38 }, "+=0.04")
        .to(".s6-arc-stage", { opacity: 1, duration: 0.18 }, "-=0.12")
        .to(".s6-arc-shell", { opacity: 1, y: 0, scale: 1, duration: 0.46 }, "<")
        .to(".s6-arc-kicker",{ opacity: 1, y: 0, duration: 0.28 }, "-=0.26")
        .to(".s6-arc-card",  { opacity: 1, y: 0, stagger: 0.055, duration: 0.42 }, "<+0.15");
    }, ref);
    return () => ctx.revert();
  }, []);

  return (
    <div ref={ref} className="absolute inset-0 overflow-hidden">
      <div className="pointer-events-none absolute inset-0">
        {S6_NOISE.map((n) => (
          <div
            key={n.text}
            className={`s6-noise-item absolute left-1/2 top-1/2 whitespace-nowrap rounded-full border font-medium tracking-[-0.02em] ${"tone" in n && n.tone === "bright"
              ? "border-[#c8d7ff]/16 bg-[#c8d7ff]/6 text-[#dce6ff]/80"
              : "border-white/8 bg-white/[0.03] text-white/38"
            } ${n.size === "lg" ? "px-6 py-3 text-[clamp(1rem,1.2vw,1.3rem)]"
              : n.size === "sm" ? "px-3 py-[0.45rem] text-[clamp(0.72rem,0.82vw,0.88rem)]"
              : "px-4 py-2 text-[clamp(0.85rem,1vw,1rem)]"
            }`}
            data-x={n.x}
            data-y={n.y}
          >
            {n.text}
          </div>
        ))}
      </div>

      <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
        <div className="s6-orb-shell relative flex h-36 w-36 items-center justify-center rounded-full border border-[#8cb7ff]/35 bg-[radial-gradient(circle_at_center,rgba(140,183,255,0.28),rgba(100,145,230,0.14)_44%,rgba(7,11,21,0.88)_78%)] shadow-[0_0_60px_rgba(140,183,255,0.32),0_0_120px_rgba(140,183,255,0.12)]">
          <div className="s6-orb-ring absolute inset-[-18px] rounded-full border border-[#8cb7ff]/20" />
          <div className="s6-orb-ring absolute inset-[-34px] rounded-full border border-[#8cb7ff]/10" />
          <div className="s6-orb-label relative z-10 text-center">
            <div className="text-[0.9rem] font-semibold uppercase tracking-[0.38em] text-[#8cb7ff]/90">Sakhi</div>
          </div>
        </div>
      </div>

      <div className="s6-output absolute inset-0">
        <div className="s6-board absolute inset-4 sm:inset-6 lg:inset-8">
          <div className="s6-board-shell relative h-full overflow-hidden rounded-[32px] border border-white/[0.09] bg-[linear-gradient(158deg,rgba(12,17,30,0.98),rgba(7,10,20,0.96))] p-5 sm:p-7">
            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_60%_50%_at_15%_10%,rgba(110,148,230,0.14),transparent),radial-gradient(ellipse_50%_45%_at_88%_92%,rgba(105,78,55,0.12),transparent)]" />
            <div className="s6-board-copy relative z-10 flex items-start justify-between">
              <div>
                <div className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-1 text-[8px] font-semibold uppercase tracking-[0.28em] text-white/40">
                  <span className="h-1.5 w-1.5 rounded-full bg-[#8cb7ff]/70" />Vidhya · Profile
                </div>
                <div className="mt-3 text-[clamp(1.6rem,2.8vw,2.2rem)] font-semibold tracking-[-0.05em] text-white">Life Occupancy</div>
                <p className="mt-1 text-[clamp(0.8rem,1.1vw,1rem)] text-white/44">Bubble size reflects how much each thread has occupied your attention.</p>
              </div>
              <div className="rounded-xl border border-white/[0.09] bg-white/[0.03] px-3 py-2 text-right">
                <div className="text-[8px] font-semibold uppercase tracking-[0.26em] text-white/30">Active</div>
                <div className="mt-1 text-sm font-semibold tracking-[-0.04em] text-white/82">5 threads</div>
              </div>
            </div>
            <div className="relative z-10 mt-2" style={{ height: "calc(100% - 7rem)" }}>
              {OCCUPANCY.map((b) => (
                <div
                  key={b.label}
                  className={`s6-bubble ${b.accent ? "s6-startup-bubble" : ""} absolute -translate-x-1/2 -translate-y-1/2 flex flex-col items-center justify-center rounded-full text-center ${
                    b.accent
                      ? "border border-[#dce8ff]/50 bg-[radial-gradient(circle_at_36%_28%,rgba(235,242,255,0.19),rgba(165,190,235,0.26)_48%,rgba(55,72,108,0.38))] shadow-[0_0_80px_rgba(148,178,255,0.18)]"
                      : "border border-white/[0.11] bg-[radial-gradient(circle_at_36%_28%,rgba(255,255,255,0.08),rgba(255,255,255,0.022)_72%)] backdrop-blur-sm"
                  }`}
                  style={{ width: b.w, height: b.h, left: b.l, top: b.t, zIndex: b.accent ? 4 : 2 }}
                >
                  <div className={`font-semibold tracking-[-0.03em] text-white/88 ${b.accent ? "text-[1rem]" : "text-[0.82rem]"}`}>{b.label}</div>
                  <div className={`leading-none tracking-[-0.07em] text-white ${b.accent ? "text-[clamp(2.8rem,5vw,4rem)] font-bold" : "text-[clamp(1.6rem,2.8vw,2.2rem)] font-bold"}`}>{b.share}</div>
                  <div className={`tracking-[-0.01em] ${b.accent ? "text-[0.85rem] text-white/55" : "text-[0.72rem] text-white/40"}`}>{b.moments}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="s6-arc-stage absolute inset-x-4 inset-y-4 flex flex-col justify-center sm:inset-x-6 lg:inset-x-8">
          <div className="s6-arc-shell relative overflow-hidden rounded-[28px] border border-[#8cb7ff]/10 bg-[linear-gradient(158deg,rgba(11,17,32,0.97),rgba(7,10,20,0.96))] px-5 py-4 shadow-[0_44px_130px_rgba(0,0,0,0.42)] sm:px-6 sm:py-5">
            <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-[linear-gradient(90deg,transparent,rgba(140,183,255,0.35)_30%,rgba(180,210,255,0.5)_50%,rgba(140,183,255,0.35)_70%,transparent)]" />
            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_60%_45%_at_15%_0%,rgba(108,145,225,0.14),transparent)]" />
            <div className="s6-arc-kicker relative z-10 mb-3 flex items-center gap-2.5">
              <div className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-1 text-[8px] font-semibold uppercase tracking-[0.28em] text-white/40">
                <span className="h-1.5 w-1.5 rounded-full bg-[#8cb7ff]/70" />Start up
              </div>
              <div className="text-[1.15rem] font-semibold tracking-[-0.04em] text-white">Continuity Arc</div>
            </div>
            <div className="relative z-10 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:hidden">
              {ARC_PHASES.map((phase) => (
                <div key={phase.label} className={`s6-arc-card rounded-[14px] border px-3 py-3 ${phase.major ? "border-[#8cb7ff]/25 bg-[#8cb7ff]/[0.06]" : "border-white/[0.07] bg-white/[0.02]"}`}>
                  <div className={`text-[7px] font-semibold uppercase tracking-[0.2em] ${phase.major ? "text-[#8cb7ff]/70" : "text-white/28"}`}>{phase.label}</div>
                  <div className={`mt-1 font-semibold tracking-[-0.03em] text-white ${phase.major ? "text-[0.82rem]" : "text-[0.72rem]"}`}>{phase.title}</div>
                  <div className={`mt-1 text-[7px] font-semibold uppercase tracking-[0.18em] ${phase.major ? "text-[#8cb7ff]/80" : "text-[#8cb7ff]/50"}`}>{phase.meta}</div>
                </div>
              ))}
            </div>
            <div className="relative hidden lg:block">
              <div className="pointer-events-none absolute inset-0 z-0">
                <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="h-full w-full" aria-hidden="true">
                  {[
                    "M24.7 16.7 L26.5 16.7", "M49.1 16.7 L50.9 16.7", "M73.5 16.7 L75.3 16.7",
                    "M97.9 16.7 L99.4 16.7 L99.4 50 L97.9 50",
                    "M75.3 50 L73.5 50", "M50.9 50 L49.1 50", "M26.5 50 L24.7 50",
                    "M2.1 50 L0.6 50 L0.6 83.3 L2.1 83.3",
                    "M24.7 83.3 L26.5 83.3", "M49.1 83.3 L50.9 83.3", "M73.5 83.3 L75.3 83.3",
                  ].map((d, i) => (
                    <g key={i}>
                      <path d={d} fill="none" stroke="rgba(140,183,255,0.18)" strokeWidth="1.1" strokeLinecap="round" strokeLinejoin="round" />
                      <path d={d} fill="none" stroke="rgba(180,210,255,0.6)" strokeWidth="0.45" strokeDasharray="1.2 1.5" strokeLinecap="round" strokeLinejoin="round" />
                    </g>
                  ))}
                </svg>
              </div>
              <div className="relative z-10 grid grid-cols-4 gap-3 px-6">
                {ARC_DESKTOP_ORDER.map((idx) => {
                  const phase = ARC_PHASES[idx];
                  return (
                    <div key={phase.label} className={`s6-arc-card rounded-[16px] border px-3.5 py-3.5 ${phase.major ? "border-[#8cb7ff]/25 bg-[#8cb7ff]/[0.06]" : "border-white/[0.07] bg-white/[0.02]"}`}>
                      <div className={`text-[7px] font-semibold uppercase tracking-[0.2em] ${phase.major ? "text-[#8cb7ff]/70" : "text-white/28"}`}>{phase.label}</div>
                      <div className={`mt-1.5 font-semibold tracking-[-0.04em] text-white ${phase.major ? "text-[0.88rem]" : "text-[0.75rem]"}`}>{phase.title}</div>
                      <p className={`mt-1.5 leading-[1.4] ${phase.major ? "text-[0.72rem] text-white/68" : "text-[0.66rem] text-white/40"}`}>{phase.body}</p>
                      <div className={`mt-2 text-[7px] font-semibold uppercase tracking-[0.2em] ${phase.major ? "text-[#8cb7ff]/80" : "text-[#8cb7ff]/50"}`}>{phase.meta}</div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Slide 07 — Life connected ────────────────────────────────────────────────
const LIFE_LINES = [
  "Noise becomes pattern.",
  "Pattern becomes readable occupancy.",
  "The system gathers scattered moments and returns which threads have actually occupied your life.",
  "So it shows not just what is happening now, but what has been taking up space across time.",
  "This is where scattered life becomes coherent.",
] as const;

function Slide07LifeConnected() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const ctx = gsap.context(() => {
      gsap.set(".s7-kicker,.s7-headline,.s7-line", { opacity: 0, y: 20 });
      gsap.timeline({ defaults: { ease: "power2.out" } })
        .to(".s7-kicker", { opacity: 1, y: 0, duration: 0.5 }, 0.2)
        .to(".s7-headline", { opacity: 1, y: 0, duration: 0.85 }, "+=0.1")
        .to(".s7-line", { opacity: 1, y: 0, stagger: 0.22, duration: 0.65 }, "+=0.5");
    }, ref);
    return () => ctx.revert();
  }, []);
  return (
    <div ref={ref} className="absolute inset-0 flex items-center overflow-hidden px-10 py-12 sm:px-14 lg:px-20">
      <div className="max-w-4xl">
        <p className="s7-kicker mb-5 text-[10px] font-semibold uppercase tracking-[0.3em] text-[#8ab0ff]/80">Continuity</p>
        <h2 className="s7-headline text-[clamp(3.2rem,6vw,5.5rem)] font-semibold leading-[0.98] tracking-[-0.06em] text-white">
          Your life, connected across time.
        </h2>
        <div className="mt-10 space-y-4">
          {LIFE_LINES.map((line, i) => (
            <p
              key={line}
              className={`s7-line text-[clamp(1rem,1.6vw,1.35rem)] leading-[1.55] tracking-[-0.025em] ${
                i === LIFE_LINES.length - 1 ? "font-medium text-white" : "text-white/60"
              }`}
            >
              {line}
            </p>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Slide 08 — First expression ───────────────────────────────────────────────
function Slide08FirstExpression() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const ctx = gsap.context(() => {
      gsap.set(".s8-text,.s8-sub", { opacity: 0, y: 24 });
      gsap.timeline({ defaults: { ease: "power2.out" } })
        .to(".s8-text", { opacity: 1, y: 0, duration: 1.0 }, 0.3)
        .to(".s8-sub", { opacity: 1, y: 0, duration: 0.8 }, "+=0.5");
    }, ref);
    return () => ctx.revert();
  }, []);
  return (
    <div ref={ref} className="absolute inset-0 flex items-center justify-center px-10 text-center">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_22%,rgba(139,160,255,0.14),transparent_28%)]" />
      <div>
        <p className="s8-text text-balance text-[clamp(3rem,7.5vw,7rem)] font-semibold leading-[0.96] tracking-[-0.06em] text-white">
          First expression of Sakhi.
        </p>
        <p className="s8-sub mt-6 text-[clamp(1rem,1.6vw,1.4rem)] text-white/50">
          Conversation, reflection, continuity, and privacy.
        </p>
      </div>
    </div>
  );
}

// ── Slides 09–12 — Product panels ────────────────────────────────────────────
const PRODUCT_PANELS = [
  {
    label: "Conversation",
    headline: "Start talking. Sakhi does the rest.",
    lead: "It keeps the thread.",
    details: ["It builds over time.", "It evolves with you."],
    src: "/story/chat.png",
    caption: "Start anywhere. Sakhi keeps the thread.",
  },
  {
    label: "Reflection",
    headline: "Your life becomes visible.",
    lead: "Across time and topics, everything connects.",
    details: ["What you have lived begins to form patterns.", "Not just moments, but something you can understand."],
    src: "/story/reflection.png",
    caption: "Threads emerge from what you have actually lived.",
  },
  {
    label: "Continuity",
    headline: "Your story starts to take shape.",
    lead: "Each thread becomes something you can return to, and build on.",
    details: ["What you have lived stays connected, forming a timeline you can move through.", "And over time, those moments begin to form your story."],
    src: "/story/continuity.PNG",
    caption: "Continuity becomes visible across what you have lived.",
  },
  {
    label: "Privacy",
    headline: "What you share stays yours.",
    lead: "Your conversations are yours, not ours.",
    details: ["End-to-end encrypted.", "No one reads your conversations.", "Not even Sakhi."],
    src: "/story/vidz-space.png",
    caption: "Private by default.",
  },
] as const;

function SlideProduct({ panelIndex }: { panelIndex: number }) {
  const panel = PRODUCT_PANELS[panelIndex];
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const ctx = gsap.context(() => {
      gsap.set(".sp-badge,.sp-headline,.sp-lead,.sp-detail,.sp-phone", { opacity: 0, y: 22 });
      gsap.timeline({ defaults: { ease: "power2.out" } })
        .to(".sp-badge", { opacity: 1, y: 0, duration: 0.5 }, 0.15)
        .to(".sp-headline", { opacity: 1, y: 0, duration: 0.78 }, "+=0.1")
        .to(".sp-lead", { opacity: 1, y: 0, duration: 0.68 }, "+=0.2")
        .to(".sp-detail", { opacity: 1, y: 0, stagger: 0.14, duration: 0.6 }, "+=0.2")
        .to(".sp-phone", { opacity: 1, y: 0, duration: 0.85 }, "<-0.3");
    }, ref);
    return () => ctx.revert();
  }, []);
  return (
    <div ref={ref} className="absolute inset-0 flex items-center overflow-hidden px-8 py-10 sm:px-12 lg:px-16 xl:px-20">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_14%_18%,rgba(84,122,142,0.15),transparent_32%),radial-gradient(circle_at_86%_82%,rgba(153,112,58,0.10),transparent_25%)]" />
      <div className="relative mx-auto flex w-full max-w-5xl items-center justify-center gap-8 lg:gap-12">
        {/* Text — left */}
        <div className="relative z-10 max-w-[380px] flex-1">
          <div className="sp-badge inline-flex items-center gap-2.5 rounded-full border border-white/10 bg-white/[0.05] px-4 py-2.5 text-[10px] font-semibold uppercase tracking-[0.28em] text-[#b9c9e8]">
            <span className="h-2.5 w-2.5 rounded-full bg-[#dce7f8] shadow-[0_0_16px_rgba(220,231,248,0.3)]" />
            {panel.label}
          </div>
          <h2 className="sp-headline mt-6 max-w-[12ch] text-balance text-[clamp(2rem,3.2vw,3.6rem)] font-extrabold leading-[0.96] tracking-[-0.055em] text-white">
            {panel.headline}
          </h2>
          <p className="sp-lead mt-5 max-w-[18ch] text-balance text-[clamp(1rem,1.4vw,1.6rem)] font-semibold leading-[1.5] tracking-[-0.03em] text-slate-100">
            {panel.lead}
          </p>
          <div className="mt-4 space-y-3 text-[clamp(0.88rem,1.1vw,1.15rem)] leading-[1.62] tracking-[-0.02em] text-slate-300">
            {panel.details.map((d) => (
              <p key={d} className="sp-detail max-w-[30ch] text-balance">{d}</p>
            ))}
          </div>
        </div>
        {/* Phone — right */}
        <div className="sp-phone relative z-10 hidden flex-none flex-col items-center self-center md:flex">
          <div
            className="relative flex flex-col items-center rounded-[40px] border border-[rgba(189,206,225,0.12)] bg-[linear-gradient(180deg,rgba(18,28,45,0.78),rgba(8,13,24,0.54))] shadow-[inset_0_1px_0_rgba(255,255,255,0.05),0_20px_60px_rgba(0,0,0,0.28)]"
            style={{ padding: "14px 14px 18px" }}
          >
            <div className="mb-3 h-[5px] w-[80px] rounded-full bg-white/10" />
            <div
              className="relative overflow-hidden rounded-[32px] border border-[rgba(203,213,225,0.16)] bg-[#040914] shadow-[0_36px_90px_rgba(0,0,0,0.55)]"
              style={{ width: "min(clamp(200px,22vw,340px), calc((100vh - 200px) * 0.5625))" }}
            >
              <Image src={panel.src} alt={panel.label} width={720} height={1280} className="block h-auto w-full" />
            </div>
          </div>
          <p className="mt-3 max-w-[220px] text-center text-[12px] leading-[1.5] text-slate-500">{panel.caption}</p>
        </div>
      </div>
    </div>
  );
}

// ── Slide 13 — Vision (mirrors Scene6Vision animation) ───────────────────────
const VISION_PILLAR_LINES = [
  "Build a living model of you evolving over time.",
  "Make your life visible across time, as a whole.",
  "Help you act decisively and learn from what follows.",
] as const;
const VISION_VOICE_LINES = ["I see you.", "I understand you.", "I act for you."] as const;
const VISION_VOICE_OFFSETS: Record<number, string> = { 0: "22vw", 1: "0vw", 2: "-22vw" };

function Slide13Vision() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const ctx = gsap.context(() => {
      gsap.set(".s13-p1",          { opacity: 0, y: 0,  scale: 1 });
      gsap.set(".s13-p2",          { opacity: 0, y: 24, scale: 0.982 });
      gsap.set(".s13-stage",       { opacity: 0, y: 20 });
      gsap.set(".s13-card",        { opacity: 0, y: 18 });
      gsap.set(".s13-voice-1",     { opacity: 0, x: VISION_VOICE_OFFSETS[0], scale: 0.42, filter: "blur(10px)" });
      gsap.set(".s13-voice-2",     { opacity: 0, x: VISION_VOICE_OFFSETS[1], scale: 0.42, filter: "blur(10px)" });
      gsap.set(".s13-voice-3",     { opacity: 0, x: VISION_VOICE_OFFSETS[2], scale: 0.42, filter: "blur(10px)" });
      gsap.set(".s13-signoff",     { opacity: 0, y: 20 });

      const voicePop = (i: number) =>
        gsap.timeline().fromTo(
          `.s13-voice-${i}`,
          { opacity: 0, x: VISION_VOICE_OFFSETS[i - 1], scale: 0.42, filter: "blur(10px)" },
          { opacity: 1, x: "0vw", scale: 1, filter: "blur(0px)", duration: 0.86, ease: "back.out(1.55)" },
        );

      gsap.timeline({ defaults: { ease: "power2.out" } })
        .to(".s13-p1",     { opacity: 1, y: 0,  duration: 0.72 }, 0.2)
        .to({}, { duration: 2.0 })
        .to(".s13-p2",     { opacity: 1, y: 0, scale: 1, duration: 0.72 })
        .to({}, { duration: 2.0 })
        .to(".s13-stage",  { opacity: 1, y: 0, duration: 0.4 }, "-=0.12")
        .to(".s13-card",   { opacity: 1, y: 0, stagger: 0.12, duration: 0.62 }, "<+0.06")
        .to({}, { duration: 2.0 })
        .add(voicePop(1))
        .to({}, { duration: 1.8 })
        .add(voicePop(2))
        .to({}, { duration: 1.8 })
        .add(voicePop(3))
        .to({}, { duration: 2.2 })
        .to(".s13-signoff", { opacity: 1, y: 0, duration: 0.72 });
    }, ref);
    return () => ctx.revert();
  }, []);
  return (
    <div ref={ref} className="absolute inset-0 flex items-center overflow-hidden px-8 py-10 sm:px-12 lg:px-16 xl:px-20">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_18%,rgba(162,179,255,0.16),transparent_24%),radial-gradient(circle_at_20%_70%,rgba(108,128,255,0.1),transparent_28%),radial-gradient(circle_at_78%_72%,rgba(112,205,255,0.08),transparent_30%)]" />
      <div className="relative mx-auto flex w-full max-w-6xl flex-col items-center text-center">
        <div className="w-full">
          <div className="text-[clamp(1.5rem,2.4vw,2.4rem)] font-medium leading-[1.3] tracking-[-0.03em] text-slate-300/80">
            <div className="s13-p1">Sakhi makes your life seen,</div>
            <div className="s13-p2">understood, and actionable.</div>
          </div>
        </div>
        <div className="s13-stage mt-10 w-full max-w-5xl">
          <div className="grid gap-5 md:grid-cols-[1fr_1.15fr_1fr] md:items-stretch">
            {VISION_PILLAR_LINES.map((line, i) => (
              <div key={line} className={i === 0 ? "text-left" : i === 1 ? "text-center" : "text-right"}>
                <div className={`s13-card flex h-full flex-col`}>
                  <p className={`s13-voice-${i + 1} text-[clamp(2.4rem,4vw,4.2rem)] font-semibold leading-[1.06] tracking-[-0.055em] text-white`}>
                    {VISION_VOICE_LINES[i]}
                  </p>
                  <p className="mt-4 text-pretty text-[clamp(0.92rem,1.18vw,1.15rem)] leading-[1.4] tracking-[-0.02em] text-slate-300/72">
                    {line}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="s13-signoff mt-10">
          <p className="text-[0.95rem] font-medium uppercase tracking-[0.28em] text-[#c8d4ff]/78">— Sakhi</p>
        </div>
      </div>
    </div>
  );
}

// ── Slide 14 — Founder bridge ─────────────────────────────────────────────────
function Slide14FounderBridge() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const ctx = gsap.context(() => {
      gsap.set(".s14b-kicker,.s14b-headline", { opacity: 0, y: 18 });
      gsap.timeline({ defaults: { ease: "power2.out" } })
        .to(".s14b-kicker", { opacity: 1, y: 0, duration: 0.55 }, 0.2)
        .to(".s14b-headline", { opacity: 1, y: 0, duration: 0.9 }, "+=0.12");
    }, ref);
    return () => ctx.revert();
  }, []);
  return (
    <div ref={ref} className="absolute inset-0 flex items-center justify-center overflow-hidden px-8 py-10 sm:px-12 lg:px-16 xl:px-20">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_24%,rgba(162,179,255,0.12),transparent_24%),radial-gradient(circle_at_16%_78%,rgba(108,128,255,0.07),transparent_28%),radial-gradient(circle_at_84%_78%,rgba(112,205,255,0.06),transparent_28%)]" />
      <div className="relative mx-auto max-w-5xl text-center">
        <p className="s14b-kicker text-[10px] font-semibold uppercase tracking-[0.34em] text-[#c8d4ff]/72 sm:text-[11px]">
          Founders
        </p>
        <h2
          className="s14b-headline mt-6 text-balance font-semibold leading-[0.96] tracking-[-0.06em] text-white"
          style={{ fontSize: "clamp(3rem, 7vw, 6rem)" }}
        >
          The Minds Behind...
        </h2>
      </div>
    </div>
  );
}

// ── Slide 15 — Vidhya quote ───────────────────────────────────────────────────
function Slide14VidhyaQuote() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const ctx = gsap.context(() => {
      gsap.set(".s14-portrait,.s14-meta,.s14-quote", { opacity: 0, y: 18 });
      gsap.timeline({ defaults: { ease: "power2.out" } })
        .to(".s14-portrait", { opacity: 1, y: 0, duration: 0.85 }, 0.2)
        .to(".s14-meta", { opacity: 1, y: 0, duration: 0.6 }, "+=0.1")
        .to(".s14-quote", { opacity: 1, y: 0, duration: 0.9 }, "+=0.2");
    }, ref);
    return () => ctx.revert();
  }, []);
  return (
    <div ref={ref} className="absolute inset-0 flex items-center overflow-hidden px-8 py-10 sm:px-12 lg:px-16 xl:px-20">
      <div className="mx-auto grid w-full max-w-[88rem] items-center gap-8 lg:grid-cols-[minmax(13rem,0.55fr)_minmax(0,1.45fr)] lg:gap-12">
        <div className="s14-portrait mx-auto w-[13rem] lg:mx-0 lg:w-[14.5rem]">
          <div className="relative rounded-[30px] border border-white/10 bg-white/[0.03] p-2.5 shadow-[0_36px_90px_rgba(0,0,0,0.42)]">
            <div className="relative aspect-[3/4] overflow-hidden rounded-[24px]">
              <Image src="/story/v-pic-20260327.png" alt="Vidhya" fill className="object-cover object-center" />
            </div>
            <div className="s14-meta mt-2.5 rounded-[16px] border border-white/10 bg-[rgba(7,11,18,0.7)] px-3.5 py-2.5">
              <div className="text-sm font-semibold text-white">Vidhya</div>
              <div className="mt-0.5 text-[10px] font-medium uppercase tracking-[0.18em] text-[#c4d2ff]/72">Co-Founder &amp; CEO</div>
              <div className="mt-1.5 text-[12px] leading-[1.5] text-white/62">Built systems for companies. Now building one for humans.</div>
            </div>
          </div>
        </div>
        <div className="text-center lg:text-left">
          <h2 className="s14-quote max-w-[16ch] text-balance text-[clamp(2.2rem,3.5vw,4.5rem)] font-semibold leading-[0.96] tracking-[-0.06em] text-white lg:max-w-[15ch]">
            I&apos;ve spent 20+ years helping organizations make better decisions. I realized we haven&apos;t solved this for individuals.
          </h2>
        </div>
      </div>
    </div>
  );
}

// ── Slide 16 — Vidhya arc ────────────────────────────────────────────────────
const VIDHYA_ARC = [
  { label: "Operator at Scale", body: "Worked alongside CEOs and COOs, building systems that turned ambiguity into structured decisions." },
  { label: "Personal Inflection Point", body: "In 2024, caregiving, leadership, and life complexity collided. What was missing was continuity at the level of a real human life." },
  { label: "Insight to Sakhi", body: "Small, personalized interventions changed everything. Timing and personalization mattered more than generic advice. The question became: can this be built as a system?" },
] as const;

function Slide15VidhyaArc() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const ctx = gsap.context(() => {
      gsap.set(".s15-kicker,.s15-step,.s15-final", { opacity: 0, y: 16 });
      gsap.timeline({ defaults: { ease: "power2.out" } })
        .to(".s15-kicker", { opacity: 1, y: 0, duration: 0.55 }, 0.2)
        .to(".s15-step", { opacity: 1, y: 0, stagger: 0.2, duration: 0.7 }, "+=0.2")
        .to(".s15-final", { opacity: 1, y: 0, duration: 0.7 }, "+=0.3");
    }, ref);
    return () => ctx.revert();
  }, []);
  return (
    <div ref={ref} className="absolute inset-0 flex items-center overflow-hidden px-8 py-10 sm:px-12 lg:px-16 xl:px-20">
      <div className="mx-auto grid w-full max-w-[88rem] items-center gap-8 lg:grid-cols-[minmax(13rem,0.55fr)_minmax(0,1.45fr)] lg:gap-12">
        <div className="mx-auto w-[13rem] opacity-70 lg:mx-0 lg:w-[14.5rem]">
          <div className="relative rounded-[30px] border border-white/10 bg-white/[0.03] p-2.5 shadow-[0_36px_90px_rgba(0,0,0,0.42)]">
            <div className="relative aspect-[3/4] overflow-hidden rounded-[24px]">
              <Image src="/story/v-pic-20260327.png" alt="Vidhya" fill className="object-cover object-center" />
            </div>
            <div className="mt-2.5 rounded-[16px] border border-white/10 bg-[rgba(7,11,18,0.7)] px-3.5 py-2.5">
              <div className="text-sm font-semibold text-white">Vidhya</div>
              <div className="mt-0.5 text-[10px] font-medium uppercase tracking-[0.18em] text-[#c4d2ff]/72">Co-Founder &amp; CEO</div>
            </div>
          </div>
        </div>
        <div>
          <p className="s15-kicker text-[10px] font-semibold uppercase tracking-[0.34em] text-[#c4d2ff]">Building From Lived Experience</p>
          <div className="mt-5 grid gap-4 sm:grid-cols-3">
            {VIDHYA_ARC.map((step) => (
              <div key={step.label} className="s15-step rounded-[22px] border border-white/[0.08] bg-white/[0.03] px-5 py-5">
                <p className="text-sm font-semibold text-white">{step.label}</p>
                <p className="mt-2.5 text-[0.88rem] leading-[1.65] text-white/55">{step.body}</p>
              </div>
            ))}
          </div>
          <p className="s15-final mt-6 text-[1.05rem] font-medium leading-7 tracking-[-0.02em] text-white">
            &quot;Sakhi is the system I wish existed when I needed it most.&quot;
          </p>
        </div>
      </div>
    </div>
  );
}

// ── Slide 17 — Ravi quote ────────────────────────────────────────────────────
function Slide16RaviQuote() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const ctx = gsap.context(() => {
      gsap.set(".s16-portrait,.s16-meta,.s16-quote", { opacity: 0, y: 18 });
      gsap.timeline({ defaults: { ease: "power2.out" } })
        .to(".s16-portrait", { opacity: 1, y: 0, duration: 0.85 }, 0.2)
        .to(".s16-meta", { opacity: 1, y: 0, duration: 0.6 }, "+=0.1")
        .to(".s16-quote", { opacity: 1, y: 0, duration: 0.9 }, "+=0.2");
    }, ref);
    return () => ctx.revert();
  }, []);
  return (
    <div ref={ref} className="absolute inset-0 flex items-center overflow-hidden px-8 py-10 sm:px-12 lg:px-16 xl:px-20">
      <div className="mx-auto grid w-full max-w-[88rem] items-center gap-8 lg:grid-cols-[minmax(13rem,0.55fr)_minmax(0,1.45fr)] lg:gap-12">
        <div className="s16-portrait mx-auto w-[13rem] lg:mx-0 lg:w-[14.5rem]">
          <div className="relative rounded-[30px] border border-white/10 bg-[rgba(7,11,18,0.6)] p-2.5 shadow-[0_36px_90px_rgba(0,0,0,0.42)]">
            <div className="relative aspect-[3/4] overflow-hidden rounded-[24px]">
              <Image src="/story/r-pic.png" alt="Ravi Shankar" fill className="object-cover" style={{ objectPosition: "50% 24%" }} />
            </div>
            <div className="s16-meta mt-2.5 rounded-[16px] border border-[#9cd7ff]/10 bg-[rgba(7,11,18,0.7)] px-3.5 py-2.5">
              <div className="text-sm font-semibold text-white">Ravi Shankar</div>
              <div className="mt-0.5 text-[10px] font-medium uppercase tracking-[0.18em] text-[#bfe3ff]/70">Co-Founder &amp; CTO</div>
              <div className="mt-1.5 text-[12px] leading-[1.5] text-white/62">Built systems across engineering, product, and AI. Now building one for the self.</div>
            </div>
          </div>
        </div>
        <div className="text-center lg:text-left">
          <h2 className="s16-quote max-w-[16ch] text-balance text-[clamp(2.2rem,3.5vw,4.5rem)] font-semibold leading-[0.96] tracking-[-0.06em] text-white">
            I&apos;m a systems thinker at heart, grounded in deep technical expertise and driven to simplify complexity.
          </h2>
        </div>
      </div>
    </div>
  );
}

// ── Slide 18 — Ravi arc ───────────────────────────────────────────────────────
const RAVI_ARC = [
  { label: "Evolution",   body: "Started with engineering; kept moving closer to the question of what actually makes systems work." },
  { label: "Realization", body: "Systems succeed because people understand, trust, and use them — not just because they are built well." },
  { label: "Expansion",   body: "Moved across engineering, product, and product marketing. Yoga and meditation deepened how he thinks about human behavior over time." },
  { label: "Convergence", body: "Technical depth, systems thinking, product narrative, and lived understanding of people converge in building Sakhi." },
] as const;

function Slide17RaviArc() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const ctx = gsap.context(() => {
      gsap.set(".s17-kicker,.s17-step,.s17-final", { opacity: 0, y: 16 });
      gsap.timeline({ defaults: { ease: "power2.out" } })
        .to(".s17-kicker", { opacity: 1, y: 0, duration: 0.55 }, 0.2)
        .to(".s17-step", { opacity: 1, y: 0, stagger: 0.18, duration: 0.7 }, "+=0.2")
        .to(".s17-final", { opacity: 1, y: 0, duration: 0.7 }, "+=0.3");
    }, ref);
    return () => ctx.revert();
  }, []);
  return (
    <div ref={ref} className="absolute inset-0 flex items-center overflow-hidden px-8 py-10 sm:px-12 lg:px-16 xl:px-20">
      <div className="mx-auto grid w-full max-w-[88rem] items-center gap-8 lg:grid-cols-[minmax(13rem,0.55fr)_minmax(0,1.45fr)] lg:gap-12">
        <div className="mx-auto w-[13rem] opacity-70 lg:mx-0 lg:w-[14.5rem]">
          <div className="relative rounded-[30px] border border-white/10 bg-[rgba(7,11,18,0.6)] p-2.5">
            <div className="relative aspect-[3/4] overflow-hidden rounded-[24px]">
              <Image src="/story/r-pic.png" alt="Ravi Shankar" fill className="object-cover" style={{ objectPosition: "50% 24%" }} />
            </div>
            <div className="mt-2.5 rounded-[16px] border border-[#9cd7ff]/10 bg-[rgba(7,11,18,0.7)] px-3.5 py-2.5">
              <div className="text-sm font-semibold text-white">Ravi Shankar</div>
              <div className="mt-0.5 text-[10px] font-medium uppercase tracking-[0.18em] text-[#bfe3ff]/70">Co-Founder &amp; CTO</div>
            </div>
          </div>
        </div>
        <div>
          <p className="s17-kicker text-[10px] font-semibold uppercase tracking-[0.34em] text-[#bfe3ff]">Building From Lived Experience</p>
          <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {RAVI_ARC.map((step) => (
              <div key={step.label} className="s17-step rounded-[22px] border border-white/[0.08] bg-white/[0.03] px-4 py-4">
                <p className="text-sm font-semibold text-white">{step.label}</p>
                <p className="mt-2 text-[0.84rem] leading-[1.65] text-white/55">{step.body}</p>
              </div>
            ))}
          </div>
          <p className="s17-final mt-6 text-[1.05rem] font-medium leading-7 tracking-[-0.02em] text-white">
            &quot;That gives me the clarity to build Sakhi.&quot;
          </p>
        </div>
      </div>
    </div>
  );
}

// ── Slide 19 — The Ask ────────────────────────────────────────────────────────
function Slide18Ask() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const ctx = gsap.context(() => {
      gsap.set(".s18-headline,.s18-sub,.s18-card,.s18-email", { opacity: 0, y: 20 });
      gsap.timeline({ defaults: { ease: "power2.out" } })
        .to(".s18-headline", { opacity: 1, y: 0, duration: 0.9 }, 0.2)
        .to(".s18-sub", { opacity: 1, y: 0, duration: 0.72 }, "+=0.3")
        .to(".s18-card", { opacity: 1, y: 0, stagger: 0.18, duration: 0.7 }, "+=0.4")
        .to(".s18-email", { opacity: 1, y: 0, duration: 0.65 }, "+=0.3");
    }, ref);
    return () => ctx.revert();
  }, []);
  return (
    <div ref={ref} className="absolute inset-0 flex items-center justify-center overflow-hidden px-10 py-12 text-center">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_24%,rgba(162,179,255,0.12),transparent_24%)]" />
      <div className="relative mx-auto w-full max-w-5xl">
        <h1 className="s18-headline mx-auto max-w-[13ch] text-balance text-[clamp(3.2rem,7vw,6rem)] font-bold leading-[0.92] tracking-[-0.07em] text-white">
          This is just the beginning.
        </h1>
        <p className="s18-sub mx-auto mt-5 max-w-xl text-balance text-[1.1rem] leading-[1.7] tracking-[-0.02em] text-white/50">
          If this resonates, let&apos;s build this together.
        </p>
        <div className="mx-auto mt-12 flex w-full max-w-[640px] flex-col gap-4 sm:flex-row sm:gap-5">
          {(["Collaborate", "Invest"] as const).map((title) => (
            <div
              key={title}
              className="s18-card flex flex-1 flex-col items-start rounded-[26px] border border-white/[0.08] bg-[rgba(255,255,255,0.025)] px-6 py-6 text-left"
            >
              <h3 className="text-[1.4rem] font-semibold tracking-[-0.05em] text-white">{title}</h3>
              <p className="mt-2 text-[0.9rem] leading-[1.65] text-white/48">
                {title === "Collaborate"
                  ? "If you believe we should shape our lives, not just react to them, come build this with us."
                  : "For investors who see this space the way we do, we share everything: vision, GTM, early product, and roadmap."}
              </p>
            </div>
          ))}
        </div>
        <div className="s18-email mt-10 flex flex-col items-center">
          <p className="mb-2 text-[0.68rem] font-semibold uppercase tracking-[0.28em] text-white/28">
            For Collaboration Or Investment
          </p>
          <a
            href="mailto:founders@sakhiintelligence.com"
            className="text-[1.05rem] font-semibold tracking-[-0.03em] text-white/78 transition-colors hover:text-white"
          >
            founders@sakhiintelligence.com
          </a>
        </div>
        <p className="mt-8 text-[0.72rem] font-semibold uppercase tracking-[0.28em] text-white/20">Sakhi · 2026</p>
      </div>
    </div>
  );
}

// ── Slide router ──────────────────────────────────────────────────────────────
function renderSlide(step: number) {
  if (step === 1)  return <Slide01Chaos key={1} />;
  if (step === 2)  return <Slide02Breakdown key={2} />;
  if (step === 3)  return <Slide03SakhiReveal key={3} />;
  if (step === 4)  return <Slide04Bridge key={4} />;
  if (step === 5)  return <Slide05StopReacting key={5} />;
  if (step === 6)  return <Slide06Continuity key={6} />;
  if (step === 7)  return <Slide07LifeConnected key={7} />;
  if (step === 8)  return <Slide08FirstExpression key={8} />;
  if (step === 9)  return <SlideProduct key={9}  panelIndex={0} />;
  if (step === 10) return <SlideProduct key={10} panelIndex={1} />;
  if (step === 11) return <SlideProduct key={11} panelIndex={2} />;
  if (step === 12) return <SlideProduct key={12} panelIndex={3} />;
  if (step === 13) return <Slide13Vision key={13} />;
  if (step === 14) return <Slide14FounderBridge key={14} />;
  if (step === 15) return <Slide14VidhyaQuote key={15} />;
  if (step === 16) return <Slide15VidhyaArc key={16} />;
  if (step === 17) return <Slide16RaviQuote key={17} />;
  if (step === 18) return <Slide17RaviArc key={18} />;
  if (step === 19) return <Slide18Ask key={19} />;
  return null;
}

// ── Main export ───────────────────────────────────────────────────────────────
interface PitchPresentationProps {
  open: boolean;
  onClose: () => void;
}

export function PitchPresentation({ open, onClose }: PitchPresentationProps) {
  const [step, setStep] = useState(1);
  const [transitioning, setTransitioning] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) setStep(1);
  }, [open]);

  const goTo = useCallback(
    (next: number) => {
      if (transitioning || next < 1 || next > TOTAL_STEPS) return;
      setTransitioning(true);
      gsap.to(contentRef.current, {
        opacity: 0,
        duration: 0.22,
        ease: "power1.in",
        onComplete: () => {
          setStep(next);
          setTransitioning(false);
          gsap.fromTo(
            contentRef.current,
            { opacity: 0 },
            { opacity: 1, duration: 0.28, ease: "power1.out" },
          );
        },
      });
    },
    [transitioning],
  );

  const navigate = useCallback(
    (dir: 1 | -1) => goTo(step + dir),
    [step, goTo],
  );

  useEffect(() => {
    if (!open || step !== 14 || transitioning) return;
    const timer = window.setTimeout(() => {
      goTo(15);
    }, FOUNDER_BRIDGE_AUTO_ADVANCE_MS);
    return () => window.clearTimeout(timer);
  }, [open, step, transitioning, goTo]);

  const toggleFullscreen = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    if (!document.fullscreenElement) {
      el.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen().catch(() => {});
    }
  }, []);

  useEffect(() => {
    const onChange = () => setIsFullscreen(Boolean(document.fullscreenElement));
    document.addEventListener("fullscreenchange", onChange);
    return () => document.removeEventListener("fullscreenchange", onChange);
  }, []);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !document.fullscreenElement) { onClose(); return; }
      if (e.key === "f" || e.key === "F") { toggleFullscreen(); return; }
      if (e.key === "ArrowRight" || e.key === "ArrowDown" || e.key === " ") { e.preventDefault(); navigate(1); }
      if (e.key === "ArrowLeft"  || e.key === "ArrowUp")                    { e.preventDefault(); navigate(-1); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, navigate, onClose, toggleFullscreen]);

  if (!open) return null;

  return (
    <div ref={containerRef} className="fixed inset-0 z-[200] bg-[#020617] text-white">
      {/* Slide content */}
      <div ref={contentRef} className="absolute inset-0">
        {renderSlide(step)}
      </div>

      {/* Top-right controls */}
      <div className="absolute right-4 top-3 z-10 flex items-center gap-2">
        {/* Fullscreen toggle */}
        <button
          type="button"
          onClick={toggleFullscreen}
          aria-label={isFullscreen ? "Exit fullscreen" : "Enter fullscreen"}
          className="flex h-9 w-9 items-center justify-center rounded-full border border-white/10 bg-transparent text-white/40 transition hover:border-white/20 hover:text-white/80"
        >
          {isFullscreen ? (
            <svg viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-current" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M8 3v3a2 2 0 0 1-2 2H3M21 8h-3a2 2 0 0 1-2-2V3M3 16h3a2 2 0 0 1 2 2v3M16 21v-3a2 2 0 0 1 2-2h3" />
            </svg>
          ) : (
            <svg viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-current" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M8 3H5a2 2 0 0 0-2 2v3M21 8V5a2 2 0 0 0-2-2h-3M3 16v3a2 2 0 0 0 2 2h3M16 21h3a2 2 0 0 0 2-2v-3" />
            </svg>
          )}
        </button>
        {/* Close */}
        <button
          type="button"
          onClick={onClose}
          aria-label="Close presentation"
          className="flex h-9 w-9 items-center justify-center rounded-full border border-white/10 bg-transparent text-white/40 transition hover:border-white/20 hover:text-white/80"
        >
          <svg viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-current" strokeWidth="2" strokeLinecap="round">
            <path d="M18 6 6 18M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Vertical dot nav — right side, matching PitchNav style */}
      <nav className="absolute right-4 top-1/2 z-10 hidden -translate-y-1/2 flex-col gap-3 md:flex sm:right-6">
        {Array.from({ length: TOTAL_STEPS }).map((_, i) => (
          <button
            key={i}
            type="button"
            onClick={() => goTo(i + 1)}
            aria-label={`Go to slide ${i + 1}`}
            className={`h-2.5 w-2.5 rounded-full transition-all duration-300 ${
              i + 1 === step
                ? "scale-125 bg-white opacity-100"
                : "bg-white opacity-25 hover:opacity-50"
            }`}
          />
        ))}
      </nav>

      {/* Prev */}
      <button
        type="button"
        onClick={() => navigate(-1)}
        disabled={step === 1 || transitioning}
        aria-label="Previous slide"
        className={`absolute bottom-6 left-5 z-10 flex h-12 w-12 items-center justify-center rounded-full border backdrop-blur-md transition sm:bottom-8 sm:left-7 ${
          step === 1
            ? "cursor-not-allowed border-white/8 bg-[#020617]/30 text-white/18"
            : "border-white/12 bg-[#020617]/76 text-white/78 shadow-[0_18px_40px_rgba(0,0,0,0.28)] hover:border-white/22 hover:bg-[#08111f]/92 hover:text-white"
        }`}
      >
        <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M15 18l-6-6 6-6" />
        </svg>
      </button>

      {/* Next */}
      <button
        type="button"
        onClick={() => navigate(1)}
        disabled={step === TOTAL_STEPS || transitioning}
        aria-label="Next slide"
        className={`absolute bottom-6 right-5 z-10 flex h-12 w-12 items-center justify-center rounded-full border backdrop-blur-md transition sm:bottom-8 sm:right-7 ${
          step === TOTAL_STEPS
            ? "cursor-not-allowed border-white/8 bg-[#020617]/30 text-white/18"
            : "border-white/12 bg-[#020617]/76 text-white/78 shadow-[0_18px_40px_rgba(0,0,0,0.28)] hover:border-white/22 hover:bg-[#08111f]/92 hover:text-white"
        }`}
      >
        <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M9 6l6 6-6 6" />
        </svg>
      </button>
    </div>
  );
}
