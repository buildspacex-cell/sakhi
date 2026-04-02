"use client";

import Image from "next/image";
import { useCallback, useEffect, useRef, useState } from "react";
import gsap from "gsap";

const TOTAL = 8;
const COVER = 0;
const DECK_HEADER_BADGE_CLASS =
  "mb-4 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 text-[10px] font-semibold uppercase tracking-[0.3em] text-white/40";
const DECK_TITLE_CLASS =
  "text-[clamp(1.8rem,3vw,2.8rem)] font-bold leading-[1.05] tracking-[-0.05em] text-white";
const DECK_SUBTITLE_CLASS =
  "mt-3 max-w-4xl text-[clamp(0.88rem,1.1vw,1rem)] leading-[1.65] text-slate-400";

// ── Slide 1 — Problem + Solution ─────────────────────────────────────────────
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

  const rows = [
    { physical: "Mapped",  physicalDetail: "GPS, roads, infrastructure",       inner: "Adrift", innerDetail: "6,200 thoughts a day. No map. No compass. No center." },
    { physical: "Managed", physicalDetail: "Calendars, schedules, commitments", inner: "Fragmented", innerDetail: "Jumping priorities, chasing the urgent. No thread holds." },
    { physical: "Tracked", physicalDetail: "Steps, sleep, spending",            inner: "Invisible",  innerDetail: "Patterns never surface. The person you're becoming stays hidden." },
  ];

  return (
    <div ref={ref} className="slide-scroll-panel absolute inset-0 overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden flex flex-col px-10 py-10 pb-24 sm:px-16 lg:px-20">
      <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-5">

        {/* Hook */}
        <div className="cd1-item shrink-0">
          <h2 className={DECK_TITLE_CLASS}>
            6,200 thoughts a day.<sup className="text-[0.5em] align-super text-white/30">1</sup>{" "}
            <span className="text-white/40">Most scattered, forgotten.</span>
          </h2>
          <p className={DECK_SUBTITLE_CLASS}>
            We built infrastructure for everything except the mind.
          </p>
        </div>

        {/* Gap — aligned rows */}
        <div className="cd1-item shrink-0 overflow-hidden rounded-2xl border border-white/[0.07]">
          {/* Column headers */}
          <div className="grid grid-cols-[1fr_1px_1fr]">
            <div className="bg-emerald-950/20 px-6 py-3">
              <span className="text-[9px] font-semibold uppercase tracking-[0.35em] text-emerald-400/60">The Physical World</span>
            </div>
            <div className="bg-white/[0.06]" />
            <div className="bg-rose-950/20 px-6 py-3">
              <span className="text-[9px] font-semibold uppercase tracking-[0.35em] text-rose-400/50">The Inner Life</span>
            </div>
          </div>
          <div className="h-px bg-white/[0.06]" />

          {/* Rows */}
          {rows.map((r, i) => (
            <div key={r.physical}>
              <div className="grid grid-cols-[1fr_1px_1fr]">
                <div className={`flex items-center gap-3 px-6 py-3.5 ${i % 2 === 0 ? "" : "bg-white/[0.015]"}`}>
                  <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-400/40" />
                  <span className="text-[0.85rem] font-semibold text-white/65">{r.physical}</span>
                  <span className="text-[0.82rem] text-slate-500">{r.physicalDetail}</span>
                </div>
                <div className="bg-white/[0.06]" />
                <div className={`flex items-center gap-3 px-6 py-3.5 ${i % 2 === 0 ? "" : "bg-white/[0.015]"}`}>
                  <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-rose-400/40" />
                  <span className="text-[0.85rem] font-semibold text-white/65">{r.inner}</span>
                  <span className="text-[0.82rem] text-slate-500">{r.innerDetail}</span>
                </div>
              </div>
              <div className="h-px bg-white/[0.04]" />
            </div>
          ))}

          {/* Result row */}
          <div className="grid grid-cols-[1fr_1px_1fr]">
            <div className="bg-emerald-950/25 px-6 py-3.5">
              <span className="text-[0.82rem] font-semibold text-emerald-300/60">Result: Order, compounding progress, and a clear record of what changed.</span>
            </div>
            <div className="bg-white/[0.06]" />
            <div className="bg-rose-950/25 px-6 py-3.5">
              <span className="text-[0.82rem] font-semibold text-rose-300/60">Result: You feel busy. You move fast. You arrive nowhere.</span>
            </div>
          </div>
        </div>

        {/* Solution — bridge flows into headline */}
        <div className="cd1-item rounded-2xl border border-[#8cb7ff]/15 bg-[#8cb7ff]/[0.05] px-6 py-6">
          <div className="mb-4 text-[9px] font-semibold uppercase tracking-[0.3em] text-[#8cb7ff]/55">Solution</div>

          {/* Bridge as intro */}
          <p className="mb-5 text-[clamp(0.82rem,1vw,0.95rem)] leading-[1.75] text-slate-500">
            You started tracking your steps. Your health improved, not because you wrote the numbers down, but because you finally saw the pattern.{" "}
            <span className="text-white">Sakhi does that for your mind. A mirror that compounds. Letting you stop reacting to life and start shaping it.</span>
          </p>

          <div className="border-t border-[#8cb7ff]/10 pt-5">
            <h3 className="text-[clamp(1rem,1.5vw,1.25rem)] font-bold leading-[1.25] tracking-[-0.03em] text-white">
              The first AI that builds a living model of you.
            </h3>
            <ul className="mt-4 grid gap-2.5 sm:grid-cols-3">
              {[
                "Remembers what you said, what you meant, and what you're becoming.",
                "Not a chatbot. Not a journal. A Life Intelligence that compounds over time.",
                "Every conversation makes it more accurate. Every reflection more useful.",
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
          <sup>1</sup> Tseng & Poppenk. <em>Nature Communications</em>, 2020. doi:10.1038/s41467-020-17255-9
        </div>

      </div>
    </div>
  );
}

// ── Slide 2 — The Long Game ───────────────────────────────────────────────────
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
    { label: "Today", heading: "Your thinking partner", body: "Talk to Sakhi. It remembers everything: what you said, what you meant, what you keep returning to. Every conversation builds a clearer picture of who you are." },
    { label: "Tomorrow", heading: "Your personal context layer", body: "Sakhi becomes the lens through which you interact with every AI. It carries your values, your priorities, your history. Every tool you touch already knows you." },
    { label: "The vision", heading: "From self to the world", body: "Every AI lab is racing to be your interface. Sakhi starts from the other direction, from inside your mind, outward. That inversion is the moat no frontier lab is building." },
  ];

  return (
    <div ref={ref} className="absolute inset-0 flex flex-col px-10 py-12 sm:px-16 lg:px-20">
      <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-8">

        <div className="cd-lg-item shrink-0">
          <div className={DECK_HEADER_BADGE_CLASS}>
            <span className="h-1.5 w-1.5 rounded-full bg-[#8cb7ff]/70" />The Long Game
          </div>
          <h2 className={DECK_TITLE_CLASS}>
            <span className="text-white/35">Every LLM wants to be your interface.</span><br />
            Sakhi becomes your thinking layer.
          </h2>
        </div>

        <div className="cd-lg-item grid flex-1 gap-5 lg:grid-cols-3">
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
              <p className="mt-3 flex-1 text-[0.83rem] leading-[1.65] text-slate-400">{p.body}</p>
              {i === 2 && (
                <p className="mt-5 text-[0.78rem] font-semibold tracking-[-0.01em] text-[#8cb7ff]/60">
                  Not one AI among many. The one that knows you well enough to decide which AI you need.
                </p>
              )}
            </div>
          ))}
        </div>

        <div className="cd-lg-item shrink-0 rounded-2xl border border-[#8cb7ff]/10 bg-[#8cb7ff]/[0.03] px-6 py-4">
          <p className="text-[clamp(0.88rem,1.05vw,1rem)] leading-[1.65] text-slate-400">
            The physical world got GPS, hospitals, financial rails.{" "}
            <span className="text-white/60">The inner world gets Sakhi: the infrastructure layer for the continuity of a human mind.</span>
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
    { label: "TAM", size: "500M+", detail: "Knowledge workers, caregivers & professionals with complex mental load", market: "$80B by 2030²" },
    { label: "SAM", size: "80M", detail: "English-speaking professionals & caregivers, 25–55, already paying for productivity software", market: "$9.6B³" },
    { label: "SOM", size: "100K", detail: "Target users in 18 months. 10K paying at $20/mo = $2.4M ARR before Seed", market: "$2.4M ARR" },
  ];

  const comps = [
    { name: "Notion", signal: "$10B valuation on personal + team knowledge⁴" },
    { name: "Day One", signal: "Acquired by Automattic; journaling alone had exit value⁵" },
    { name: "Rewind", signal: "$75M raised on passive desktop recall alone⁶" },
    { name: "Replika", signal: "10M+ users seeking connection, but it forgets. It doesn't build a model of you.⁷" },
  ];

  return (
    <div ref={ref} className="absolute inset-0 overflow-y-auto px-10 py-12 sm:px-16 lg:px-20">
      <div className="mx-auto max-w-6xl space-y-7">
        <div className="cd2-item">
          <div className={DECK_HEADER_BADGE_CLASS}>
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400/70" />Market Opportunity
          </div>
          <h2 className={DECK_TITLE_CLASS}>
            The number isn&apos;t the story. The timing is.
          </h2>
          <p className={DECK_SUBTITLE_CLASS}>
            LLMs just became capable enough to hold context at depth. People are willing to talk to an AI in ways they never were before. And they are overwhelmed enough to pay for relief. That window didn&apos;t exist three years ago. Nobody has walked through it yet.
          </p>
        </div>

        {/* TAM / SAM / SOM */}
        <div className="cd2-item grid gap-4 sm:grid-cols-3">
          {tam.map((t) => (
            <div key={t.label} className="rounded-2xl border border-white/[0.08] bg-white/[0.03] px-5 py-6">
              <div className="text-[9px] font-semibold uppercase tracking-[0.3em] text-emerald-400/70">{t.label}</div>
              <div className="mt-2 text-[clamp(2.4rem,4vw,3.6rem)] font-bold leading-none tracking-[-0.06em] text-white">{t.size}</div>
              <p className="mt-3 text-[clamp(0.82rem,1vw,0.95rem)] leading-[1.55] text-slate-400">{t.detail}</p>
              <div className="mt-4 text-[9px] font-semibold uppercase tracking-[0.22em] text-emerald-400/60">{t.market}</div>
            </div>
          ))}
        </div>

        {/* Comparable signals */}
        <div className="cd2-item">
          <div className="mb-3 text-[9px] font-semibold uppercase tracking-[0.3em] text-white/30">Comparable signals</div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {comps.map((c) => (
              <div key={c.name} className="rounded-xl border border-white/[0.07] bg-white/[0.02] px-4 py-3.5">
                <div className="text-[0.85rem] font-semibold tracking-[-0.02em] text-white/80">{c.name}</div>
                <p className="mt-1.5 text-[0.75rem] leading-[1.5] text-slate-500">{c.signal}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="cd2-item rounded-2xl border border-emerald-400/12 bg-emerald-400/[0.04] px-5 py-4">
          <p className="text-[clamp(0.88rem,1.05vw,1rem)] leading-[1.65] text-emerald-200/70">
            Nobody owns the continuity layer. That&apos;s the gap. The gap is the company.
          </p>
        </div>

        <div className="cd2-item border-t border-white/[0.05] pt-4 text-[0.7rem] leading-[1.6] text-white/22">
          <p><sup>2</sup> Combined TAM: Precedence Research, <em>Mental Health Apps Market</em>, 2023; Grand View Research, <em>Productivity Management Software Market</em>, 2023. &nbsp;<sup>3</sup> Internal estimate (Statista, <em>SaaS User Demographics</em>, 2023).</p>
          <p><sup>4</sup> Notion Series C at $10B valuation, Oct 2021 (The Information). &nbsp;<sup>5</sup> Automattic acquisition of Day One, 2021. &nbsp;<sup>6</sup> Rewind AI funding rounds, TechCrunch, 2022–2023. &nbsp;<sup>7</sup> Replika public user count, Luka Inc. press, 2023.</p>
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
    { category: "Personal AI",     name: "Dot / Kin / Personal.ai",     does: "Stores your life context",    misses: "Retrieval, not inference. An archive, not a model of who you're becoming." },
  ];

  return (
    <div ref={ref} className="slide-scroll-panel absolute inset-0 overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden px-10 py-12 pb-24 sm:px-14 lg:px-16">
      <div className="mx-auto flex max-w-7xl flex-col gap-4">

        <div className="cd3-item shrink-0">
          <div className={DECK_HEADER_BADGE_CLASS}>
            <span className="h-1.5 w-1.5 rounded-full bg-amber-400/70" />Why It Doesn&apos;t Exist
          </div>
          <h2 className={DECK_TITLE_CLASS}>
            Everyone stores. Nobody remembers.
          </h2>
        </div>

        {/* Column labels — same row, aligned above their panels */}
        <div className="cd3-item grid shrink-0 gap-4 lg:grid-cols-2">
          <div className="text-[9px] font-semibold uppercase tracking-[0.3em] text-white/30">Landscape</div>
          <div className="text-[9px] font-semibold uppercase tracking-[0.3em] text-white/30">Capability map</div>
        </div>

        {/* Two-column layout */}
        <div className="cd3-item grid gap-4 lg:grid-cols-2">

          {/* Left — table */}
          <div className="rounded-xl border border-white/[0.08]">
            <table className="w-full text-left text-[0.7rem]">
              <thead>
                <tr className="border-b border-white/[0.07] bg-white/[0.03]">
                  <th className="px-3 py-1.5 text-[7px] font-semibold uppercase tracking-[0.22em] text-white/25">Company</th>
                  <th className="px-3 py-1.5 text-[7px] font-semibold uppercase tracking-[0.22em] text-white/25">What it does</th>
                  <th className="px-3 py-1.5 text-[7px] font-semibold uppercase tracking-[0.22em] text-amber-400/50">What it misses</th>
                </tr>
              </thead>
              <tbody>
                {competitors.map((c, i) => (
                  <tr key={c.name} className={`border-b border-white/[0.05] ${i % 2 === 0 ? "" : "bg-white/[0.015]"}`}>
                    <td className="px-3 py-1.5">
                      <div className="text-[0.72rem] font-semibold text-white">{c.name}</div>
                      <div className="text-[0.65rem] text-slate-500">{c.category}</div>
                    </td>
                    <td className="px-3 py-1.5 text-[0.72rem] text-slate-400">{c.does}</td>
                    <td className="px-3 py-1.5 text-[0.72rem] text-amber-200/60">{c.misses}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Right — capability matrix */}
          <div className="relative overflow-hidden rounded-xl border border-white/[0.08] bg-white/[0.02] min-h-[420px]">
              {/* Axis labels */}
              <div className="absolute left-1/2 top-2.5 -translate-x-1/2 text-[7px] font-semibold uppercase tracking-[0.25em] text-white/14">Understands your life</div>
              <div className="absolute bottom-2.5 left-1/2 -translate-x-1/2 text-[7px] font-semibold uppercase tracking-[0.25em] text-white/65">Surface-level only</div>
              <div className="absolute left-2 top-[53%] text-[7px] font-semibold uppercase tracking-[0.2em] text-white/65">Forgets you</div>
              <div className="absolute right-2 top-[53%] text-right text-[7px] font-semibold uppercase tracking-[0.2em] text-white/14">Remembers &amp; compounds</div>
              {/* Axis lines */}
              <div className="absolute inset-x-8 top-1/2 h-px bg-white/[0.06]" />
              <div className="absolute inset-y-8 left-1/2 w-px bg-white/[0.06]" />
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
            </div>

        </div>

        {/* Qualification statement */}
        <div className="cd3-item shrink-0 rounded-xl border border-[#8cb7ff]/10 bg-[#8cb7ff]/[0.03] px-5 py-3.5">
          <p className="text-[0.78rem] leading-[1.65] text-slate-400">
            Replika, Pi, Dot, Kin, and Personal.ai are building toward the top-right.{" "}
            <span className="text-white/70">All five retrieve. Sakhi infers.</span>{" "}
            The difference: an archive of what you said versus a compounding model of who you are becoming.
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
    { label: "Continuity Engine", tag: "Core infrastructure", body: "Memory that persists, connects, and surfaces across sessions. Not a feature. The infrastructure layer no competitor has built." },
    { label: "Personalization Flywheel", tag: "Data moat", body: "Every conversation sharpens the model. The system compounds private context instead of starting from zero each session." },
    { label: "Life Occupancy", tag: "Visible in product", body: "The app already maps what has actually occupied your life across time. This is not conceptual deckware." },
    { label: "Continuity Arc", tag: "Visible in product", body: "The app already turns moments into an explorable story arc, so users can revisit how a thread evolved." },
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
    <div ref={ref} className="slide-scroll-panel absolute inset-0 overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden flex flex-col justify-start px-10 py-12 pb-24 sm:px-14 lg:px-18">
      <div className="mx-auto w-full max-w-7xl">
        <div className="cd4w-header mx-auto mb-7 w-full max-w-6xl">
          <div className={DECK_HEADER_BADGE_CLASS}>
            <span className="h-1.5 w-1.5 rounded-full bg-[#8cb7ff]/70" />Why We Win
          </div>
          <h2 className={DECK_TITLE_CLASS}>
            The model is the moat.
          </h2>
          <p className={DECK_SUBTITLE_CLASS}>
            Not the interface. Not the features. The compounding intelligence that builds inside Sakhi and lives nowhere else.
          </p>
        </div>

        <div className="mx-auto grid max-w-6xl items-center gap-8 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)] lg:gap-10">
          <div className="grid gap-3 sm:grid-cols-2">
            {moat.map((m) => (
              <div key={m.label} className="cd4w-card rounded-2xl border border-[#8cb7ff]/10 bg-[#8cb7ff]/[0.04] px-5 py-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]">
                <div className="text-[0.92rem] font-bold tracking-[-0.02em] text-white">{m.label}</div>
                <div className="mt-1 text-[8px] font-semibold uppercase tracking-[0.22em] text-[#8cb7ff]/40">{m.tag}</div>
                <p className="mt-3 text-[0.81rem] leading-[1.65] text-slate-400">{m.body}</p>
              </div>
            ))}
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
    { name: "Free", price: "$0", color: "border-white/8 bg-white/[0.02]", tag: "Experience Sakhi", features: ["Start seeing your life more clearly", "Capture thoughts, decisions, and patterns", "30-day active memory window", "3 Deep Reflects/mo to experience the system", "Arc view (read only)"] },
    { name: "Pro", price: "$20/mo", color: "border-[#8cb7ff]/20 bg-[#8cb7ff]/[0.05]", tag: "Build your model", features: ["Annual plan: $180/yr. Commit to continuity.", "Your model builds and compounds over time", "Understand what's really going on across weeks, not moments", "See patterns, cycles, and decisions clearly", "Full Arc. Full history. Unlimited Deep Reflect."] },
    { name: "Collective", price: "$30/user/mo", color: "border-amber-400/12 bg-amber-400/[0.04]", tag: "Year 2, expansion", features: ["Shared intelligence across people who matter", "Each person builds their own model", "Shared context across relationships. Think together, not in fragments.", "Privacy-first by design"] },
  ];

  const trajectory = [
    { period: "Month 12", users: "2,000 paying", arr: "$480K ARR" },
    { period: "Month 18", users: "10,000 paying", arr: "$2.4M ARR" },
    { period: "Month 24", users: "50,000 paying", arr: "$12M ARR" },
  ];

  const unitEcon = [
    { label: "CAC target (organic-led)", value: "$8–12⁸" },
    { label: "ARPU", value: "$240/yr" },
    { label: "LTV:CAC (yr 1)", value: "20–30×" },
    { label: "Gross margin (Yr 2)", value: "50–65%⁸" },
  ];

  return (
    <div ref={ref} className="slide-scroll-panel absolute inset-0 overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden px-10 py-12 pb-24 sm:px-16 lg:px-20">
      <div className="mx-auto max-w-6xl">
        <div className="cd4-item mb-7">
          <div className={DECK_HEADER_BADGE_CLASS}>
            <span className="h-1.5 w-1.5 rounded-full bg-violet-400/70" />Revenue Model
          </div>
          <h2 className={DECK_TITLE_CLASS}>
            Simple. Subscription-first. No ads. No data selling.
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
        <p className="cd4-item mt-2 text-[0.75rem] text-slate-500">Your model is the asset. <span className="text-white/40">The longer you use Sakhi, the sharper it gets.</span></p>

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
            <p className="mt-1.5 text-[0.7rem] leading-[1.5] text-white/22"><sup>8</sup> CAC assumes organic-led growth. Gross margin assumes frontier model (GPT-4o / Claude Sonnet) for all substantive interactions; improves as inference costs decline and caching matures. See internal pricing assumptions doc.</p>
          </div>

          {/* Growth trajectory */}
          <div>
            <div className="mb-3 text-[9px] font-semibold uppercase tracking-[0.3em] text-white/30">Growth trajectory</div>
            <div className="space-y-2.5">
              {trajectory.map((t) => (
                <div key={t.period} className="flex items-center justify-between rounded-xl border border-white/[0.07] bg-white/[0.02] px-4 py-3">
                  <div className="text-[0.78rem] font-semibold text-white/50">{t.period}</div>
                  <div className="text-[0.78rem] text-slate-400">{t.users}</div>
                  <div className="text-[0.82rem] font-bold tracking-[-0.02em] text-emerald-300/80">{t.arr}</div>
                </div>
              ))}
            </div>
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
    "Continuity Engine V2: deeper memory, cross-session inference",
    "Life signal layer (HealthKit, calendar, email): the first version of Sakhi that knows what's happening in your life without you having to narrate it",
    "Mobile-first experience, polished for iOS and Android",
    "10,000 active users, 2,000+ paying",
    "60%+ Day-90 retention",
    "$40K MRR run rate",
  ];

  const allocation = [
    { pct: "20%", amount: "$254K", label: "Engineering", detail: "LLM API, infra, AI tools, design, QA, equipment, observability" },
    { pct: "14%", amount: "$171K", label: "GTM", detail: "First cohort, content, community, creator partnerships, paid experiments" },
    { pct: "28%", amount: "$350K", label: "People", detail: "CEO, CTO, AI/ML engineer, growth hire, India statutory" },
    { pct: "6%",  amount: "$75K",  label: "Legal + Compliance", detail: "C-Corp, India entity, IP, SAFE, GDPR, HealthKit" },
    { pct: "4%",  amount: "$50K",  label: "Operations", detail: "Payroll, accounting, tools, co-working" },
    { pct: "28%", amount: "$350K", label: "Runway + Buffer", detail: "8 months full team burn in reserve for Seed timing" },
  ];

  return (
    <div ref={ref} className="slide-scroll-panel absolute inset-0 overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden px-10 py-12 pb-24 sm:px-16 lg:px-20">
      <div className="mx-auto max-w-6xl">
        <div className="cd5-item mb-8 text-center">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3.5 py-1.5 text-[9px] font-semibold uppercase tracking-[0.3em] text-white/40">
            <span className="h-1.5 w-1.5 rounded-full bg-[#8cb7ff]/70" />Pre-Seed Round
          </div>
          <div className="text-[clamp(3.5rem,7vw,6rem)] font-bold leading-none tracking-[-0.07em] text-white">$1,250,000</div>
          <p className="mt-3 text-[clamp(0.95rem,1.3vw,1.2rem)] text-slate-400">
            Raising $1.25M to prove what we already believe:{" "}
            <span className="text-white/60">the world&apos;s most underbuilt infrastructure is the continuity of a human mind.</span>
          </p>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          {/* Milestones */}
          <div className="cd5-item">
            <div className="mb-3 text-[9px] font-semibold uppercase tracking-[0.3em] text-white/30">What we prove with this raise (Month 12)</div>
            <div className="space-y-2.5">
              {milestones.map((m, i) => (
                <div key={i} className="flex items-start gap-3 rounded-xl border border-white/[0.07] bg-white/[0.02] px-4 py-3">
                  <span className="mt-[0.3em] h-1.5 w-1.5 shrink-0 rounded-full bg-[#8cb7ff]/60" />
                  <p className="text-[clamp(0.82rem,1vw,0.95rem)] leading-[1.5] text-slate-300">{m}</p>
                </div>
              ))}
            </div>
            <div className="mt-4 rounded-xl border border-emerald-400/15 bg-emerald-400/[0.04] px-4 py-3 text-[0.82rem] font-semibold text-emerald-300/70">
              Seed target at Month 12–15: $4–5M at $15–20M valuation
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
                      <span className="text-[1.5rem] font-bold leading-none tracking-[-0.05em] text-white/88">{a.pct}</span>
                      <div>
                        <div className="text-[0.85rem] font-semibold text-white/70">{a.label}</div>
                        <div className="text-[0.75rem] text-slate-500">{a.detail}</div>
                      </div>
                    </div>
                    <div className="text-[0.9rem] font-bold tracking-[-0.03em] text-[#c8d8ff]/60">{a.amount}</div>
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
    name: "Vidhya",
    role: "Co-Founder & CEO",
    image: "/story/v-pic-20260327.png",
    imageStyle: {},
    bio: "Built systems for companies. Now building one for humans.",
    quote:
      "I've spent 20+ years helping organizations make better decisions. I realized we haven't solved this for individuals.",
    beats: [
      "Operator at Scale: turned ambiguity into structured decisions.",
      "Inflection Point: caregiving, leadership, and life complexity collided.",
      "Insight to Sakhi: personalization and timing mattered more than generic advice.",
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
      "Evolution: moved from engineering into product systems thinking.",
      "Realization: systems work only when people trust and use them.",
      "Convergence: technical depth plus human-behavior lens now builds Sakhi.",
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
    <div ref={ref} className="slide-scroll-panel absolute inset-0 overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden px-8 py-10 pb-24 sm:px-12 lg:px-16 xl:px-20">
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
                      <div key={beat} className="rounded-xl border border-white/[0.08] bg-white/[0.03] px-3.5 py-2.5 text-[0.78rem] leading-[1.5] text-slate-300">
                        {beat}
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

// ── Cover slide ───────────────────────────────────────────────────────────────
function SlideCover({ onEnter }: { onEnter: () => void }) {
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
        <div className="cov-ring absolute h-[420px] w-[420px] rounded-full border border-white/[0.04]" />
        <div className="cov-ring absolute h-[320px] w-[320px] rounded-full border border-white/[0.07]" />
        <div className="cov-ring absolute h-[236px] w-[236px] rounded-full border border-white/[0.10]" />
        <div className="cov-orb relative flex h-[168px] w-[168px] items-center justify-center rounded-full border border-[#8ab0ff]/25 bg-[radial-gradient(circle_at_38%_32%,rgba(140,183,255,0.22),rgba(80,120,210,0.14)_48%,rgba(3,11,24,0.85)_78%)] shadow-[0_0_80px_rgba(100,148,255,0.18),0_0_160px_rgba(80,120,255,0.08)]" style={{ opacity: 0, scale: "0.85" }}>
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

      {/* Enter cta */}
      <button
        type="button"
        onClick={onEnter}
        className="cov-cta absolute bottom-10 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.3em] text-white/25 transition hover:text-white/60"
        style={{ opacity: 0 }}
      >
        View deck
        <svg viewBox="0 0 24 24" className="h-3 w-3 fill-none stroke-current" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
          <path d="M9 6l6 6-6 6" />
        </svg>
      </button>
    </div>
  );
}

// ── Slide router ──────────────────────────────────────────────────────────────
const SLIDE_LABELS = [
  "Problem + Solution",
  "The Long Game",
  "Market",
  "Why It Doesn't Exist",
  "Why We Win",
  "Revenue",
  "The Ask",
  "Founders",
];

function renderSlide(step: number, onEnter: () => void) {
  switch (step) {
    case 0: return <SlideCover onEnter={onEnter} />;
    case 1: return <Slide01ProblemSolution />;
    case 2: return <Slide02LongGame />;
    case 3: return <Slide02Market />;
    case 4: return <Slide03Gap />;
    case 5: return <Slide04WhyWeWin />;
    case 6: return <Slide04Revenue />;
    case 7: return <Slide05Ask />;
    case 8: return <Slide06FoundersCompact />;
    default: return null;
  }
}

// ── Main deck ─────────────────────────────────────────────────────────────────
export function CompanyDeck() {
  const [step, setStep] = useState(COVER);
  const [transitioning, setTransitioning] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);

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
        {renderSlide(step, () => goTo(1))}
      </div>

      {/* Top bar */}
      <div className="absolute inset-x-0 top-0 z-20 flex items-center justify-between px-5 py-3 sm:px-7">
        {/* Logo + slide label */}
        <div className="flex items-center gap-3">
          <span className="text-[11px] font-semibold tracking-[0.38em] text-[#8ab0ff]/70">SAKHI</span>
          {step > 0 && (
            <>
              <span className="text-white/12">·</span>
              <span className="text-[11px] text-white/30">{SLIDE_LABELS[step - 1]}</span>
            </>
          )}
        </div>
        {/* Controls */}
        <div className="flex items-center gap-2">
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
      <button
        type="button"
        onClick={() => navigate(-1)}
        disabled={step === COVER || transitioning}
        aria-label="Previous slide"
        className={`absolute bottom-6 left-5 z-20 flex h-12 w-12 items-center justify-center rounded-full border backdrop-blur-md transition sm:bottom-8 sm:left-7 ${
          step === COVER
            ? "cursor-not-allowed border-white/8 bg-[#020617]/30 text-white/18"
            : "border-white/12 bg-[#020617]/76 text-white/78 shadow-[0_18px_40px_rgba(0,0,0,0.28)] hover:border-white/22 hover:text-white"
        }`}
      >
        <svg viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M15 18l-6-6 6-6" />
        </svg>
      </button>

      {/* Next */}
      <button
        type="button"
        onClick={() => navigate(1)}
        disabled={step === TOTAL || transitioning}
        aria-label="Next slide"
        className={`absolute bottom-6 right-5 z-20 flex h-12 w-12 items-center justify-center rounded-full border backdrop-blur-md transition sm:bottom-8 sm:right-7 ${
          step === TOTAL
            ? "cursor-not-allowed border-white/8 bg-[#020617]/30 text-white/18"
            : "border-white/12 bg-[#020617]/76 text-white/78 shadow-[0_18px_40px_rgba(0,0,0,0.28)] hover:border-white/22 hover:text-white"
        }`}
      >
        <svg viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M9 6l6 6-6 6" />
        </svg>
      </button>

      {/* Bottom step counter — hidden on cover */}
      {step > 0 && (
        <div className="absolute bottom-8 left-1/2 z-20 -translate-x-1/2 text-[11px] font-medium tracking-[0.22em] text-white/20">
          {step} / {TOTAL}
        </div>
      )}
    </div>
  );
}
