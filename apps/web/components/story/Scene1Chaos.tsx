"use client";

import ThoughtParticle from "@/components/story/ThoughtParticle";

// ── Persistent thoughts ─────────────────────────────────────────────
// Tagged by type so GSAP can target each group during the Scene 2 transition:
//   thought-signal  → fades when "The signal fades with it"
//   thought-thread  → stretches + vanishes when "By morning, the thread is gone"
//   thought-idea    → bright amber sparks that die when "Good ideas die"
//   (untagged)      → general thoughts, reset on "Thoughts reset"

const persistentThoughts = [
  // ── general ──────────────────────────────────────────────────────
  { text: "did I reply?",                       top: "12%", left: "56%" },
  { text: "I'll do it later",                   top: "18%", left: "72%" },
  { text: "what did they say?",                 top: "14%", left: "40%" },
  { text: "don't forget",                       top: "56%", left: "74%" },
  { text: "maybe later",                        top: "30%", left: "82%" },
  { text: "why again?",                         top: "44%", left: "62%" },
  { text: "call her back",                      top: "38%", left: "78%" },
  { text: "what now",                           top: "70%", left: "54%" },
  { text: "not now",                            top: "26%", left: "64%" },
  { text: "later tonight",                      top: "14%", left: "84%" },
  { text: "tomorrow",                           top: "72%", left: "84%" },
  { text: "remember",                           top: "86%", left: "62%" },
  { text: "respond",                            top: "50%", left: "90%" },
  { text: "later",                              top: "8%",  left: "70%" },
  { text: "how do I say this?",                 top: "24%", left: "88%" },
  { text: "did that sound wrong?",              top: "34%", left: "68%" },
  { text: "media presentation",                 top: "22%", left: "18%" },
  { text: "flu shot for the kids",              top: "84%", left: "34%" },
  { text: "grocery, I'm out of milk",           top: "88%", left: "78%" },
  { text: "pay piano class fee",                top: "58%", left: "16%" },
  { text: "say something",                      top: "62%", left: "48%" },
  { text: "pick up clothes from laundry",       top: "64%", left: "8%"  },
  // ── signal ───────────────────────────────────────────────────────
  { text: "why does this keep repeating",       top: "68%", left: "74%", type: "signal" as const },
  { text: "the same pattern again",             top: "74%", left: "60%", type: "signal" as const },
  { text: "I should remember this",             top: "54%", left: "58%", type: "signal" as const },
  { text: "did I miss something",               top: "32%", left: "60%", type: "signal" as const },
  { text: "again?",                             top: "18%", left: "73%", type: "signal" as const },
  // ── thread ───────────────────────────────────────────────────────
  { text: "this thread isn't finished",         top: "48%", left: "38%", type: "thread" as const },
  { text: "I said I'd revisit this",            top: "40%", left: "50%", type: "thread" as const },
  { text: "I need to get back to them",         top: "60%", left: "30%", type: "thread" as const },
  { text: "what did I promise?",                top: "42%", left: "26%", type: "thread" as const },
  { text: "what am I missing",                  top: "80%", left: "70%", type: "thread" as const },
  // ── idea (bright amber sparks) ────────────────────────────────────
  { text: "✦ what if this changes everything",  top: "20%", left: "34%", type: "idea" as const },
  { text: "✦ I just had a breakthrough",        top: "50%", left: "20%", type: "idea" as const },
  { text: "✦ this connects it all",             top: "66%", left: "44%", type: "idea" as const },
  { text: "✦ an insight that matters",          top: "15%", left: "60%", type: "idea" as const },
  { text: "✦ this could work differently",      top: "78%", left: "28%", type: "idea" as const },
] as const;

const transientThoughts = [
  { text: "one more thing",                top: "14%", left: "10%", markerSize: "base" },
  { text: "did I say yes?",               top: "24%", left: "28%", markerSize: "base" },
  { text: "need to follow up",            top: "44%", left: "14%", markerSize: "base" },
  { text: "what did I promise?",          top: "74%", left: "16%", markerSize: "lg" },
  { text: "I forgot again",               top: "10%", left: "48%", markerSize: "base" },
  { text: "should I reply now?",          top: "82%", left: "38%", markerSize: "base" },
  { text: "did I miss the tone?",         top: "34%", left: "44%", markerSize: "base" },
  { text: "follow up tomorrow",           top: "66%", left: "54%", markerSize: "base" },
  { text: "not this again",               top: "18%", left: "78%", markerSize: "base" },
  { text: "I need to remember",           top: "52%", left: "86%", markerSize: "lg" },
  { text: "this feels urgent",            top: "30%", left: "70%", markerSize: "lg" },
  { text: "not tonight",                  top: "78%", left: "72%", markerSize: "base" },
  { text: "say it clearly",               top: "12%", left: "90%", markerSize: "base" },
  { text: "I missed that",                top: "60%", left: "66%", markerSize: "base" },
  { text: "how do I respond?",            top: "46%", left: "84%", markerSize: "base" },
  { text: "did I commit to that?",        top: "68%", left: "34%", markerSize: "base" },
  { text: "what do they need from me?",   top: "18%", left: "60%", markerSize: "base" },
  { text: "I need to take mom to dentist",top: "12%", left: "22%", markerSize: "lg" },
  { text: "schedule interview",           top: "38%", left: "20%", markerSize: "base" },
  { text: "an aha moment...",             top: "72%", left: "46%", markerSize: "lg" },
  { text: "this connects to last week",   top: "28%", left: "52%", markerSize: "base" },
  { text: "I keep coming back to this",   top: "80%", left: "58%", markerSize: "base" },
] as const;

function thoughtClass(type?: "signal" | "thread" | "idea") {
  if (type === "signal") return "thought-persistent thought-signal text-[clamp(0.95rem,1.35vw,1.75rem)] font-medium tracking-[-0.03em] text-white/36";
  if (type === "thread") return "thought-persistent thought-thread text-[clamp(0.95rem,1.35vw,1.75rem)] font-medium tracking-[-0.03em] text-white/36";
  if (type === "idea")   return "thought-persistent thought-idea   text-[clamp(0.95rem,1.3vw,1.65rem)]  font-medium tracking-[-0.02em] text-[#ffd59a]/80";
  return "thought-persistent text-[clamp(0.95rem,1.35vw,1.75rem)] font-medium tracking-[-0.03em] text-white/36";
}

export default function Scene1Chaos() {
  return (
    <div className="relative h-full overflow-hidden px-8 py-10 sm:px-12 lg:px-16 xl:px-24">
      <div className="thought-field absolute inset-0">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_18%_18%,rgba(138,163,255,0.08),transparent_26%),radial-gradient(circle_at_76%_26%,rgba(138,163,255,0.07),transparent_28%),radial-gradient(circle_at_64%_70%,rgba(138,163,255,0.06),transparent_24%),linear-gradient(180deg,rgba(7,10,16,0.18),rgba(7,10,16,0.74))]" />
        <div className="thought-vignette absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,rgba(2,6,23,0.08)_48%,rgba(2,6,23,0.58)_100%)]" />

        {persistentThoughts.map((thought) => {
          const isIdea = "type" in thought && thought.type === "idea";
          const renderedText = isIdea ? (
            <>
              <span className="text-[1.4em] text-yellow-200 drop-shadow-[0_0_8px_rgba(255,236,120,0.9)]">✦</span>
              {thought.text.replace("✦", "")}
            </>
          ) : thought.text;
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

        {transientThoughts.map((thought) => (
          <ThoughtParticle
            key={thought.text}
            text={thought.text}
            top={thought.top}
            left={thought.left}
            blip
            markerSize={thought.markerSize as "base" | "lg"}
            className="thought-transient text-[clamp(0.85rem,1.05vw,1.2rem)] font-medium tracking-[-0.02em] text-[#d8e2ff]/0"
          />
        ))}
      </div>

      <div className="scene-1-copy relative z-10 flex h-full items-center">
        <div className="max-w-4xl">
          <div className="line-1 max-w-[9ch] text-balance text-5xl font-semibold leading-[0.98] tracking-[-0.06em] text-white drop-shadow-[0_0_20px_rgba(255,255,255,0.1)] sm:text-6xl lg:text-8xl">
            There&apos;s a conversation happening in your head.
          </div>
          <div className="mt-12 max-w-2xl space-y-6 text-xl leading-[1.45] tracking-[-0.03em] text-[#c9d3ea] sm:text-2xl">
            <p className="line-2">It never really stops.</p>
            <p className="line-3a">And it doesn&apos;t carry forward.</p>
            <p className="line-3b text-slate-100">Nothing actually holds it together.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
