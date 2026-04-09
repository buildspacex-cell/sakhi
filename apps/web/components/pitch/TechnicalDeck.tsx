"use client";

import { useState } from "react";
import { FadeIn } from "@/components/pitch/FadeIn";

// ── Types ─────────────────────────────────────────────────────────────────────

type StatusLevel = "live" | "next" | "foundation";

const STATUS_CONFIG: Record<StatusLevel, { label: string; dot: string; badge: string; text: string }> = {
  live:       { label: "In MVP",      dot: "bg-emerald-400",  badge: "border-emerald-400/20 bg-emerald-400/[0.06]", text: "text-emerald-400/80" },
  next:       { label: "Next Step",   dot: "bg-amber-400",    badge: "border-amber-400/20 bg-amber-400/[0.06]",     text: "text-amber-400/80" },
  foundation: { label: "Foundation",  dot: "bg-[#8cb7ff]",    badge: "border-[#8cb7ff]/20 bg-[#8cb7ff]/[0.06]",    text: "text-[#8cb7ff]/80" },
};

// ── Stack ─────────────────────────────────────────────────────────────────────

const stack = [
  { label: "Backend",   value: "FastAPI · Python 3.11" },
  { label: "Database",  value: "PostgreSQL + pgvector" },
  { label: "Queue",     value: "Redis + RQ" },
  { label: "Frontend",  value: "Next.js 14 · React Native (Expo)" },
  { label: "LLM",       value: "GPT-4o / GPT-4o-mini · OpenAI Embeddings" },
  { label: "Deploy",    value: "Railway (API) · Vercel (Web)" },
];

// ── Sections ──────────────────────────────────────────────────────────────────

type Module = { name: string; detail: string };

type Section = {
  id: string;
  status: StatusLevel;
  layer: string;
  heading: string;
  summary: string;
  enables: string;
  modules: Module[];
};

const sections: Section[] = [
  // ── IN MVP — ground up ────────────────────────────────────────────────────
  {
    id: "data",
    status: "live",
    layer: "Layer 1 · Data",
    heading: "Personal Model — 179 Tables",
    summary: "Every conversation writes into a structured model of the person. 179 tables organized by domain: state, memory, soul, identity, rhythm, coherence, alignment. Not a user profile — a living representation that evolves with every exchange.",
    enables: "Enables: a system that knows who you are before you speak",
    modules: [
      { name: "operating_system", detail: "Constitutional type (Adaptive/Performance/Conservation). Set at onboarding, refined continuously." },
      { name: "short_term / long_term", detail: "Current state drift + persistent emotional, mind, and soul layers." },
      { name: "soul_state / identity_state", detail: "Shadow, light, conflicts, identity momentum — the deeper model of who the person is becoming." },
      { name: "rhythm_state / energy_state", detail: "Chronobiological patterns. Time-of-day awareness baked into every response." },
      { name: "coherence_state / alignment_state", detail: "Are actions matching values? Is thinking coherent across domains? Tracked continuously." },
      { name: "30+ cache tables", detail: "Pre-computed context for morning, evening, micro-flow, reflection — so the main turn reads, not computes." },
    ],
  },
  {
    id: "kala",
    status: "live",
    layer: "Layer 2 · Engine",
    heading: "Kala — Temporal Intelligence Engine",
    summary: "The computational core of Sakhi. Kala provides the pure-computation layer for everything temporal: arc tracking, vector similarity for memory recall, state drift, pattern crystallization, and alignment. It has zero external dependencies and 552 tests. Every layer above it draws from Kala.",
    enables: "Enables: memory that works, arcs that track how threads evolve, patterns that surface reliably",
    modules: [
      { name: "Temporal arcs", detail: "TemporalArc, ArcPhase, ArcFeatures — generic arc data types used to track how any thread begins, evolves, and where it is now." },
      { name: "Memory vector math", detail: "cosine_similarity, recency_weight, diversity_filter — powers memory recall scoring in every turn." },
      { name: "State & drift", detail: "Constitution computation and drift tracking. Detects when a person is veering from their baseline." },
      { name: "Pattern trajectory", detail: "PatternCandidate — detects when a repeating signal has solidified into a durable pattern." },
      { name: "Constraint evaluation", detail: "11 operators (equals, range, threshold, rate-of-change). Priority-based HARD/SOFT enforcement." },
      { name: "Objective versioning", detail: "v1 → v2 → v3 with full lineage. The system knows how a person's goals evolved, and when a goal was replaced." },
      { name: "Event ledger", detail: "Every decision logged to governance_events. Fully auditable trail of how the system reasoned." },
      { name: "552 tests", detail: "Full coverage. Pure computation — no mocks, no external calls, reproducible everywhere." },
    ],
  },
  {
    id: "memory",
    status: "live",
    layer: "Layer 3 · Memory",
    heading: "Three-Tier Memory",
    summary: "Built on Kala's vector math. Short-term captures the recent signal. Episodic consolidates it into daily summaries with state vectors. Long-term extracts the patterns and identity themes that persist across months. Each tier feeds the next.",
    enables: "Enables: recall that is both recent and deep — not just what was said, but what it meant over time",
    modules: [
      { name: "Short-term (24–48h)", detail: "Recent conversations and journal entries. Hybrid search: 0.7 vector weight + 0.3 BM25 keyword. Exact matches boosted 5.5×." },
      { name: "Episodic (days–weeks)", detail: "Daily episode summaries with dosha/guna state vectors. Produced by episodic_consolidation_v21 worker." },
      { name: "Long-term (weeks–months)", detail: "Persistent patterns, values, identity themes, soul state. Stored in personal_model.long_term." },
      { name: "1536-dim embeddings", detail: "OpenAI text-embedding-3-small. Stored in PostgreSQL via pgvector extension." },
    ],
  },
  {
    id: "workers",
    status: "live",
    layer: "Layer 4 · Pipeline",
    heading: "Async Worker Queue — 50+ Workers",
    summary: "After every conversation turn, workers fire asynchronously via Redis + RQ. The main response returns in under 500ms. Workers enrich the personal model in the background — so every turn starts with a richer model than the last.",
    enables: "Enables: a model that compounds — every conversation makes the next one smarter",
    modules: [
      { name: "turn_memory_update", detail: "Ingests the user message into memory_short_term immediately." },
      { name: "episodic_consolidation_v21", detail: "Creates daily episode summaries with state vectors." },
      { name: "pattern_crystallization", detail: "Uses Kala's PatternCandidate to detect when a repeating signal becomes a durable pattern." },
      { name: "identity_momentum_deep", detail: "Tracks identity evolution across turns. Updates identity_state." },
      { name: "emotion_soul_rhythm_deep", detail: "Deep ESR integration — emotion, soul, and rhythm state in one pass." },
      { name: "longitudinal_update", detail: "Weekly learning pass — updates long-term model from accumulated episodes." },
      { name: "ayurvedic_pipeline", detail: "Extracts Ayurvedic signals — dosha drift, elemental state, energy state." },
    ],
  },
  {
    id: "turn",
    status: "live",
    layer: "Layer 5 · Conversation",
    heading: "The Turn — What the MVP Delivers",
    summary: "When a user sends a message: load brain_state from personal_model → build continuity pack from Kala arcs → generate_reply with full context. Response in under 500ms. Workers update the model in the background for the next turn.",
    enables: "Enables: a conversation that picks up where it left off — every time",
    modules: [
      { name: "brain_state", detail: "Single personal_model query at turn start. Loads current state, rhythm, soul, coherence, identity — no duplicate DB calls." },
      { name: "build_continuity_pack", detail: "Kala arcs: where each thread started, how it evolved, anchor moments, decision ledger. Injected into every reply." },
      { name: "generate_reply", detail: "GPT-4o with full context: brain_state + continuity pack + memory recall + session history." },
      { name: "enqueue_turn_jobs", detail: "Fire-and-forget after reply: memory update, episodic consolidation, pattern detection, state refresh." },
      { name: "< 500ms synchronous", detail: "The turn returns before background work runs. Users feel zero latency from the enrichment pipeline." },
    ],
  },

  // ── NEXT STEP ─────────────────────────────────────────────────────────────
  {
    id: "mobile",
    status: "next",
    layer: "Next · Surface",
    heading: "iOS + Android",
    summary: "React Native (Expo) app. The API, memory, Kala, and turn pipeline are fully built. The mobile app is the surface layer that makes this accessible anywhere. Currently in active build.",
    enables: "Enables: continuity in your pocket — the same thread, on every device",
    modules: [
      { name: "React Native (Expo)", detail: "Cross-platform — iOS and Android from a single codebase." },
      { name: "Core screens", detail: "Conversation, reflection, continuity arc, profile. Flow matches web." },
      { name: "Voice interface", detail: "STT → Sakhi → TTS pipeline already built on the API side. Mobile surface is the remaining connection." },
    ],
  },
  {
    id: "proactive",
    status: "next",
    layer: "Next · Intelligence",
    heading: "Proactive Delivery",
    summary: "The intelligence is pre-computed. Morning brief engines, nudge workers, and the rhythm scheduler already run. The next step is wiring them to scheduled push notifications so Sakhi surfaces the right thread before you ask.",
    enables: "Enables: continuity that finds you — not just continuity you have to seek",
    modules: [
      { name: "Morning brief", detail: "morning_ask + morning_momentum engines pre-compute the brief. Delivery is the remaining step." },
      { name: "Nudge worker", detail: "nudge_worker already runs. Surface as daily thread suggestions." },
      { name: "Google Calendar sync", detail: "Scheduling service built. OAuth integration is the remaining connection." },
    ],
  },

  // ── FOUNDATION ─────────────────────────────────────────────────────────────
  {
    id: "mesh",
    status: "foundation",
    layer: "Foundation · Network",
    heading: "Sakhi Mesh",
    summary: "The protocol for Sakhi-to-Sakhi coordination. Two Sakhis can schedule between people, coordinate on shared decisions, and share structured context — with explicit trust levels controlling what is shared. The groundwork for collective continuity.",
    enables: "Enables: continuity across people, not just within a person",
    modules: [
      { name: "Trust levels", detail: "minimal / standard / full. Each person controls exactly what their Sakhi shares with another." },
      { name: "Coordination protocol", detail: "Scheduling, inquiry, transaction — structured message types between Sakhis." },
    ],
  },
  {
    id: "agent",
    status: "foundation",
    layer: "Foundation · Execution",
    heading: "Desktop Agent",
    summary: "Sakhi can act on behalf of the user in the real world. The desktop agent runs on macOS. Browser automation via Playwright handles 90% of tasks using DOM selectors before falling back to vision.",
    enables: "Enables: Sakhi that doesn't just remember — it can act",
    modules: [
      { name: "Desktop agent (Electron)", detail: "macOS DMG. navigate, click, type, scroll. Accessibility + Screen Recording permissions." },
      { name: "Browser automation", detail: "Playwright DOM-first. Vision fallback via Claude Sonnet for complex UIs." },
      { name: "Session management", detail: "Persistent browser contexts, credential vault, session locking." },
    ],
  },
  {
    id: "email",
    status: "foundation",
    layer: "Foundation · Signals",
    heading: "Email Intelligence",
    summary: "Gmail OAuth integration that extracts behavioural signals from email patterns — not content. Subscriptions, avoidance patterns, boundary erosion, cognitive load. These signals feed Kala's state model.",
    enables: "Enables: Sakhi that sees what you're avoiding, not just what you're saying",
    modules: [
      { name: "Gmail OAuth sync", detail: "Full OAuth flow with incremental sync. Normalized metadata in email_events." },
      { name: "Signal extractors", detail: "subscription, avoidance, boundary, cognitive_load — each a standalone extractor." },
      { name: "Conversation integration", detail: "Email signals feed into the turn context when active." },
    ],
  },
];

// ── Components ────────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: StatusLevel }) {
  const c = STATUS_CONFIG[status];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[9px] font-semibold uppercase tracking-[0.28em] ${c.badge} ${c.text}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${c.dot}`} />
      {c.label}
    </span>
  );
}

function SectionCard({ section }: { section: Section }) {
  return (
    <FadeIn>
      <div className={`rounded-[28px] border p-6 sm:p-8 ${
        section.status === "live"
          ? "border-white/[0.08] bg-white/[0.025]"
          : section.status === "next"
          ? "border-amber-400/10 bg-amber-400/[0.03]"
          : "border-[#8cb7ff]/10 bg-[#8cb7ff]/[0.025]"
      }`}>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.3em] text-white/30">{section.layer}</p>
            <h3 className="mt-1.5 text-[clamp(1.2rem,2vw,1.6rem)] font-bold leading-[1.1] tracking-[-0.04em] text-white">
              {section.heading}
            </h3>
          </div>
          <StatusBadge status={section.status} />
        </div>

        <p className="mt-4 text-[0.88rem] leading-[1.7] text-slate-400 max-w-3xl">
          {section.summary}
        </p>

        <p className="mt-3 text-[0.82rem] font-semibold tracking-[-0.01em] text-[#8cb7ff]/60">
          ↳ {section.enables}
        </p>

        <div className="mt-5 grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
          {section.modules.map((m) => (
            <div key={m.name} className="rounded-[16px] border border-white/[0.06] bg-white/[0.02] px-4 py-3">
              <p className="text-[0.8rem] font-semibold tracking-[-0.02em] text-white/80">{m.name}</p>
              <p className="mt-1 text-[0.73rem] leading-[1.5] text-slate-500">{m.detail}</p>
            </div>
          ))}
        </div>
      </div>
    </FadeIn>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────

export function TechnicalDeck() {
  const [activeFilter, setActiveFilter] = useState<StatusLevel | "all">("all");

  const filtered = activeFilter === "all" ? sections : sections.filter((s) => s.status === activeFilter);

  return (
    <div className="min-h-screen bg-[#020617] text-white">
      <div className="mx-auto max-w-6xl px-5 py-10 sm:px-8 sm:py-14 md:px-12">

        {/* Header */}
        <FadeIn>
          <div className="mb-2 text-[10px] font-semibold uppercase tracking-[0.3em] text-[#8ab0ff]/60">
            Sakhi · Technical Architecture · Pre-Seed 2026
          </div>
          <h1 className="text-[clamp(1.8rem,4vw,3rem)] font-bold leading-[1.05] tracking-[-0.05em] text-white">
            How it works.
          </h1>
          <p className="mt-3 max-w-2xl text-[0.9rem] leading-[1.7] text-slate-400">
            Built ground up. Each layer enables the next. The MVP is a complete vertical slice — data, engine, memory, pipeline, conversation.
          </p>
        </FadeIn>

        {/* Stack */}
        <FadeIn delay={100}>
          <div className="mt-8 overflow-x-auto rounded-2xl border border-white/[0.07] bg-white/[0.02]">
            <div className="flex min-w-[560px] divide-x divide-white/[0.06]">
              {stack.map((s) => (
                <div key={s.label} className="flex flex-1 flex-col px-4 py-3">
                  <span className="text-[9px] font-semibold uppercase tracking-[0.28em] text-white/30">{s.label}</span>
                  <span className="mt-1 text-[0.8rem] font-semibold text-white/70">{s.value}</span>
                </div>
              ))}
            </div>
          </div>
        </FadeIn>

        {/* Filter */}
        <FadeIn delay={150}>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            {(["all", "live", "next", "foundation"] as const).map((f) => {
              const isActive = activeFilter === f;
              if (f === "all") {
                return (
                  <button
                    key="all"
                    type="button"
                    onClick={() => setActiveFilter("all")}
                    className={`rounded-full border px-3 py-1 text-[9px] font-semibold uppercase tracking-[0.28em] transition ${
                      isActive
                        ? "border-white/20 bg-white/10 text-white"
                        : "border-white/[0.08] text-white/30 hover:text-white/60"
                    }`}
                  >
                    All
                  </button>
                );
              }
              const c = STATUS_CONFIG[f];
              return (
                <button
                  key={f}
                  type="button"
                  onClick={() => setActiveFilter(f)}
                  className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[9px] font-semibold uppercase tracking-[0.28em] transition ${
                    isActive ? `${c.badge} ${c.text}` : "border-white/[0.08] text-white/30 hover:text-white/60"
                  }`}
                >
                  <span className={`h-1.5 w-1.5 rounded-full ${c.dot}`} />
                  {c.label}
                </button>
              );
            })}
          </div>
        </FadeIn>

        {/* Divider */}
        <div className="mt-8 h-px bg-white/[0.06]" />

        {/* Sections */}
        <div className="mt-8 flex flex-col gap-5">
          {filtered.map((section) => (
            <SectionCard key={section.id} section={section} />
          ))}
        </div>

        {/* Footer */}
        <div className="mt-14 border-t border-white/[0.05] pt-8">
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div>
              <p className="text-[0.78rem] text-slate-500">
                81 API routes · 50+ background workers · 179 database tables · 552 Kala tests
              </p>
              <p className="mt-1 text-[0.75rem] text-slate-600">
                All figures derived from the live codebase. No simulated capabilities included.
              </p>
            </div>
            <a
              href="/company-deck"
              className="inline-flex items-center gap-1.5 rounded-full border border-[#8cb7ff]/20 bg-[#8cb7ff]/[0.05] px-4 py-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-[#8cb7ff]/70 transition hover:border-[#8cb7ff]/40 hover:text-[#8cb7ff]"
            >
              Company Deck
              <svg viewBox="0 0 24 24" className="h-3 w-3 fill-none stroke-current" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 6l6 6-6 6" />
              </svg>
            </a>
          </div>
        </div>

      </div>
    </div>
  );
}
