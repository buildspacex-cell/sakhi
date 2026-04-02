"use client";

import { useEffect, useRef } from "react";

import gsap from "gsap";

import ThoughtParticle from "@/components/story/ThoughtParticle";

const persistentThoughts = [
  { text: "did I reply?", top: "12%", left: "56%" },
  { text: "I'll do it later", top: "18%", left: "72%" },
  { text: "what did they say?", top: "14%", left: "40%" },
  { text: "don't forget", top: "56%", left: "74%" },
  { text: "maybe later", top: "30%", left: "82%" },
  { text: "why again?", top: "44%", left: "62%" },
  { text: "call her back", top: "38%", left: "78%" },
  { text: "what now", top: "70%", left: "54%" },
  { text: "not now", top: "26%", left: "64%" },
  { text: "later tonight", top: "14%", left: "84%" },
  { text: "tomorrow", top: "72%", left: "84%" },
  { text: "remember", top: "86%", left: "62%" },
  { text: "respond", top: "50%", left: "90%" },
  { text: "later", top: "8%", left: "70%" },
  { text: "how do I say this?", top: "24%", left: "88%" },
  { text: "did that sound wrong?", top: "34%", left: "68%" },
  { text: "media presentation", top: "22%", left: "18%" },
  { text: "flu shot for the kids", top: "84%", left: "34%" },
  { text: "grocery, I'm out of milk", top: "88%", left: "78%" },
  { text: "pay piano class fee", top: "58%", left: "16%" },
  { text: "say something", top: "62%", left: "48%" },
  { text: "pick up clothes from laundry", top: "64%", left: "8%" },
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
] as const;

function thoughtClass(type?: "signal" | "thread" | "idea") {
  if (type === "signal") {
    return "pitch-problem-thought-persistent pitch-problem-thought-signal text-[clamp(0.95rem,1.35vw,1.75rem)] font-medium tracking-[-0.03em] text-white/34";
  }
  if (type === "thread") {
    return "pitch-problem-thought-persistent pitch-problem-thought-thread text-[clamp(0.95rem,1.35vw,1.75rem)] font-medium tracking-[-0.03em] text-white/34";
  }
  if (type === "idea") {
    return "pitch-problem-thought-persistent pitch-problem-thought-idea text-[clamp(0.95rem,1.3vw,1.65rem)] font-medium tracking-[-0.02em] text-[#ffd59a]/82";
  }

  return "pitch-problem-thought-persistent text-[clamp(0.95rem,1.35vw,1.75rem)] font-medium tracking-[-0.03em] text-white/34";
}

export function PitchProblem() {
  const sectionRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (!sectionRef.current) return;

    const ctx = gsap.context(() => {
      gsap.set(".pitch-problem-thought-field", { opacity: 1, scale: 1 });
      gsap.set(".pitch-problem-thought-vignette", { opacity: 0.56 });
      gsap.set(".pitch-problem-thought-persistent", { opacity: 0.55, scale: 1 });
      gsap.set(".pitch-problem-copy", { opacity: 1 });
      gsap.set(".pitch-bridge-1, .pitch-bridge-2, .pitch-bridge-3", { opacity: 0, y: 18 });
      gsap.set(".pitch-break-1, .pitch-break-2, .pitch-break-3", { opacity: 0, y: 20 });

      let hasPlayed = false;

      const observer = new IntersectionObserver(
        (entries) => {
          const entry = entries[0];
          if (!entry?.isIntersecting || hasPlayed) return;
          hasPlayed = true;

          const tl = gsap.timeline({ defaults: { ease: "power2.out" } });

          tl.fromTo(
            ".pitch-problem-copy",
            { opacity: 0.85 },
            { opacity: 1, duration: 0.4 },
          )
            .to(".pitch-bridge-1", { opacity: 1, y: 0, duration: 0.72 })
            .to(
              ".pitch-problem-thought-persistent:not(.pitch-problem-thought-signal):not(.pitch-problem-thought-thread):not(.pitch-problem-thought-idea)",
              {
                y: "+=45",
                opacity: 0.22,
                duration: 2.0,
                stagger: { each: 0.04, from: "random" },
                ease: "power1.inOut",
              },
              "<+0.08",
            )
            .to(".pitch-bridge-2", { opacity: 1, y: 0, duration: 0.72 }, "+=1.2")
            .to(
              ".pitch-problem-thought-signal",
              {
                opacity: 0,
                filter: "blur(10px)",
                y: "+=30",
                scale: 0.88,
                duration: 1.3,
                stagger: { each: 0.12, from: "random" },
                ease: "power2.in",
              },
              "<+0.06",
            )
            .to(".pitch-bridge-3", { opacity: 1, y: 0, duration: 0.78 }, "+=1.2")
            .to(
              ".pitch-problem-thought-thread",
              {
                scaleX: 2.4,
                opacity: 0,
                filter: "blur(8px)",
                duration: 1.4,
                stagger: { each: 0.14, from: "random" },
                ease: "power2.in",
              },
              "<+0.05",
            )
            .to(".pitch-break-1", { opacity: 1, y: 0, duration: 0.78 }, "+=1.25")
            .to(
              ".pitch-problem-thought-persistent:not(.pitch-problem-thought-signal):not(.pitch-problem-thought-thread):not(.pitch-problem-thought-idea)",
              {
                y: "+=150",
                opacity: 0,
                filter: "blur(8px)",
                scale: 0.82,
                duration: 1.6,
                stagger: { each: 0.06, from: "random" },
                ease: "power2.in",
              },
              "<+0.05",
            )
            .to(".pitch-break-2", { opacity: 1, y: 0, duration: 0.78 }, "+=1.1")
            .to(
              ".pitch-problem-thought-idea",
              {
                scale: 0,
                opacity: 0,
                filter: "blur(14px)",
                duration: 1.0,
                stagger: { each: 0.12, from: "random" },
                ease: "back.in(1.2)",
              },
              "<+0.05",
            )
            .to(".pitch-break-3", { opacity: 1, y: 0, duration: 0.82 }, "+=1.15")
            .to(
              ".pitch-problem-thought-vignette",
              { opacity: 0, duration: 1.5, ease: "power1.in" },
              "<",
            )
            .to(
              ".pitch-problem-thought-field",
              { opacity: 0.16, duration: 1.0, ease: "power1.in" },
              "<+0.7",
            );

          observer.disconnect();
        },
        { threshold: 0.55 },
      );

      observer.observe(sectionRef.current!);
    }, sectionRef);

    return () => {
      ctx.revert();
    };
  }, []);

  return (
    <section
      id="problem"
      ref={sectionRef}
      className="relative flex min-h-[100svh] items-center overflow-hidden border-t border-white/[0.06] bg-[#020617] px-8 py-28 scroll-mt-16 sm:px-16 sm:py-32 lg:px-24"
    >
      <div className="pitch-problem-thought-field pointer-events-none absolute inset-0">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_18%_18%,rgba(138,163,255,0.08),transparent_26%),radial-gradient(circle_at_76%_26%,rgba(138,163,255,0.07),transparent_28%),radial-gradient(circle_at_64%_70%,rgba(138,163,255,0.06),transparent_24%),linear-gradient(180deg,rgba(7,10,16,0.12),rgba(7,10,16,0.74))]" />
        <div className="pitch-problem-thought-vignette absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,rgba(2,6,23,0.06)_44%,rgba(2,6,23,0.54)_100%)]" />

        {persistentThoughts.map((thought) => {
          const isIdea = "type" in thought && thought.type === "idea";
          const renderedText = isIdea ? (
            <>
              <span className="text-[1.4em] text-yellow-200 drop-shadow-[0_0_8px_rgba(255,236,120,0.9)]">✦</span>
              {thought.text.replace("✦", "")}
            </>
          ) : (
            thought.text
          );

          return (
            <ThoughtParticle
              key={thought.text}
              text={renderedText}
              top={thought.top}
              left={thought.left}
              className={thoughtClass("type" in thought ? thought.type : undefined)}
            />
          );
        })}
      </div>

      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(2,6,23,0.14),transparent_40%),linear-gradient(180deg,rgba(2,6,23,0.08),rgba(2,6,23,0.2))]" />

      <div className="pitch-problem-copy relative mx-auto w-full max-w-5xl text-center">
        <div className="mx-auto max-w-2xl space-y-3 text-lg leading-8 tracking-[-0.03em] text-slate-300 drop-shadow-[0_0_18px_rgba(2,6,23,1)] sm:text-xl">
          <p className="pitch-bridge-1">You wind down for the day.</p>
          <p className="pitch-bridge-2">The signal fades with it.</p>
          <p className="pitch-bridge-3 text-slate-100">By morning, the thread is gone.</p>
        </div>

        <div className="mt-14 space-y-5">
          <div className="pitch-break-1 rounded-full bg-white/6 px-8 py-5 text-3xl font-medium leading-none tracking-[-0.04em] text-white backdrop-blur-md sm:text-4xl">
            Thoughts reset
          </div>
          <div className="pitch-break-2 rounded-full bg-white/6 px-8 py-5 text-3xl font-medium leading-none tracking-[-0.04em] text-white backdrop-blur-md sm:text-4xl">
            Good ideas die
          </div>
          <div className="pitch-break-3 rounded-full bg-white/6 px-8 py-5 text-3xl font-medium leading-none tracking-[-0.04em] text-white backdrop-blur-md sm:text-4xl">
            Continuity is lost
          </div>
        </div>
      </div>
    </section>
  );
}
