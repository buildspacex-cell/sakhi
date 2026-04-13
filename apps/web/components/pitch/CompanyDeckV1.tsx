"use client";

import Image from "next/image";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import gsap from "gsap";
import StoryContainer from "@/components/story/StoryContainer";

const TOTAL = 12;
const COVER = 0;
const DECK_HEADER_BADGE_CLASS =
  "mb-4 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 text-[10px] font-semibold uppercase tracking-[0.3em] text-white/40";
const DECK_TITLE_CLASS =
  "text-[clamp(1.8rem,3vw,2.8rem)] font-bold leading-[1.05] tracking-[-0.05em] text-white";
const DECK_SUBTITLE_CLASS =
  "mt-3 max-w-4xl text-[clamp(0.88rem,1.1vw,1rem)] leading-[1.65] text-slate-400";

// ── Slide 1 — Three Moments (Stories) ────────────────────────────────────────
function SlideStories() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const ctx = gsap.context(() => {
      gsap.set(".st-item", { opacity: 0, y: 20 });
      gsap.timeline({ defaults: { ease: "power2.out" } })
        .to(".st-item", { opacity: 1, y: 0, stagger: 0.12, duration: 0.65 }, 0.2);
    }, ref);
    return () => ctx.revert();
  }, []);

  type Story = {
    domain: string;
    tag: string;
    trigger: string;
    accent: string;
    dim: string;
    border: string;
    dot: string;
    scene: ReactNode;
    moment: string;
  };

  const S = "text-[0.75rem] leading-[1.6] text-slate-500";
  const DLG = "text-[0.75rem] leading-[1.6] text-slate-400 italic";
  const PAYOFF = "text-[0.75rem] font-semibold text-white/60";

  // Visual repeating pattern row
  function PatternRow({
    label,
    accent,
    items,
    singleLineLabel = false,
    noWrapItems = false,
  }: {
    label: string;
    accent: string;
    items: string[];
    singleLineLabel?: boolean;
    noWrapItems?: boolean;
  }) {
    return (
      <div className="flex items-start gap-2">
        <span
          className={`mt-[0.35em] shrink-0 text-[9px] font-semibold ${
            singleLineLabel ? "w-20 whitespace-nowrap tracking-[0.18em]" : "w-14 uppercase tracking-[0.22em]"
          }`}
          style={{ color: accent }}
        >
          {label}
        </span>
        <div className={`flex items-center gap-1 ${noWrapItems ? "whitespace-nowrap" : "flex-wrap"}`}>
          {items.map((item, i) => (
            <span key={i} className="flex items-center gap-1">
              <span className="whitespace-nowrap text-[0.7rem] text-slate-400 font-medium">{item}</span>
              {i < items.length - 1 && <span className="text-slate-600 text-[0.65rem]">&#8594;</span>}
            </span>
          ))}
        </div>
      </div>
    );
  }

  const stories: Story[] = [
    {
      domain: "Health",
      tag: "Health · Priya",
      trigger: "Leaving a doctor's office still confused",
      accent: "#2dd4bf",
      dim: "rgba(45,212,191,0.06)",
      border: "rgba(45,212,191,0.18)",
      dot: "bg-teal-400/50",
      scene: (
        <div className="flex flex-col gap-2 flex-1">
          <p className={S}>Priya describes what she&rsquo;s been feeling. Vaguely, because she doesn&rsquo;t have the pattern yet. Routine tests. Nothing conclusive.</p>
          <p className={S}>That night, she opens Sakhi. Eight months of health, sleep, and energy threads, held together while she lived them. She sees it for the first time.</p>
          <div className="my-1 rounded-lg bg-white/[0.03] border border-white/[0.06] px-3 py-2.5 flex flex-col gap-1.5">
            <PatternRow label="Month 1" accent="#2dd4bf" items={["Sleep down", "Fatigue up", "Cycle delay"]} singleLineLabel noWrapItems />
            <PatternRow label="Month 3" accent="#2dd4bf" items={["Sleep down", "Fatigue up", "Cycle delay"]} singleLineLabel noWrapItems />
            <PatternRow label="Month 6" accent="#2dd4bf" items={["Sleep down", "Fatigue up", "Cycle delay"]} singleLineLabel noWrapItems />
            <p className="text-[0.68rem] text-teal-400/60 font-semibold mt-0.5">Same sequence. Every time.</p>
          </div>
          <p className={S}>She goes back.</p>
          <p className={DLG}>&ldquo;Same pattern, three times. Can we test for thyroid?&rdquo;</p>
          <p className={PAYOFF}>They test. Diagnosis confirmed. Nothing missed.</p>
        </div>
      ),
      moment: "Seeing your own pattern, before anyone else does.",
    },
    {
      domain: "Ambition",
      tag: "Ambition · Marcus",
      trigger: "Putting in effort, but not breaking through",
      accent: "#f59e0b",
      dim: "rgba(245,158,11,0.06)",
      border: "rgba(245,158,11,0.18)",
      dot: "bg-amber-400/50",
      scene: (
        <div className="flex flex-col gap-2 flex-1">
          <p className={S}>Marcus has tried everything. Every variable, every protocol. Game performance still swings. He can&rsquo;t find the lever.</p>
          <p className={S}>He opens Sakhi. Months of training logs, game reflections, sleep notes, held across time while he was living through them one session at a time.</p>
          <div className="my-1 rounded-lg bg-white/[0.03] border border-white/[0.06] px-3 py-2.5 flex flex-col gap-1.5">
            <PatternRow label="Best games" accent="#f59e0b" items={["Strength cycle", "Sleep stable", "Peak output"]} />
            <PatternRow label="Flat games" accent="#f59e0b" items={["Agility only", "Sleep variable", "No change"]} />
            <p className="text-[0.68rem] text-amber-400/60 font-semibold mt-0.5">Agility alone never moved it.</p>
          </div>
          <p className={S}>The correlation he was missing wasn&rsquo;t about working harder. It was about what he was pairing.</p>
          <p className={S}>He stops treating sleep as optional when strength work is high.</p>
          <p className={PAYOFF}>His game shifts.</p>
        </div>
      ),
      moment: "What actually works, finally visible.",
    },
    {
      domain: "Life",
      tag: "Life · Nadia",
      trigger: "Holding everything together, until you can't",
      accent: "#c084fc",
      dim: "rgba(192,132,252,0.06)",
      border: "rgba(192,132,252,0.18)",
      dot: "bg-purple-400/50",
      scene: (
        <div className="flex flex-col gap-2 flex-1">
          <p className={S}>Nadia leads a SaaS company. Two kids. Ageing parents.</p>
          <p className={S}>Her father has an accident. TBI. Weeks in the ICU. Her days collapse into hospital rounds, doctor calls, and late-night updates. Work, kids, meals, sleep, all start slipping.</p>
          <p className={S}>Then she starts waking at 2 a.m. with her heart racing. She doesn&rsquo;t understand why it&rsquo;s happening.</p>
          <p className={S}>She opens Sakhi. &ldquo;I&rsquo;m not giving up. I&rsquo;m doing everything I can to keep things going. What&rsquo;s happening at night? Why do I wake up in a panic?&rdquo;</p>
          <div className="my-1 rounded-lg bg-white/[0.03] border border-white/[0.06] px-3 py-2.5 flex flex-col gap-1.5">
            <PatternRow label="Before" accent="#c084fc" items={["Work steady", "Kids covered", "Sleeping normally"]} />
            <PatternRow label="Now" accent="#c084fc" items={["ICU first", "Sleep gone", "Waking panicked"]} />
          </div>
          <p className={S}>Three months earlier, morning walks and yoga had steadied her during another stretch of overload. She had written about both. Sakhi brings them back.</p>
          <p className={DLG}>&ldquo;The last time your system went off balance, walking and yoga helped steady you. Start there.&rdquo;</p>
          <p className={PAYOFF}>Not generic advice. Her answer, from her own history.</p>
        </div>
      ),
      moment: "The path back, found in your own history.",
    },
  ];

  return (
    <div ref={ref} className="slide-scroll-panel absolute inset-0 overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden flex flex-col px-6 pt-12 pb-20 sm:px-10 sm:pt-14 sm:pb-8 lg:px-14 lg:pt-12 lg:pb-10">
      <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-5">

        {/* Header */}
        <div className="st-item shrink-0">
          <p className="text-[clamp(0.82rem,1vw,0.9rem)] text-slate-500 leading-[1.6]">
            Notes apps store. AI chats respond. Nobody compounds thought over time.
          </p>
          <h2 className={DECK_TITLE_CLASS}>
            Sakhi is the continuity layer for the human mind.{" "}
            <span className="text-white/30">Three moments that show what that means.</span>
          </h2>
        </div>

        {/* Story cards */}
        <div className="st-item grid gap-4 lg:grid-cols-3">
          {stories.map((s) => (
            <div
              key={s.tag}
              className="flex flex-col rounded-2xl border px-5 py-5 gap-4"
              style={{ background: s.dim, borderColor: s.border }}
            >
              {/* Domain tag */}
              <div className="flex items-center gap-2 shrink-0">
                <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${s.dot}`} />
                <span className="text-[9px] font-semibold uppercase tracking-[0.32em]" style={{ color: s.accent }}>
                  {s.tag}
                </span>
              </div>

              {/* Trigger */}
              <div className="shrink-0">
                <p className="text-[9px] font-semibold uppercase tracking-[0.28em] text-white/25 mb-1.5">Trigger</p>
                <p className="text-[0.82rem] font-semibold leading-[1.35] text-white/70">{s.trigger}</p>
              </div>

              {/* Scene */}
              {s.scene}

              {/* The shift */}
              <div className="shrink-0 border-t pt-3.5" style={{ borderColor: s.border }}>
                <p className="text-[9px] font-semibold uppercase tracking-[0.28em] mb-1.5" style={{ color: s.accent }}>The shift</p>
                <p className="text-[0.8rem] font-semibold leading-[1.4] text-white/80">{s.moment}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Closing line */}
        <div className="st-item shrink-0 rounded-xl border border-white/[0.07] bg-white/[0.02] px-5 py-3">
          <p className="text-[clamp(0.78rem,0.92vw,0.88rem)] leading-[1.55] text-slate-400">
            Different lives. Different problems. One thing in common:{" "}
            <span className="font-semibold text-white">nobody was holding the continuity. Sakhi does.</span>
          </p>
        </div>

      </div>
    </div>
  );
}

// ── Slide 2 — Problem + Solution ─────────────────────────────────────────────
function Slide01ProblemSolution() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const ctx = gsap.context(() => {
      gsap.set(".cd1-item", { opacity: 0, y: 18 });
      gsap.timeline({ defaults: { ease: "power2.out" } })
        .to(".cd1-item", { opacity: 1, y: 0, stagger: 0.1, duration: 0.6 }, 0.2);
    }, ref);
    return () => ctx.revert();
  }, []);

  return (
    <div ref={ref} className="slide-scroll-panel absolute inset-0 overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden flex flex-col px-6 pt-14 pb-20 sm:px-12 sm:pt-14 sm:pb-6 lg:px-16 lg:pt-12 lg:pb-8">
      <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-5">

        {/* Hook */}
        <div className="cd1-item shrink-0">
          <h2 className={DECK_TITLE_CLASS}>
            ChatGPT and Claude respond.{" "}
            <span className="text-white/40">They remember context. But they don&apos;t carry your discussions forward.</span>
          </h2>
          <p className={DECK_SUBTITLE_CLASS}>
            Continuity depends on you. You rewrite the prompt, restate the context, come back and start over. Sometimes it works. Often it doesn&apos;t. So nothing really builds.
          </p>
        </div>

        {/* Problem — three consequences */}
        <div className="cd1-item shrink-0 overflow-x-auto rounded-2xl border border-white/[0.07] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          <div className="min-w-[520px]">
          <div className="grid grid-cols-3">
            {[
              { label: "Patterns missed", body: "Recurring signals across your discussions never surface. You repeat the same loops." },
              { label: "Connections lost", body: "What you figured out last week doesn't inform what you're deciding today." },
              { label: "Never becomes yours", body: "The answer is generic. It could be anyone's. Your sequence, your story, is invisible." },
            ].map((item, i) => (
              <div key={item.label} className={`px-5 py-4 ${i < 2 ? "border-r border-white/[0.06]" : ""}`}>
                <span className="h-1.5 w-1.5 rounded-full bg-rose-400/40 block mb-2" />
                <p className="text-[0.82rem] font-semibold text-white/65 mb-1">{item.label}</p>
                <p className="text-[0.78rem] text-slate-500 leading-[1.55]">{item.body}</p>
              </div>
            ))}
          </div>
          <div className="border-t border-white/[0.04] px-5 py-3 bg-rose-950/20">
            <span className="text-[0.78rem] font-semibold text-rose-300/60">Result: Patterns are missed, and the answer never really becomes yours.</span>
          </div>
          </div>
        </div>

        {/* Solution */}
        <div className="cd1-item rounded-2xl border border-[#8cb7ff]/15 bg-[#8cb7ff]/[0.05] px-6 py-6">
          <div className="mb-4 text-[9px] font-semibold uppercase tracking-[0.3em] text-[#8cb7ff]/55">Solution</div>

          <p className="text-[clamp(0.82rem,1vw,0.95rem)] leading-[1.75] text-slate-500">
            Sakhi carries the thread. Across days, across topics, it tracks where your discussions go and knows which parts matter to what you&apos;re asking now.
          </p>
          <p className="mt-2 mb-5 text-[clamp(0.82rem,1vw,0.95rem)] font-semibold text-[#8cb7ff]/80">
            The answer becomes yours.
          </p>

          <div className="border-t border-[#8cb7ff]/10 pt-5">
            <h3 className="text-[clamp(1rem,1.5vw,1.25rem)] font-bold leading-[1.25] tracking-[-0.03em] text-white">
              You don&apos;t restate. You don&apos;t restructure. You just continue.
            </h3>
            <ul className="mt-4 grid gap-2.5 sm:grid-cols-3">
              {[
                "Patterns across your days surface without you having to narrate them.",
                "The right thread for the right moment. Not just time — contextual sequence.",
                "Answers from your own history reach you when they matter.",
              ].map((t) => (
                <li key={t} className="flex gap-2.5 text-[0.82rem] leading-[1.55] text-slate-400">
                  <span className="mt-[0.4em] h-1 w-1 shrink-0 rounded-full bg-[#8cb7ff]/40" />{t}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Footnote */}
        <div className="cd1-item shrink-0 border-t border-white/[0.05] pt-3 text-[0.68rem] leading-[1.5] text-white/20">
          6,200 thoughts a day. Most scattered, forgotten. &nbsp;<sup>1</sup> Tseng &amp; Poppenk. <em>Nature Communications</em>, 2020. doi:10.1038/s41467-020-17255-9
        </div>

      </div>
    </div>
  );
}

// ── Slide 2 — How Sakhi Solves It ────────────────────────────────────────────
function Slide02HowItSolves(_props: { onWatchStory?: () => void }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const ctx = gsap.context(() => {
      gsap.set(".cd-sol-item", { opacity: 0, y: 18 });
      gsap.timeline({ defaults: { ease: "power2.out" } })
        .to(".cd-sol-item", { opacity: 1, y: 0, stagger: 0.1, duration: 0.6 }, 0.2);
    }, ref);
    return () => ctx.revert();
  }, []);

  const steps = [
    {
      tag: "Capture",
      heading: "Start anywhere.",
      body: "Thoughts, dilemmas, decisions, and open loops enter naturally. No structure required.",
      accent: "#f59e0b",
      dim: "rgba(245,158,11,0.07)",
      border: "rgba(245,158,11,0.18)",
      image: "/story/chat.png",
    },
    {
      tag: "Thread",
      heading: "Thinking stays connected.",
      body: "Scattered thinking becomes a thread you can continue across time.",
      accent: "#8cb7ff",
      dim: "rgba(140,183,255,0.07)",
      border: "rgba(140,183,255,0.20)",
      image: "/story/life-occupancy.PNG",
    },
    {
      tag: "Reflect",
      heading: "Patterns surface when it matters.",
      body: "When you return, Sakhi brings back the patterns and prior thinking that matter most.",
      accent: "#2dd4bf",
      dim: "rgba(45,212,191,0.07)",
      border: "rgba(45,212,191,0.18)",
      image: "/story/continuity.PNG",
    },
  ];

  return (
    <div ref={ref} className="absolute inset-0 flex flex-col px-6 pt-12 pb-4 sm:px-10 sm:pt-14 sm:pb-5 lg:px-14 lg:pt-12 lg:pb-6">
      <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-3 min-h-0">

        {/* Header */}
        <div className="cd-sol-item shrink-0">
          <div className={DECK_HEADER_BADGE_CLASS}>
            <span className="h-1.5 w-1.5 rounded-full bg-[#8cb7ff]/70" />How Sakhi Solves It
          </div>
          <h2 className={DECK_TITLE_CLASS}>
            How Sakhi turns thinking into a thread you can continue.
          </h2>
          <p className="mt-1.5 max-w-4xl text-[clamp(0.78rem,0.95vw,0.9rem)] leading-[1.55] text-slate-400">
            It captures what matters, organizes it into a thread, and brings it back when it matters.
          </p>
        </div>

        {/* Mechanism blocks — flex-1 + min-h-0 so they fill remaining height */}
        <div className="cd-sol-item grid min-h-0 flex-1 gap-3 lg:grid-cols-3">
          {steps.map((s, i) => (
            <div
              key={s.tag}
              className="flex min-h-0 flex-col rounded-2xl border px-4 py-4"
              style={{ background: s.dim, borderColor: s.border }}
            >
              {/* Tag + number */}
              <div className="mb-2 flex shrink-0 items-center gap-2">
                <span className="flex h-5 w-5 items-center justify-center rounded-full border text-[9px] font-bold" style={{ borderColor: s.accent, color: s.accent }}>{i + 1}</span>
                <span className="text-[9px] font-semibold uppercase tracking-[0.3em]" style={{ color: s.accent }}>{s.tag}</span>
              </div>
              {/* Text */}
              <h3 className="shrink-0 text-[clamp(0.85rem,1.1vw,1rem)] font-bold leading-[1.25] tracking-[-0.02em] text-white">
                {s.heading}
              </h3>
              <p className="mt-1.5 shrink-0 text-[clamp(0.72rem,0.85vw,0.82rem)] leading-[1.5] text-slate-400">{s.body}</p>
              {/* Image — fills remaining card space */}
              <div className="mt-3 min-h-0 flex-1 overflow-hidden rounded-xl border border-white/[0.06] bg-white/[0.02]">
                <Image
                  src={s.image}
                  alt={s.tag}
                  width={600}
                  height={800}
                  className="h-full w-full object-contain object-top"
                  style={{ maxHeight: "100%" }}
                />
              </div>
            </div>
          ))}
        </div>

        {/* Bottom bar */}
        <div className="cd-sol-item shrink-0 rounded-xl border border-white/[0.07] bg-white/[0.02] px-5 py-2.5">
          <p className="text-[clamp(0.74rem,0.88vw,0.84rem)] leading-[1.5] text-slate-400">
            Unlike ChatGPT or Notes, Sakhi is not session-based.{" "}
            <span className="font-semibold text-white">It is thread-based. That is the product difference.</span>
          </p>
        </div>

      </div>
    </div>
  );
}

// ── Slide 3 — The Long Game ───────────────────────────────────────────────────
function Slide02LongGame() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const ctx = gsap.context(() => {
      gsap.set(".cd-lg-item", { opacity: 0, y: 20 });
      gsap.timeline({ defaults: { ease: "power2.out" } })
        .to(".cd-lg-item", { opacity: 1, y: 0, stagger: 0.12, duration: 0.7 }, 0.2);
    }, ref);
    return () => ctx.revert();
  }, []);

  const pillars = [
    { label: "Today", heading: "A continuity product people return to", body: "Sakhi helps people continue their thinking across time, not just within one session. It brings back what matters, so returning feels natural instead of starting over.", detail: "People return because the context continues over time." },
    { label: "Tomorrow", heading: "A continuity layer across life", body: "Sakhi becomes the system that holds your ongoing context: what you care about, what you are navigating, what keeps repeating, and how your thinking evolves.", detail: "Every AI tool you use already knows where you are." },
    { label: "The Vision", heading: "Infrastructure for the human mind", body: "Every AI system will get smarter. The missing layer is the one that knows you across time: your threads, patterns, priorities, and becoming. That is the layer Sakhi is building.", detail: "Not a feature. A foundation." },
  ];

  return (
    <div ref={ref} className="absolute inset-0 flex flex-col px-6 pt-14 pb-4 sm:px-12 sm:pt-14 sm:pb-7 lg:px-16 lg:pt-12 lg:pb-10">
      <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-8">

        <div className="cd-lg-item shrink-0">
          <div className={DECK_HEADER_BADGE_CLASS}>
            <span className="h-1.5 w-1.5 rounded-full bg-[#8cb7ff]/70" />Vision
          </div>
          <h2 className={DECK_TITLE_CLASS}>
            <span className="text-white/35">Every LLM wants to be your interface.</span><br />
            Sakhi is the continuity layer for the human mind.
          </h2>
        </div>

        <div className="cd-lg-item grid gap-5 lg:grid-cols-3">
          {pillars.map((p, i) => (
            <div key={p.label} className={`flex flex-col rounded-2xl border px-6 py-6 ${
              i === 2
                ? "border-[#8cb7ff]/20 bg-gradient-to-br from-[#8cb7ff]/[0.09] to-[#8cb7ff]/[0.02]"
                : "border-white/[0.07] bg-white/[0.02]"
            }`}>
              <div className="mb-4 text-[9px] font-semibold uppercase tracking-[0.3em] text-white/28">{p.label}</div>
              <h3 className={`text-[clamp(1rem,1.4vw,1.2rem)] font-bold leading-[1.2] tracking-[-0.03em] ${i === 2 ? "text-[#c8d8ff]" : "text-white/80"}`}>
                {p.heading}
              </h3>
              <p className="mt-3 text-[0.83rem] leading-[1.65] text-slate-400">{p.body}</p>
              <p className={`mt-4 text-[0.78rem] font-semibold leading-[1.4] ${i === 2 ? "text-[#8cb7ff]/55" : "text-white/30"}`}>{p.detail}</p>
            </div>
          ))}
        </div>

        <div className="cd-lg-item shrink-0 rounded-2xl border border-[#8cb7ff]/10 bg-[#8cb7ff]/[0.03] px-6 py-4">
          <p className="text-[clamp(0.88rem,1.05vw,1rem)] leading-[1.65] text-slate-400">
            The physical world has infrastructure.{" "}
            <span className="text-white/60">The mind has none. Sakhi is built to become it.</span>
          </p>
        </div>

      </div>
    </div>
  );
}

// ── Slide 3 — Market Opportunity ─────────────────────────────────────────────
function Slide02Market() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const ctx = gsap.context(() => {
      gsap.set(".cd2-item", { opacity: 0, y: 18 });
      gsap.timeline({ defaults: { ease: "power2.out" } })
        .to(".cd2-item", { opacity: 1, y: 0, stagger: 0.09, duration: 0.6 }, 0.2);
    }, ref);
    return () => ctx.revert();
  }, []);

  const tam = [
    { label: "TAM", size: "500M+", detail: "People navigating ongoing, unresolved threads across work, relationships, health, and self-direction.", market: "$80B by 2030²" },
    { label: "SAM", size: "75M", detail: "US & UK adults already trying to manage ongoing decisions, clarity, and mental load with existing tools.", market: "$9.0B³" },
    { label: "SOM", size: "100K", detail: "Initial wedge: founders, operators, and high-agency professionals managing unresolved threads across work and life.\n100K target users in 18 months → 10K paid → $2.0–2.4M ARR", market: "$2.0–2.4M ARR" },
  ];

  const comps = [
    { name: "Notion", signal: "$10B valuation on personal + team knowledge⁴" },
    { name: "Day One", signal: "Acquired by Automattic; journaling alone had exit value⁵" },
    { name: "Rewind", signal: "$75M raised on passive desktop recall alone⁶" },
    { name: "Replika", signal: "10M+ users seeking connection, but it forgets. No model of you.⁷" },
  ];

  return (
    <div ref={ref} className="absolute inset-0 flex flex-col px-6 pt-12 pb-3 sm:px-12 sm:pt-14 sm:pb-4 lg:px-16 lg:pt-12 lg:pb-4">
      <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-3 min-h-0">

        {/* Header */}
        <div className="cd2-item shrink-0">
          <div className={DECK_HEADER_BADGE_CLASS}>
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400/70" />Why Now
          </div>
          <h2 className={DECK_TITLE_CLASS}>
            The number isn&apos;t the story. The timing is.
          </h2>
          <p className={DECK_SUBTITLE_CLASS}>
            This is not just a large market. It is a newly opened window, where technical capability, user behavior, and unmet need have finally converged.
          </p>
          <p className="mt-3 max-w-4xl text-[0.84rem] leading-[1.6] text-slate-500">
            We are starting with founders and high-agency operators managing unresolved decisions across work and life, because they feel the cost of fragmented thinking earliest and most often.
          </p>
        </div>

        {/* Why Now cards */}
        <div className="cd2-item shrink-0 grid gap-3 sm:grid-cols-3">
          {[
            { num: "1", label: "The primitives are finally here", tag: "Model Shift", body: "AI can now hold conversations that are richer in thought and nuance, making a continuity layer possible for the first time." },
            { num: "2", label: "People now think out loud with AI", tag: "Behavior Shift", body: "People now externalize thoughts, dilemmas, and emotions into AI as a natural behavior. Something that barely existed 2–3 years ago." },
            { num: "3", label: "No one owns continuity", tag: "Category Gap", body: "Notes apps store. AI chats respond. Nobody compounds thought over time." },
          ].map((w) => (
            <div key={w.num} className="rounded-2xl border border-[#8cb7ff]/12 bg-[#8cb7ff]/[0.04] px-4 py-4">
              <div className="mb-1.5 flex items-center gap-2">
                <span className="flex h-5 w-5 items-center justify-center rounded-full border border-[#8cb7ff]/40 text-[9px] font-bold text-[#8cb7ff]/80">{w.num}</span>
                <span className="text-[9px] font-semibold uppercase tracking-[0.28em] text-[#8cb7ff]/70">{w.tag}</span>
              </div>
              <div className="text-[0.85rem] font-semibold leading-[1.25] tracking-[-0.01em] text-white">{w.label}</div>
              <p className="mt-1.5 text-[0.75rem] leading-[1.5] text-slate-400">{w.body}</p>
            </div>
          ))}
        </div>

        {/* TAM / SAM / SOM */}
        <div className="cd2-item shrink-0 grid gap-3 sm:grid-cols-3">
          {tam.map((t) => (
            <div key={t.label} className="rounded-2xl border border-white/[0.08] bg-white/[0.03] px-4 py-3">
              <div className="text-[9px] font-semibold uppercase tracking-[0.3em] text-emerald-400/70">{t.label}</div>
              <div className="mt-1 text-[clamp(1.6rem,2.8vw,2.4rem)] font-bold leading-none tracking-[-0.06em] text-white">{t.size}</div>
              <p className="mt-1.5 whitespace-pre-line text-[0.72rem] leading-[1.45] text-slate-400">{t.detail}</p>
              <div className="mt-2 text-[9px] font-semibold uppercase tracking-[0.22em] text-emerald-400/60">{t.market}</div>
            </div>
          ))}
        </div>

        {/* Comparable signals */}
        <div className="cd2-item shrink-0">
          <div className="mb-2 text-[9px] font-semibold uppercase tracking-[0.3em] text-white/30">Behavioral Proof</div>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            {comps.map((c) => (
              <div key={c.name} className="rounded-xl border border-white/[0.07] bg-white/[0.02] px-3 py-2.5">
                <div className="text-[0.8rem] font-semibold tracking-[-0.02em] text-white/80">{c.name}</div>
                <p className="mt-1 text-[0.72rem] leading-[1.45] text-slate-500">{c.signal}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="cd2-item shrink-0 rounded-2xl border border-[#8cb7ff]/15 bg-[#8cb7ff]/[0.04] px-4 py-3">
          <p className="text-[0.85rem] leading-[1.55] text-[#8cb7ff]/70">
            Nobody owns the continuity layer. That gap is the company.
          </p>
        </div>

        <div className="cd2-item shrink-0 max-h-[2.8rem] overflow-y-auto border-t border-white/[0.05] pt-1.5 text-[0.6rem] leading-[1.4] text-white/18 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          <p><sup>2</sup> Combined TAM: Precedence Research, <em>Mental Health Apps Market</em>, 2023; Grand View Research, <em>Productivity Management Software Market</em>, 2023. &nbsp;<sup>3</sup> BLS, <em>Occupational Employment Statistics</em>, 2023 (US: ~63M); ONS, <em>Labour Force Survey</em>, 2023 (UK: ~12M). SAM reflects subset already paying for a productivity or wellness subscription.</p>
          <p><sup>4</sup> Notion Series C at $10B valuation, Oct 2021. &nbsp;<sup>5</sup> Automattic acquisition of Day One, 2021. &nbsp;<sup>6</sup> Rewind AI funding rounds, TechCrunch, 2022–2023. &nbsp;<sup>7</sup> Replika public user count, Luka Inc. press, 2023.</p>
        </div>

      </div>
    </div>
  );
}

// ── Slide 4 — Why It Doesn't Exist ───────────────────────────────────────────
function Slide03Gap() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const ctx = gsap.context(() => {
      gsap.set(".cd3-item", { opacity: 0, y: 18 });
      gsap.timeline({ defaults: { ease: "power2.out" } })
        .to(".cd3-item", { opacity: 1, y: 0, stagger: 0.09, duration: 0.6 }, 0.2);
    }, ref);
    return () => ctx.revert();
  }, []);

  const competitors = [
    { category: "AI Assistants",   name: "ChatGPT / Claude / Gemini",   does: "Answers questions",           misses: "Resets every session. No model of you." },
    { category: "Knowledge Tools", name: "Notion / Obsidian / Roam",    does: "Stores notes",                misses: "Manual. No inference. No emotional layer." },
    { category: "Journaling",      name: "Day One / Reflectly",         does: "Captures thoughts",           misses: "No intelligence. Passive archive." },
    { category: "Passive Recall",  name: "Rewind / Limitless",          does: "Records everything",          misses: "No personal model. No meaning-making." },
    { category: "Companionship",   name: "Replika / Pi / Character.AI", does: "Builds relational memory",    misses: "Domain-locked to the relationship. Models the bond, not your life." },
    { category: "Mindfulness",     name: "Headspace / Calm",            does: "Session-based calm",          misses: "No continuity. Resets with every session." },
    { category: "Mental Health",   name: "BetterHelp / Talkspace",      does: "Guided therapy",              misses: "Isolated sessions. No longitudinal picture." },
    { category: "Personal AI",     name: "Dot / Kin / Personal.ai",     does: "Stores your life context",    misses: "Retrieval, not inference. An archive, not a model." },
  ];

  return (
    <div ref={ref} className="absolute inset-0 flex flex-col px-6 pt-12 pb-4 sm:px-10 sm:pt-14 sm:pb-5 lg:px-14 lg:pt-12 lg:pb-5">
      <div className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-3 min-h-0">

        <div className="cd3-item shrink-0">
          <div className={DECK_HEADER_BADGE_CLASS}>
            <span className="h-1.5 w-1.5 rounded-full bg-amber-400/70" />Why It Doesn&apos;t Exist
          </div>
          <h2 className={DECK_TITLE_CLASS}>
            Everyone stores. Nobody remembers.
          </h2>
          <p className={DECK_SUBTITLE_CLASS}>
            Today&apos;s tools either answer, archive, or relate. None help your thinking compound across time.
          </p>
        </div>

        {/* Two-column layout — fills remaining height */}
        <div className="cd3-item grid min-h-0 flex-1 gap-3 lg:grid-cols-2">

          {/* Left — table */}
          <div className="flex min-h-0 flex-col overflow-hidden rounded-xl border border-white/[0.08]">
            <div className="text-[9px] font-semibold uppercase tracking-[0.3em] text-white/50 px-3 pt-2 pb-1.5 shrink-0 border-b border-white/[0.06]">Landscape</div>
            <div className="min-h-0 flex-1 overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            <table className="w-full text-left text-[0.7rem]">
              <thead className="sticky top-0">
                <tr className="border-b border-white/[0.07] bg-[#020617]">
                  <th className="px-3 py-1.5 text-[7px] font-semibold uppercase tracking-[0.22em] text-white/25">Company</th>
                  <th className="px-3 py-1.5 text-[7px] font-semibold uppercase tracking-[0.22em] text-white/25">What it does</th>
                  <th className="px-3 py-1.5 text-[7px] font-semibold uppercase tracking-[0.22em] text-amber-400/50">What it misses</th>
                </tr>
              </thead>
              <tbody>
                {competitors.map((c, i) => (
                  <tr key={c.name} className={`border-b border-white/[0.05] ${i % 2 === 0 ? "" : "bg-white/[0.015]"}`}>
                    <td className="px-3 py-2.5">
                      <div className="text-[0.72rem] font-semibold text-white">{c.name}</div>
                      <div className="text-[0.65rem] text-slate-500">{c.category}</div>
                    </td>
                    <td className="px-3 py-2.5 text-[0.72rem] text-slate-400">{c.does}</td>
                    <td className="px-3 py-2.5 text-[0.72rem] text-amber-200/60">{c.misses}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          </div>

          {/* Right — capability matrix */}
          <div className="flex min-h-0 flex-col overflow-hidden rounded-xl border border-white/[0.08] bg-white/[0.02]">
            <div className="text-[9px] font-semibold uppercase tracking-[0.3em] text-white/50 px-3 pt-2 pb-1.5 shrink-0 border-b border-white/[0.06]">Capability map</div>
          <div className="relative min-h-0 flex-1">
              {/* Axis labels */}
              <div className="absolute left-1/2 top-2.5 -translate-x-1/2 text-[7px] font-semibold uppercase tracking-[0.25em] text-[#8cb7ff]/90">Understands your life</div>
              <div className="absolute bottom-2.5 left-1/2 -translate-x-1/2 text-[7px] font-semibold uppercase tracking-[0.25em] text-white/50">Surface-level only</div>
              <div className="absolute left-2 top-[53%] text-[7px] font-semibold uppercase tracking-[0.2em] text-white/50">Forgets you</div>
              <div className="absolute right-2 top-[53%] text-right text-[7px] font-semibold uppercase tracking-[0.2em] text-[#8cb7ff]/90">Remembers &amp; compounds</div>
              {/* Axis lines */}
              <div className="absolute inset-x-8 top-1/2 h-px bg-white/[0.18]" />
              <div className="absolute inset-y-8 left-1/2 w-px bg-white/[0.18]" />
              {/* Bottom-left: surface + forgets */}
              {[
                { label: "ChatGPT",    x: "24%", y: "56%" },
                { label: "Claude",     x: "34%", y: "63%" },
                { label: "Gemini",     x: "15%", y: "67%" },
                { label: "MS Copilot", x: "27%", y: "73%" },
                { label: "Notion",     x: "12%", y: "79%" },
                { label: "Obsidian",   x: "22%", y: "84%" },
                { label: "Roam",       x: "33%", y: "81%" },
                { label: "Day One",    x: "9%",  y: "89%" },
                { label: "Google Keep",x: "38%", y: "88%" },
              ].map((p) => (
                <div key={p.label} className="absolute flex items-center gap-1" style={{ left: p.x, top: p.y }}>
                  <span className="h-1.5 w-1.5 rounded-full bg-white/18" />
                  <span className="text-[8px] text-white/28">{p.label}</span>
                </div>
              ))}
              {/* Bottom-right: remembers but surface-level */}
              {[
                { label: "Rewind",      x: "57%", y: "58%" },
                { label: "Limitless",   x: "70%", y: "65%" },
                { label: "Mem.ai",      x: "60%", y: "73%" },
                { label: "Evernote",    x: "76%", y: "72%" },
                { label: "Readwise",    x: "55%", y: "81%" },
                { label: "Apple Notes", x: "77%", y: "82%" },
                { label: "Capacities",  x: "64%", y: "87%" },
              ].map((p) => (
                <div key={p.label} className="absolute flex items-center gap-1" style={{ left: p.x, top: p.y }}>
                  <span className="h-1.5 w-1.5 rounded-full bg-white/14" />
                  <span className="text-[8px] text-white/24">{p.label}</span>
                </div>
              ))}
              {/* Top-left: understands life but forgets */}
              {[
                { label: "Character.AI", x: "37%", y: "14%" },
                { label: "BetterHelp",   x: "11%", y: "27%" },
                { label: "Talkspace",    x: "23%", y: "32%" },
                { label: "Woebot",       x: "35%", y: "29%" },
                { label: "Headspace",    x: "13%", y: "39%" },
                { label: "Calm",         x: "28%", y: "41%" },
                { label: "Wysa",         x: "39%", y: "38%" },
                { label: "Reflectly",    x: "18%", y: "46%" },
              ].map((p) => (
                <div key={p.label} className="absolute flex items-center gap-1" style={{ left: p.x, top: p.y }}>
                  <span className="h-1.5 w-1.5 rounded-full bg-white/16" />
                  <span className="text-[8px] text-white/26">{p.label}</span>
                </div>
              ))}
              {/* Top-right: understands + remembers — partial fits clustering below Sakhi */}
              {[
                { label: "Replika",     x: "54%", y: "16%" },
                { label: "Pi",          x: "64%", y: "22%" },
                { label: "Dot",         x: "55%", y: "30%" },
                { label: "Kin",         x: "68%", y: "34%" },
                { label: "Personal.ai", x: "58%", y: "40%" },
              ].map((p) => (
                <div key={p.label} className="absolute flex items-center gap-1" style={{ left: p.x, top: p.y }}>
                  <span className="h-1.5 w-1.5 rounded-full bg-white/22" />
                  <span className="text-[8px] text-white/34">{p.label}</span>
                </div>
              ))}
              {/* Sakhi — top right, alone */}
              <div className="absolute flex items-center gap-1.5" style={{ right: "10%", top: "14%" }}>
                <span className="h-2.5 w-2.5 rounded-full bg-[#8cb7ff]/80 shadow-[0_0_14px_rgba(140,183,255,0.55)]" />
                <span className="text-[9px] font-semibold text-[#8cb7ff]">Sakhi</span>
              </div>
            </div>{/* end relative flex-1 */}
          </div>{/* end capability map column */}

        </div>{/* end two-column grid */}

        {/* Qualification statement */}
        <div className="cd3-item shrink-0 rounded-xl border border-[#8cb7ff]/10 bg-[#8cb7ff]/[0.03] px-4 py-2.5">
          <p className="text-[clamp(0.72rem,0.85vw,0.8rem)] leading-[1.6] text-slate-400">
            <span className="text-white/70">All five retrieve. Sakhi infers.</span>{" "}
            Replika, Pi, Dot, Kin, and Personal.ai are building toward the top-right.{" "}
            The difference is an archive of what you said versus a model that helps your thinking compound across time.
          </p>
        </div>

      </div>
    </div>
  );
}

// ── Slide 5 — Why We Win ──────────────────────────────────────────────────────
function Slide04WhyWeWin() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const ctx = gsap.context(() => {
      gsap.set(".cd4w-header,.cd4w-card,.cd4w-proof,.cd4w-note", { opacity: 0, y: 18 });
      gsap.timeline({ defaults: { ease: "power2.out" } })
        .to(".cd4w-header", { opacity: 1, y: 0, duration: 0.55 }, 0.15)
        .to(".cd4w-card", { opacity: 1, y: 0, stagger: 0.08, duration: 0.55 }, 0.35)
        .to(".cd4w-proof", { opacity: 1, y: 0, stagger: 0.12, duration: 0.7 }, 0.48)
        .to(".cd4w-note", { opacity: 1, y: 0, duration: 0.45 }, 0.82);
    }, ref);
    return () => ctx.revert();
  }, []);

  const moat = [
    { label: "Continuity Engine", tag: "Core infrastructure", body: "Sakhi does not just remember what you said. It builds continuity across time, so your context gets stronger every time you return." },
    { label: "Continuity Arc", tag: "Product expression", body: "A thought, decision, or dilemma does not disappear. You can see how it evolved across time." },
    { label: "Thinking That Compounds", tag: "Moat", body: "The more you use Sakhi, the more useful it becomes. Your patterns, decisions, and context build on each other instead of resetting." },
    { label: "Life Occupancy", tag: "Product expression", body: "Sakhi shows what has actually occupied your mind and life across time, not just what you said most recently." },
  ];

  const proofPanels = [
    {
      title: "Life Occupancy",
      tag: "Life Occupancy",
      src: "/story/life-occupancy.PNG",
      alt: "Sakhi reflection screen showing life occupancy",
      tilt: "-rotate-[5deg]",
    },
    {
      title: "Continuity Arc",
      tag: "Continuity Arc",
      src: "/story/continuity.PNG",
      alt: "Sakhi continuity arc screen",
      tilt: "rotate-[4deg]",
    },
  ];

  return (
    <div ref={ref} className="slide-scroll-panel absolute inset-0 overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden flex flex-col justify-start px-6 pt-14 pb-20 sm:px-10 sm:pt-14 sm:pb-6 lg:px-14 lg:pt-12 lg:pb-8">
      <div className="mx-auto w-full max-w-7xl">
        <div className="cd4w-header mx-auto mb-7 w-full max-w-6xl">
          <div className={DECK_HEADER_BADGE_CLASS}>
            <span className="h-1.5 w-1.5 rounded-full bg-[#8cb7ff]/70" />Why We Win
          </div>
          <h2 className={DECK_TITLE_CLASS}>
            The continuity model Sakhi builds is the moat.
          </h2>
          <p className={DECK_SUBTITLE_CLASS}>
            Not the interface. Not the features. The continuity Sakhi builds across time is what makes the product more useful every time someone returns.
          </p>
        </div>

        <div className="mx-auto grid max-w-6xl items-center gap-8 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)] lg:gap-10">
          <div className="grid gap-3 sm:grid-cols-2">
            {moat.map((m) => {
              const isProduct = m.tag.toLowerCase() === "product expression";
              return (
                <div key={m.label} className={`cd4w-card rounded-2xl border px-5 py-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.03)] ${isProduct ? "border-teal-400/20 bg-[linear-gradient(135deg,rgba(94,234,212,0.08),rgba(45,212,191,0.04))]" : "border-white/[0.07] bg-white/[0.03]"}`}>
                  <div className="text-[0.92rem] font-bold tracking-[-0.02em] text-white">{m.label}</div>
                  <div className={`mt-1 text-[8px] font-semibold uppercase tracking-[0.22em] ${isProduct ? "text-teal-400/70" : "text-white/25"}`}>{m.tag}</div>
                  <p className="mt-3 text-[0.81rem] leading-[1.65] text-slate-400">{m.body}</p>
                </div>
              );
            })}
          </div>

          <div className="relative flex min-h-[29rem] items-center justify-center rounded-[34px] border border-white/[0.07] bg-[linear-gradient(160deg,rgba(13,18,31,0.98),rgba(7,10,20,0.96))] px-6 py-8 shadow-[0_36px_120px_rgba(0,0,0,0.32)]">
            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_22%_24%,rgba(111,144,221,0.12),transparent_28%),radial-gradient(circle_at_78%_74%,rgba(183,126,63,0.10),transparent_26%)]" />
            <div className="relative z-10 flex w-full max-w-[34rem] items-center justify-center gap-2 sm:gap-4">
              {proofPanels.map((panel) => (
                <div key={panel.title} className={`cd4w-proof flex flex-col items-center ${panel.tilt}`}>
                  <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-[8px] font-semibold uppercase tracking-[0.24em] text-white/40">
                    <span className="h-1.5 w-1.5 rounded-full bg-[#8cb7ff]/65" />
                    {panel.tag}
                  </div>
                  <div className="relative flex flex-col items-center rounded-[34px] border border-[rgba(189,206,225,0.12)] bg-[linear-gradient(180deg,rgba(18,28,45,0.78),rgba(8,13,24,0.54))] px-3 pb-4 pt-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.05),0_20px_60px_rgba(0,0,0,0.28)]">
                    <div className="mb-2.5 h-[5px] w-[76px] rounded-full bg-white/10" />
                    <div className="relative overflow-hidden rounded-[28px] border border-[rgba(203,213,225,0.16)] bg-[#040914] shadow-[0_30px_80px_rgba(0,0,0,0.46)]">
                      <Image
                        src={panel.src}
                        alt={panel.alt}
                        width={720}
                        height={1280}
                        className="block h-auto w-[min(220px,26vw)] min-w-[170px]"
                      />
                    </div>
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

// ── Slide 4 — Revenue Model ───────────────────────────────────────────────────
function Slide04Revenue() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const ctx = gsap.context(() => {
      gsap.set(".cd4-item", { opacity: 0, y: 18 });
      gsap.timeline({ defaults: { ease: "power2.out" } })
        .to(".cd4-item", { opacity: 1, y: 0, stagger: 0.09, duration: 0.6 }, 0.2);
    }, ref);
    return () => ctx.revert();
  }, []);

  const tiers = [
    { name: "Free", price: "$0", color: "border-white/8 bg-white/[0.02]", tag: "Limited continuity", features: ["Start seeing your life more clearly", "30-day active memory window", "3 Deep Reflects/mo. Limited continuity. Your model does not fully compound.."] },
    { name: "Pro", price: "$20/mo", color: "border-[#8cb7ff]/20 bg-[#8cb7ff]/[0.05]", tag: "Full continuity across time", features: ["Your thinking compounds instead of resetting.", "Understand what's really going on across weeks, not moments", "See patterns, cycles, and decisions clearly", "Full Arc. Full history. Unlimited Deep Reflect.", "Annual plan: $180/yr"] },
    { name: "Collective", price: "$30/user/mo", color: "border-amber-400/12 bg-amber-400/[0.04]", tag: "Continuity across people", features: ["Continuity across people. Year 2.", "Each person builds their own model", "Shared context across relationships. Think together, not in fragments.", "Privacy-first by design"] },
  ];

  const trajectory = [
    { period: "Month 12", users: "2,000+ paying", arr: "$35–40K MRR" },
    { period: "Month 18", users: "10,000+ paying", arr: "$2.0–2.4M ARR" },
    { period: "Month 24", users: "50,000+ paying", arr: "$10–12M ARR", note: "Collective launch + referral loop" },
  ];

  const unitEcon = [
    { label: "Blended CAC target", value: "$20–35⁸" },
    { label: "ARPU", value: "$240/yr" },
    { label: "LTV:CAC (yr 1)", value: "7–12×" },
    { label: "Gross margin (Yr 2)", value: "50–65%⁸" },
  ];

  return (
    <div ref={ref} className="slide-scroll-panel absolute inset-0 overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden px-6 pt-14 pb-20 sm:px-12 sm:pt-14 sm:pb-6 lg:px-16 lg:pt-12 lg:pb-8">
      <div className="mx-auto max-w-6xl">
        <div className="cd4-item mb-7">
          <div className={DECK_HEADER_BADGE_CLASS}>
            <span className="h-1.5 w-1.5 rounded-full bg-violet-400/70" />Revenue Model
          </div>
          <h2 className={DECK_TITLE_CLASS}>
            Simple. Subscription-first. Value compounds over time.
          </h2>
        </div>

        {/* Pricing tiers */}
        <div className="cd4-item grid gap-4 sm:grid-cols-3">
          {tiers.map((t) => (
            <div key={t.name} className={`rounded-2xl border px-5 py-5 ${t.color}`}>
              <div className="flex items-start justify-between gap-2">
                <div className="text-[1rem] font-bold tracking-[-0.02em] text-white">{t.name}</div>
                <div className="text-[0.82rem] font-semibold text-white/50">{t.price}</div>
              </div>
              <div className="mt-1 text-[8px] font-semibold uppercase tracking-[0.22em] text-white/28">{t.tag}</div>
              <ul className="mt-4 space-y-2">
                {t.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-[0.78rem] leading-[1.5] text-slate-400">
                    <span className="mt-[0.4em] h-1 w-1 shrink-0 rounded-full bg-white/25" />{f}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <p className="cd4-item mt-6 text-[clamp(1rem,1.4vw,1.25rem)] font-bold leading-[1.4] tracking-[-0.02em] text-white">Sakhi is not a subscription for usage.<br /><span className="text-[#8cb7ff]">It is a subscription for thinking that compounds.</span></p>

        <div className="cd4-item mt-5 grid gap-4 sm:grid-cols-2">
          {/* Unit economics */}
          <div>
            <div className="mb-3 text-[9px] font-semibold uppercase tracking-[0.3em] text-white/30">Unit economics</div>
            <div className="grid grid-cols-2 gap-3">
              {unitEcon.map((u) => (
                <div key={u.label} className="rounded-xl border border-white/[0.07] bg-white/[0.02] px-4 py-3">
                  <div className="text-[8px] font-semibold uppercase tracking-[0.22em] text-white/30">{u.label}</div>
                  <div className="mt-1 text-[1.1rem] font-bold tracking-[-0.04em] text-white/88">{u.value}</div>
                </div>
              ))}
            </div>
            <p className="mt-2 text-[0.72rem] leading-[1.5] text-slate-500">Memory-intensive inference (long-context reflection, thread surfacing) keeps COGS elevated in Year 1. Margin improves as caching and batching mature.</p>
            <p className="mt-1.5 text-[0.68rem] leading-[1.5] text-white/20"><sup>8</sup> Blended CAC reflects full channel mix: organic ($0–12), creator partnerships ($8–15), and paid acquisition ($10–20) scaling through Month 18. Gross margin assumes frontier model (GPT-4o / Claude Sonnet) for all substantive interactions; improves as inference costs decline and caching matures.</p>
          </div>

          {/* Initial Wedge */}
          <div>
            <div className="mb-3 text-[9px] font-semibold uppercase tracking-[0.3em] text-white/30">Initial Wedge</div>
            <div className="space-y-2.5">
              {trajectory.map((t) => (
                <div key={t.period} className="rounded-xl border border-white/[0.07] bg-white/[0.02] px-4 py-3">
                  <div className="flex items-center justify-between">
                    <div className="text-[0.78rem] font-semibold text-white/50">{t.period}</div>
                    <div className="text-[0.78rem] text-slate-400">{t.users}</div>
                    <div className="text-[0.82rem] font-bold tracking-[-0.02em] text-emerald-300/80">{t.arr}</div>
                  </div>
                  {"note" in t && t.note && (
                    <div className="mt-1 text-[0.68rem] text-white/25">{t.note}</div>
                  )}
                </div>
              ))}
            </div>
            <p className="mt-2 text-[0.68rem] leading-[1.5] text-white/22">Ranges reflect blended conversion and churn assumptions. Lower bound assumes 10–15% monthly churn on paying cohorts; upper bound assumes improving retention as the continuity model matures.</p>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Slide 5 — The Ask ─────────────────────────────────────────────────────────
function Slide05Ask() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const ctx = gsap.context(() => {
      gsap.set(".cd5-item", { opacity: 0, y: 18 });
      gsap.timeline({ defaults: { ease: "power2.out" } })
        .to(".cd5-item", { opacity: 1, y: 0, stagger: 0.09, duration: 0.6 }, 0.2);
    }, ref);
    return () => ctx.revert();
  }, []);

  const milestones = [
    { tag: "Product", heading: "Launch a continuity product ready to serve 10K+ users", body: "With Continuity Engine V2, sensing layer, and mobile product live, moving from memory to real-life context." },
    { tag: "Retention / Behavior", heading: "Prove continuity becomes a retained behavior", body: "Strong Day-30 and 60%+ Day-90 retention in a defined ICP, showing users come back because their context compounds." },
    { tag: "Monetization", heading: "Validate willingness to pay for thinking that compounds", body: "10,000 active users, 2,000+ paying, and $35–40K MRR run-rate." },
    { tag: "Fundraise Bridge", heading: "Earn the Seed by proving continuity is both habit-forming and monetizable", body: "Target: Month 12–15 | $4–5M at $15–20M valuation" },
  ];

  const allocation = [
    { pct: "48%", amount: "$600K", label: "Product + Engineering", detail: "Core team, infra, AI, design, QA" },
    { pct: "22%", amount: "$275K", label: "Growth", detail: "Content, community, partnerships, paid" },
    { pct: "6%",  amount: "$75K",  label: "Compliance + Legal", detail: "C-Corp, India entity, IP, GDPR, HealthKit" },
    { pct: "4%",  amount: "$50K",  label: "Operations", detail: "Payroll, tools, accounting, admin" },
    { pct: "20%", amount: "$250K", label: "Runway + Buffer", detail: "18-month total runway. Buffer for Seed timing." },
  ];

  return (
    <div ref={ref} className="slide-scroll-panel absolute inset-0 overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden px-6 pt-14 pb-20 sm:px-12 sm:pt-14 sm:pb-6 lg:px-16 lg:pt-12 lg:pb-8">
      <div className="mx-auto max-w-6xl">
        <div className="cd5-item mb-8 text-center">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3.5 py-1.5 text-[9px] font-semibold uppercase tracking-[0.3em] text-white/40">
            <span className="h-1.5 w-1.5 rounded-full bg-[#8cb7ff]/70" />Pre-Seed Round
          </div>
          <div className="text-[clamp(3.5rem,7vw,6rem)] font-bold leading-none tracking-[-0.07em] text-white">$1,250,000</div>
          <p className="mt-3 text-[clamp(0.95rem,1.3vw,1.2rem)] text-slate-400">
            Raising $1.25M to test one core thesis:{" "}
            <span className="text-white/60">continuity can become a retained consumer behavior and a real subscription business.</span>
          </p>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          {/* Milestones */}
          <div className="cd5-item">
            <div className="mb-3 text-[9px] font-semibold uppercase tracking-[0.3em] text-white/30">What this round proves (in 12 months)</div>
            <div className="space-y-2.5">
              {milestones.map((m, i) => (
                <div key={i} className={`rounded-xl border px-4 py-3.5 ${i === 3 ? "border-emerald-400/15 bg-emerald-400/[0.04]" : "border-white/[0.07] bg-white/[0.02]"}`}>
                  <div className={`mb-1 text-[8px] font-semibold uppercase tracking-[0.22em] ${i === 3 ? "text-emerald-300/60" : "text-[#8cb7ff]/60"}`}>{m.tag}</div>
                  <p className={`text-[clamp(0.82rem,1vw,0.9rem)] font-semibold leading-[1.4] ${i === 3 ? "text-emerald-300/90" : "text-white/85"}`}>{m.heading}</p>
                  <p className={`mt-1 text-[0.78rem] leading-[1.5] ${i === 3 ? "text-emerald-300/55" : "text-slate-400"}`}>{m.body}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Use of funds */}
          <div className="cd5-item">
            <div className="mb-3 text-[9px] font-semibold uppercase tracking-[0.3em] text-white/30">Use of funds</div>
            <div className="space-y-3">
              {allocation.map((a) => (
                <div key={a.label} className="rounded-xl border border-white/[0.07] bg-white/[0.02] px-4 py-4">
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                      <span className="text-[0.78rem] font-semibold tabular-nums text-white/30 w-8 shrink-0">{a.pct}</span>
                      <div>
                        <div className="text-[0.92rem] font-bold text-white/88">{a.label}</div>
                        <div className="text-[0.75rem] text-slate-500">{a.detail}</div>
                      </div>
                    </div>
                    <div className="text-[0.9rem] font-bold tracking-[-0.03em] text-[#c8d8ff]/60 shrink-0">{a.amount}</div>
                  </div>
                  <div className="mt-3 h-1 w-full overflow-hidden rounded-full bg-white/[0.06]">
                    <div className="h-full rounded-full bg-[#8cb7ff]/40" style={{ width: a.pct }} />
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

// ── Slide 6 — Compact founders narrative ─────────────────────────────────────
const FOUNDERS_COMPACT = [
  {
    name: "Vidhya Padmanabhan",
    role: "Co-Founder & CEO",
    image: "/story/v-pic-20260327.png",
    imageStyle: {},
    bio: "Built systems for companies. Now building one for humans.",
    quote:
      "I've spent 20+ years helping organizations make better decisions. I realized we haven't solved this for individuals.",
    beats: [
      { tag: "The Foundation", text: "20+ years partnering with CEOs and COOs at a $4B public company and a high-growth SaaS firm serving large enterprises." },
      { tag: "Personal Inflection Point", text: "Caregiving, leadership, and life complexity, all at once. Continuity was missing." },
      { tag: "Insight to Sakhi", text: "Timing and personalization beat generic advice. Could this be a system?" },
    ],
    closing: "\"Sakhi is the system I wish existed when I needed it most.\"",
    accent: "#c4d2ff",
  },
  {
    name: "Ravi Shankar",
    role: "Co-Founder & CTO",
    image: "/story/r-pic.png",
    imageStyle: { objectPosition: "50% 24%" },
    bio: "Built systems across engineering, product, and AI. Now building one for the self.",
    quote:
      "I'm a systems thinker at heart, grounded in deep technical expertise and driven to simplify complexity.",
    beats: [
      { tag: "Evolution", text: "Engineering first. Kept moving toward what actually makes systems work." },
      { tag: "Realization", text: "Systems succeed because people trust and use them. Not just because they are built well." },
      { tag: "Expansion", text: "Engineering, product, product marketing. Yoga and meditation deepened how he reads human behavior over time." },
      { tag: "Convergence", text: "Technical depth, systems thinking, and lived understanding of people. All of it builds Sakhi." },
    ],
    closing: "\"That gives me the clarity to build Sakhi.\"",
    accent: "#bfe3ff",
  },
] as const;

function Slide06FoundersCompact() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const ctx = gsap.context(() => {
      gsap.set(".cd7-head,.cd7-card", { opacity: 0, y: 16 });
      gsap.timeline({ defaults: { ease: "power2.out" } })
        .to(".cd7-head", { opacity: 1, y: 0, duration: 0.55 }, 0.2)
        .to(".cd7-card", { opacity: 1, y: 0, stagger: 0.1, duration: 0.65 }, 0.38);
    }, ref);
    return () => ctx.revert();
  }, []);

  return (
    <div ref={ref} className="slide-scroll-panel absolute inset-0 overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden px-5 pt-14 pb-20 sm:px-10 sm:pt-14 sm:pb-6 lg:px-14 lg:pt-12 lg:pb-8">
      <div className="mx-auto max-w-7xl">
        <div className="cd7-head mb-7">
          <p className={DECK_HEADER_BADGE_CLASS}>
            <span className="h-1.5 w-1.5 rounded-full bg-[#8cb7ff]/70" />Founders
          </p>
          <h2 className={DECK_TITLE_CLASS}>
            The Minds Behind Sakhi
          </h2>
        </div>

        <div className="grid gap-5 lg:grid-cols-2">
          {FOUNDERS_COMPACT.map((founder) => (
            <div key={founder.name} className="cd7-card rounded-[28px] border border-white/[0.09] bg-[linear-gradient(160deg,rgba(16,23,39,0.9),rgba(7,11,21,0.82))] p-5">
              <div className="grid gap-5 sm:grid-cols-[9.5rem_minmax(0,1fr)]">
                <div className="mx-auto w-[9.5rem] sm:mx-0">
                  <div className="relative rounded-[22px] border border-white/10 bg-white/[0.03] p-2">
                    <div className="relative aspect-[3/4] overflow-hidden rounded-[18px]">
                      <Image src={founder.image} alt={founder.name} fill className="object-cover" style={founder.imageStyle} />
                    </div>
                    <div className="mt-2 rounded-[12px] border border-white/10 bg-[rgba(7,11,18,0.72)] px-2.5 py-2">
                      <div className="text-[0.82rem] font-semibold text-white">{founder.name}</div>
                      <div className="mt-0.5 text-[9px] font-medium uppercase tracking-[0.16em] text-white/58">{founder.role}</div>
                    </div>
                  </div>
                </div>

                <div>
                  <p className="text-[0.86rem] leading-[1.5] text-white/58">{founder.bio}</p>
                  <p className="mt-3 text-[clamp(1.05rem,1.3vw,1.35rem)] font-semibold leading-[1.3] tracking-[-0.03em] text-white">
                    {founder.quote}
                  </p>
                  <div className="mt-4 space-y-2.5">
                    {founder.beats.map((beat) => (
                      <div key={typeof beat === "string" ? beat : beat.tag} className="rounded-xl border border-white/[0.08] bg-white/[0.03] px-3.5 py-2.5 text-[0.78rem] leading-[1.5] text-slate-300">
                        {typeof beat === "string" ? beat : (
                          <>
                            <span className="mr-1.5 text-[0.68rem] font-semibold uppercase tracking-[0.18em]" style={{ color: founder.accent }}>{beat.tag}</span>
                            <span className="text-slate-300">{beat.text}</span>
                          </>
                        )}
                      </div>
                    ))}
                  </div>
                  <p className="mt-4 text-[0.9rem] font-medium leading-6 text-white/85" style={{ color: founder.accent }}>
                    {founder.closing}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── GTM Slide ─────────────────────────────────────────────────────────────────
function SlideGTM() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const ctx = gsap.context(() => {
      gsap.set(".gtm-item", { opacity: 0, y: 18 });
      gsap.set(".gtm-bar", { opacity: 0, scaleX: 0.6, transformOrigin: "left center" });
      gsap.set(".gtm-milestone", { opacity: 0, scale: 0 });
      gsap.timeline({ defaults: { ease: "power2.out" } })
        .to(".gtm-item", { opacity: 1, y: 0, stagger: 0.07, duration: 0.55 }, 0.15)
        .to(".gtm-bar", { opacity: 1, scaleX: 1, stagger: { each: 0.05, from: "start" }, duration: 0.55, ease: "power2.out" }, 0.5)
        .to(".gtm-milestone", { opacity: 1, scale: 1, stagger: 0.08, duration: 0.4, ease: "back.out(1.4)" }, 0.9);
    }, ref);
    return () => ctx.revert();
  }, []);

  const phases = [
    { label: "Launch", sublabel: "Months 1 to 2", period: "Find the first pull", accent: "rgba(251,191,36,0.55)", dim: "rgba(251,191,36,0.08)" },
    { label: "Deepen", sublabel: "Months 3 to 6", period: "Make continuity habit-forming", accent: "rgba(140,183,255,0.55)", dim: "rgba(140,183,255,0.07)" },
    { label: "Scale", sublabel: "Months 7 to 12", period: "Turn retention into distribution", accent: "rgba(45,212,191,0.55)", dim: "rgba(45,212,191,0.08)" },
  ];

  // from/to are 1-indexed phase numbers
  const swimLanes = [
    {
      label: "User Impact",
      accent: "#f59e0b",
      rows: [
        {
          name: "User Impact",
          dot: "#f59e0b",
          bars: [
            { from: 1, to: 1, label: "The first experience feels different.\nThey feel understood across sessions. The conversation does not reset.", theme: "amber" },
            { from: 2, to: 2, label: "A thread becomes personally useful.\nClarity builds. Decisions get easier. They return because it helps.", theme: "blue" },
            { from: 3, to: 3, label: "Their life becomes more visible over time.\nPatterns, change, and progress become tangible. This is when retention, referral, and payment kick in.", theme: "green" },
          ],
        },
      ],
    },
    {
      label: "Product",
      accent: "#a78bfa",
      rows: [
        {
          name: "Product",
          dot: "#a78bfa",
          bars: [
            { from: 1, to: 1, label: "Make return feel magical.\nWhen users come back, Sakhi remembers what matters and picks up the thread without friction.", theme: "amber" },
            { from: 2, to: 2, label: "Continuity becomes the product.\nSakhi connects moments into patterns. Each return builds on the last. The model of the person deepens.", theme: "blue" },
            { from: 3, to: 3, label: "The model expands beyond conversation.\nCalendar, communication, and behavioral signal enrich the thread. Context becomes ambient, not manual.", theme: "green" },
          ],
        },
      ],
    },
    {
      label: "Distribution",
      accent: "#8cb7ff",
      rows: [
        {
          name: "Distribution",
          dot: "#8cb7ff",
          bars: [
            { from: 1, to: 1, label: "Start with 25–50 founders and operators already carrying unresolved decisions across weeks.\nHigh-touch onboarding through warm intros, founder/operator communities, and direct outreach.", theme: "amber" },
            { from: 2, to: 2, label: "Turn insight into word of mouth.\nSeed trusted communities. Launch only once the \"this is different\" moment is repeatable.", theme: "blue" },
            { from: 3, to: 3, label: "Scale what already retains.\nAdd creator partnerships, referrals, and paid once continuity already sticks.", theme: "green" },
          ],
        },
      ],
    },
  ];

  const milestones = [
    { col: 1, label: "50 users → strong pull", color: "rgba(255,255,255,0.55)" },
    { col: 2, label: "Retention becomes visible", color: "#8cb7ff" },
    { col: 3, label: "2,000+ paying", color: "#2dd4bf" },
  ];

  const barStyles = {
    amber:   { bg: "rgba(251,191,36,0.10)",   border: "rgba(251,191,36,0.28)",   text: "rgba(254,240,138,0.80)", glow: "0 0 14px rgba(251,191,36,0.10)" },
    blue:    { bg: "rgba(140,183,255,0.10)",  border: "rgba(140,183,255,0.25)",  text: "rgba(200,216,255,0.80)", glow: "0 0 14px rgba(140,183,255,0.10)" },
    green:   { bg: "rgba(45,212,191,0.08)",   border: "rgba(45,212,191,0.24)",   text: "rgba(153,246,228,0.8)", glow: "0 0 14px rgba(45,212,191,0.1)" },
    neutral: { bg: "rgba(255,255,255,0.04)",  border: "rgba(255,255,255,0.08)",  text: "rgba(255,255,255,0.38)", glow: "" },
    empty:   { bg: "transparent",             border: "transparent",             text: "transparent",             glow: "" },
  };

  return (
    <div ref={ref} className="slide-scroll-panel absolute inset-0 overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden px-5 pt-14 pb-20 sm:px-10 sm:pt-14 sm:pb-6 lg:px-14 lg:pt-12 lg:pb-8">
      <div className="mx-auto max-w-7xl space-y-6">

        {/* Header */}
        <div className="gtm-item">
          <div className={DECK_HEADER_BADGE_CLASS}>
            <span className="h-1.5 w-1.5 rounded-full bg-violet-400/70" />Go to Market
          </div>
          <h2 className={DECK_TITLE_CLASS}>Go-to-Market Motion</h2>
          <p className={DECK_SUBTITLE_CLASS}>
            Depth before scale. The right 50 users unlock the next 50,000.
          </p>
        </div>

        {/* Gantt */}
        <div className="gtm-item overflow-x-auto rounded-xl [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        <div className="min-w-[580px]">

          {/* Phase header row */}
          <div className="flex items-end pb-3">
            <div className="grid flex-1 grid-cols-3">
              {phases.map((p) => (
                <div key={p.label} className="relative px-3">
                  {/* Phase column tint */}
                  <div className="pointer-events-none absolute inset-x-1 -bottom-3 top-0 rounded-t-xl" style={{ background: p.dim }} />
                  {/* Tick */}
                  <div className="absolute left-0 top-0 h-2 w-px" style={{ background: p.accent }} />
                  <div className="relative">
                    <div className="text-[clamp(0.7rem,1vw,0.85rem)] font-bold uppercase tracking-[0.24em]" style={{ color: p.accent }}>{p.label}</div>
                    <div className="mt-1 text-[clamp(0.6rem,0.75vw,0.72rem)] font-semibold uppercase tracking-[0.14em] text-white/30">{p.sublabel}</div>
                    <div className="mt-0.5 text-[clamp(0.6rem,0.72vw,0.7rem)] text-white/35">{p.period}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Timeline spine */}
          <div className="flex items-center">
            <div className="relative flex-1">
              <div className="h-px bg-gradient-to-r from-white/[0.06] via-white/[0.12] to-white/[0.06]" />
              {/* Phase dividers */}
              <div className="pointer-events-none absolute inset-0 grid grid-cols-3">
                {phases.map((p, i) => (
                  <div key={i} className="relative">
                    <div className="absolute left-0 top-[-3px] h-[7px] w-px" style={{ background: p.accent, opacity: 0.6 }} />
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Track rows */}
          <div className="mt-3 space-y-3">
            {swimLanes.map((lane, laneIndex) => (
              <div key={lane.label} className="space-y-2.5">
                <div className="flex items-center gap-2">
                  <div className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: lane.accent, boxShadow: `0 0 8px ${lane.accent}80` }} />
                  <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-white/45">{lane.label}</div>
                </div>
                <div className="space-y-2.5">
                  {lane.rows.map((row) => (
                    <div key={row.name} className="flex items-stretch">
                      <div className="relative flex-1 pl-3">
                        <div className="pointer-events-none absolute inset-0 grid grid-cols-3">
                          {phases.map((p, pi) => (
                            <div key={pi} className="mx-0.5 rounded-lg" style={{ background: p.dim, opacity: 0.5 }} />
                          ))}
                        </div>
                        <div className="relative grid grid-cols-3 gap-1">
                          {row.bars.map((bar, bi) => {
                            const s = barStyles[bar.theme as keyof typeof barStyles];
                            return (
                              <div
                                key={bi}
                                className={`gtm-bar rounded-xl border px-3 py-2.5 ${bar.theme === "empty" ? "pointer-events-none" : ""}`}
                                style={{
                                  gridColumn: `${bar.from} / ${bar.to + 1}`,
                                  background: s.bg,
                                  borderColor: s.border,
                                  boxShadow: s.glow,
                                }}
                              >
                                {bar.label && <p className="whitespace-pre-line text-[0.82rem] leading-[1.55]" style={{ color: s.text }}>{bar.label}</p>}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
                {laneIndex < swimLanes.length - 1 && (
                  <div className="relative h-[7px] w-full">
                    <div className="absolute inset-x-0 top-1/2 h-px -translate-y-1/2 bg-gradient-to-r from-white/[0.06] via-white/[0.12] to-white/[0.06]" />
                    <div className="pointer-events-none absolute inset-0 grid grid-cols-3">
                      {phases.map((p, pi) => (
                        <div key={pi} className="relative">
                          <div className="absolute left-0 top-0 h-[7px] w-px" style={{ background: p.accent, opacity: 0.6 }} />
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Milestone row */}
          <div className="mt-4 flex">
            <div className="grid flex-1 grid-cols-3 gap-1">
              {milestones.map((m) => (
                <div key={m.col} className="gtm-milestone flex flex-col items-center gap-1.5 pt-1">
                  <div className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: m.color, boxShadow: `0 0 8px ${m.color}` }} />
                  <div className="text-center text-[9px] font-semibold leading-[1.3] tracking-[0.06em]" style={{ color: m.color }}>{m.label}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
        </div>

      </div>
    </div>
  );
}

// ── Cover slide ───────────────────────────────────────────────────────────────
function SlideCover({ onEnter, onWatchFounders: _onWatchFounders }: { onEnter: () => void; onWatchFounders?: () => void }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const ctx = gsap.context(() => {
      gsap.set([".cov-orb", ".cov-ring", ".cov-title", ".cov-tag", ".cov-cta"], { opacity: 0 });
      gsap.timeline({ defaults: { ease: "power2.out" } })
        .to(".cov-ring",  { opacity: 1, stagger: 0.15, duration: 1.0 }, 0.2)
        .to(".cov-orb",   { opacity: 1, scale: 1, duration: 0.8, ease: "back.out(1.2)" }, 0.3)
        .to(".cov-title", { opacity: 1, y: 0, duration: 0.7 }, 0.9)
        .to(".cov-tag",   { opacity: 1, y: 0, duration: 0.6 }, 1.2)
        .to(".cov-cta",   { opacity: 1, duration: 0.5 }, 1.7);
    }, ref);
    return () => ctx.revert();
  }, []);

  return (
    <div ref={ref} className="absolute inset-0 flex flex-col items-center justify-center">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_70%_60%_at_50%_46%,rgba(30,50,100,0.5),rgba(3,11,24,0.0)_68%)]" />

      {/* Orb */}
      <div className="relative mb-5 flex items-center justify-center">
        <div className="cov-ring absolute h-[min(420px,88vw)] w-[min(420px,88vw)] rounded-full border border-white/[0.04]" />
        <div className="cov-ring absolute h-[min(320px,67vw)] w-[min(320px,67vw)] rounded-full border border-white/[0.07]" />
        <div className="cov-ring absolute h-[min(236px,50vw)] w-[min(236px,50vw)] rounded-full border border-white/[0.10]" />
        <div className="cov-orb relative flex h-[min(168px,36vw)] w-[min(168px,36vw)] items-center justify-center rounded-full border border-[#8ab0ff]/25 bg-[radial-gradient(circle_at_38%_32%,rgba(140,183,255,0.22),rgba(80,120,210,0.14)_48%,rgba(3,11,24,0.85)_78%)] shadow-[0_0_80px_rgba(100,148,255,0.18),0_0_160px_rgba(80,120,255,0.08)] animate-[sakhi-pulse_3s_ease-in-out_infinite]" style={{ opacity: 0, scale: "0.85" }}>
          <div className="pointer-events-none absolute inset-[14%] rounded-full border border-white/[0.09]" />
          <span className="relative z-10 text-[12px] font-semibold tracking-[0.42em] text-[#8ab0ff]/90">SAKHI</span>
        </div>
      </div>

      {/* Text */}
      <div className="relative z-10 flex flex-col items-center gap-2 text-center">
        <p className="cov-title text-[clamp(1.3rem,2.2vw,2rem)] font-semibold leading-none tracking-[-0.03em] text-white/35" style={{ opacity: 0, transform: "translateY(12px)" }}>
          Stop Reacting.
        </p>
        <h1 className="cov-tag text-[clamp(2rem,4vw,3.6rem)] font-bold leading-[1.05] tracking-[-0.06em] text-white" style={{ opacity: 0, transform: "translateY(10px)" }}>
          Start Shaping.
        </h1>
      </div>

      {/* CTAs */}
      <div className="cov-cta relative z-10 mt-10 flex items-center gap-7" style={{ opacity: 0 }}>
        <button
          type="button"
          onClick={onEnter}
          className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.3em] text-white/65 transition hover:text-white"
        >
          View Company Deck
          <svg viewBox="0 0 24 24" className="h-3 w-3 fill-none stroke-current" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 6l6 6-6 6" />
          </svg>
        </button>
      </div>
    </div>
  );
}

// ── Slide router ──────────────────────────────────────────────────────────────
// ── Slide 10 — The Beginning (closing) ───────────────────────────────────────
function Slide10Beginning() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const ctx = gsap.context(() => {
      gsap.set(".cd-end-item", { opacity: 0, y: 18 });
      gsap.timeline({ defaults: { ease: "power2.out" } })
        .to(".cd-end-item", { opacity: 1, y: 0, stagger: 0.12, duration: 0.7 }, 0.2);
    }, ref);
    return () => ctx.revert();
  }, []);

  return (
    <div ref={ref} className="absolute inset-0 flex flex-col items-center justify-center px-8 pt-14 pb-8 text-center">
      <div className="mx-auto w-full max-w-3xl">
        <div className="cd-end-item">
          <h2
            className="font-bold leading-[1.05] tracking-[-0.06em] text-white"
            style={{ fontSize: "clamp(3.5rem,8vw,6.5rem)" }}
          >
            This is just<br />the beginning.
          </h2>
        </div>

        <div className="cd-end-item mt-5">
          <p className="text-[clamp(1rem,1.4vw,1.2rem)] leading-relaxed text-white/45">
            If this resonates, let&apos;s build the continuity layer together.
          </p>
        </div>

        <div className="cd-end-item mt-12 flex flex-col gap-4 sm:flex-row">
          <div className="flex-1 rounded-[28px] border border-white/10 bg-white/[0.04] px-7 py-7 text-left">
            <p className="text-[9px] font-semibold uppercase tracking-[0.28em] text-[#8cb7ff]/65">Collaborate</p>
            <p className="mt-4 text-[0.9rem] leading-relaxed text-white/55">
              If you believe the inner life deserves real infrastructure, come build this with us.
            </p>
          </div>
          <div className="flex-1 rounded-[28px] border border-white/10 bg-white/[0.04] px-7 py-7 text-left">
            <p className="text-[9px] font-semibold uppercase tracking-[0.28em] text-[#8cb7ff]/65">Invest</p>
            <p className="mt-4 text-[0.9rem] leading-relaxed text-white/55">
              For investors who see continuity as the next consumer AI layer, let&apos;s talk.
            </p>
          </div>
        </div>

        <div className="cd-end-item mt-10">
          <p className="text-[9px] font-semibold uppercase tracking-[0.28em] text-white/28">
            For Collaboration or Investment
          </p>
          <a
            href="mailto:sakhiadmin@gmail.com"
            className="mt-3 inline-flex items-center gap-2 text-[1.1rem] font-medium text-white/75 transition-colors hover:text-white"
          >
            sakhiadmin@gmail.com
            <svg viewBox="0 0 20 20" fill="none" className="h-4 w-4 opacity-50" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 15.5l11-11m0 0H7.5m8 0v8" />
            </svg>
          </a>
        </div>

        <div className="cd-end-item mt-8">
          <p className="text-[10px] uppercase tracking-widest text-white/18">Sakhi · 2026</p>
        </div>
      </div>
    </div>
  );
}

const SLIDE_LABELS = [
  "Three Moments",
  "Problem + Solution",
  "How Sakhi Solves It",
  "Why Now",
  "Why It Doesn't Exist",
  "Why We Win",
  "Revenue",
  "The Ask",
  "Go to Market",
  "Founders",
  "The Long Game",
  "The Beginning",
];

function renderSlide(step: number, onEnter: () => void, onWatchStory?: () => void, onWatchFounders?: () => void) {
  switch (step) {
    case 0: return <SlideCover onEnter={onEnter} onWatchFounders={onWatchFounders} />;
    case 1: return <SlideStories />;
    case 2: return <Slide01ProblemSolution />;
    case 3: return <Slide02HowItSolves onWatchStory={onWatchStory} />;
    case 4: return <Slide02Market />;
    case 5: return <Slide03Gap />;
    case 6: return <Slide04WhyWeWin />;
    case 7: return <Slide04Revenue />;
    case 8: return <Slide05Ask />;
    case 9: return <SlideGTM />;
    case 10: return <Slide06FoundersCompact />;
    case 11: return <Slide02LongGame />;
    case 12: return <Slide10Beginning />;
    default: return null;
  }
}

// ── Main deck ─────────────────────────────────────────────────────────────────
export function CompanyDeckV1() {
  const [step, setStep] = useState(COVER);
  const [transitioning, setTransitioning] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [storyOpen, setStoryOpen] = useState(false);
  const [showBackToDeck, setShowBackToDeck] = useState(false);
  const backToDeckTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);

  const openStory = useCallback(() => {
    setStoryOpen(true);
    setShowBackToDeck(false);
    backToDeckTimerRef.current = setTimeout(() => setShowBackToDeck(true), 5000);
  }, []);

  const closeStory = useCallback(() => {
    setStoryOpen(false);
    setShowBackToDeck(false);
    if (backToDeckTimerRef.current) clearTimeout(backToDeckTimerRef.current);
  }, []);

  useEffect(() => {
    return () => {
      if (backToDeckTimerRef.current) clearTimeout(backToDeckTimerRef.current);
    };
  }, []);

  const goTo = useCallback((next: number) => {
    if (transitioning || next < COVER || next > TOTAL) return;
    setTransitioning(true);
    gsap.to(contentRef.current, {
      opacity: 0, duration: 0.2, ease: "power1.in",
      onComplete: () => {
        setStep(next);
        setTransitioning(false);
        gsap.fromTo(contentRef.current, { opacity: 0 }, { opacity: 1, duration: 0.28, ease: "power1.out" });
      },
    });
  }, [transitioning]);

  const navigate = useCallback((dir: 1 | -1) => goTo(step + dir), [step, goTo]);

  const toggleFullscreen = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    if (!document.fullscreenElement) el.requestFullscreen().catch(() => {});
    else document.exitFullscreen().catch(() => {});
  }, []);

  useEffect(() => {
    const onChange = () => setIsFullscreen(Boolean(document.fullscreenElement));
    document.addEventListener("fullscreenchange", onChange);
    return () => document.removeEventListener("fullscreenchange", onChange);
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "f" || e.key === "F") { toggleFullscreen(); return; }
      // Only navigate on vertical arrows if the active slide is not mid-scroll
      const panel = contentRef.current?.querySelector<HTMLElement>(".slide-scroll-panel");
      const atBottom = panel ? panel.scrollTop + panel.clientHeight >= panel.scrollHeight - 4 : true;
      const atTop = panel ? panel.scrollTop <= 4 : true;
      if (e.key === "ArrowRight" || e.key === " " || (e.key === "ArrowDown" && atBottom)) { e.preventDefault(); navigate(1); }
      if (e.key === "ArrowLeft"  || (e.key === "ArrowUp" && atTop))                        { e.preventDefault(); navigate(-1); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [navigate, toggleFullscreen]);

  return (
    <div ref={containerRef} className="fixed inset-0 overflow-hidden bg-[#020617] text-white">
      {/* Slide content */}
      <div ref={contentRef} className="absolute inset-0">
        {renderSlide(step, () => goTo(1), openStory, () => window.open("https://youtu.be/Zxa3yQA-jTU", "_blank"))}
      </div>

      {/* Top bar */}
      <div className="absolute inset-x-0 top-0 z-20 flex items-center justify-between px-5 py-3 sm:px-7">
        {/* Logo + slide label */}
        <div className="flex items-center gap-3">
          <button type="button" onClick={() => goTo(0)} className="text-[11px] font-semibold tracking-[0.38em] text-[#8ab0ff]/70 transition hover:text-[#8ab0ff]">SAKHI</button>
          {step > 0 && (
            <>
              <span className="text-white/20">/</span>
              <span className="text-[11px] font-medium tracking-[0.06em] text-white/55">{SLIDE_LABELS[step - 1]}</span>
            </>
          )}
        </div>
        {/* Controls */}
        <div className="flex items-center gap-2">
          {step > 0 && (
            <div className="px-2 text-[11px] font-medium tracking-[0.22em] text-white/30">
              {step} / {TOTAL}
            </div>
          )}
          <button
            type="button"
            onClick={toggleFullscreen}
            aria-label={isFullscreen ? "Exit fullscreen" : "Enter fullscreen"}
            className="flex h-8 w-8 items-center justify-center rounded-full border border-white/10 text-white/35 transition hover:border-white/20 hover:text-white/75"
          >
            {isFullscreen ? (
              <svg viewBox="0 0 24 24" className="h-3.5 w-3.5 fill-none stroke-current" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M8 3v3a2 2 0 0 1-2 2H3M21 8h-3a2 2 0 0 1-2-2V3M3 16h3a2 2 0 0 1 2 2v3M16 21v-3a2 2 0 0 1 2-2h3" />
              </svg>
            ) : (
              <svg viewBox="0 0 24 24" className="h-3.5 w-3.5 fill-none stroke-current" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M8 3H5a2 2 0 0 0-2 2v3M21 8V5a2 2 0 0 0-2-2h-3M3 16v3a2 2 0 0 0 2 2h3M16 21h3a2 2 0 0 0 2-2v-3" />
              </svg>
            )}
          </button>
        </div>
      </div>

      {/* Right-side dot nav — hidden on cover */}
      {step > 0 && (
        <nav className="absolute right-4 top-1/2 z-20 hidden -translate-y-1/2 flex-col gap-3 md:flex sm:right-5">
          {Array.from({ length: TOTAL }).map((_, i) => (
            <button
              key={i}
              type="button"
              onClick={() => goTo(i + 1)}
              aria-label={`Go to slide ${i + 1}`}
              className={`h-2.5 w-2.5 rounded-full transition-all duration-300 ${
                i + 1 === step ? "scale-125 bg-white opacity-100" : "bg-white opacity-25 hover:opacity-50"
              }`}
            />
          ))}
        </nav>
      )}

      {/* Prev */}
      {step > COVER && (
        <button
          type="button"
          onClick={() => navigate(-1)}
          disabled={transitioning}
          aria-label="Previous slide"
          className="absolute bottom-6 left-5 z-20 flex h-12 w-12 items-center justify-center rounded-full border border-white/12 bg-[#020617]/76 text-white/78 shadow-[0_18px_40px_rgba(0,0,0,0.28)] backdrop-blur-md transition hover:border-white/22 hover:text-white sm:bottom-8 sm:left-7"
        >
          <svg viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M15 18l-6-6 6-6" />
          </svg>
        </button>
      )}

      {/* Next */}
      {step > COVER && step < TOTAL && (
        <button
          type="button"
          onClick={() => navigate(1)}
          disabled={transitioning}
          aria-label="Next slide"
          className="absolute bottom-6 right-5 z-20 flex h-12 w-12 items-center justify-center rounded-full border border-white/12 bg-[#020617]/76 text-white/78 shadow-[0_18px_40px_rgba(0,0,0,0.28)] backdrop-blur-md transition hover:border-white/22 hover:text-white sm:bottom-8 sm:right-7"
        >
          <svg viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 6l6 6-6 6" />
          </svg>
        </button>
      )}

      {/* Story overlay */}
      {storyOpen && (
        <div className="absolute inset-0 z-50">
          <StoryContainer autoPlay />
          <div
            className={`absolute bottom-[4.8rem] right-6 z-[100] transition-all duration-500 sm:bottom-[5.2rem] sm:right-8 ${
              showBackToDeck ? "pointer-events-auto opacity-100" : "pointer-events-none opacity-0"
            }`}
          >
            <button
              type="button"
              onClick={closeStory}
              className="flex items-center gap-2 rounded-full border border-white/10 bg-black/30 px-5 py-2.5 text-[12px] font-medium text-white/45 backdrop-blur-md transition hover:border-white/18 hover:text-white/75"
            >
              Back to deck
              <svg viewBox="0 0 24 24" className="h-3.5 w-3.5 fill-none stroke-current" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                <path d="M6 9l6 6 6-6" />
              </svg>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
