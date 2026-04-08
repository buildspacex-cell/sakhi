"use client";

import { useState } from "react";
import { FadeIn } from "@/components/pitch/FadeIn";

// ── Types ─────────────────────────────────────────────────────────────────────

type StatusLevel = "live" | "next" | "foundation";

const STATUS_CONFIG: Record<StatusLevel, { label: string; dot: string; badge: string; text: string }> = {
  live:       { label: "Live & Tested",  dot: "bg-emerald-400",  badge: "border-emerald-400/20 bg-emerald-400/[0.06]", text: "text-emerald-400/80" },
  next:       { label: "Next Step",      dot: "bg-amber-400",    badge: "border-amber-400/20 bg-amber-400/[0.06]",     text: "text-amber-400/80" },
  foundation: { label: "Baked In",       dot: "bg-[#8cb7ff]",    badge: "border-[#8cb7ff]/20 bg-[#8cb7ff]/[0.06]",    text: "text-[#8cb7ff]/80" },
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
  eyebrow: string;
  heading: string;
  summary: string;
  modules: Module[];
  anchor?: string;
};

const sections: Section[] = [
  // ── LIVE ──────────────────────────────────────────────────────────────────
  {
    id: "continuity",
    status: "live",
    eyebrow: "Core Engine",
    heading: "Continuity Engine",
    summary: "The system that keeps threads alive across time. Every conversation contributes to a growing model of the person — what they are navigating, what keeps repeating, and what matters most.",
    anchor: "An AI that remembers the thread, not just the prompt.",
    modules: [
      { name: "Topic compiler", detail: "Windowed compilation of live threads from journal entries and conversation turns." },
      { name: "Arc retrieval", detail: "Deterministic continuity arc for any anchor — where a thread began, how it evolved, where it is now." },
      { name: "Continuity pack", detail: "Injected into every turn: compact history, phase path, anchor moments, decision ledger." },
      { name: "Deep Reflect", detail: "Async job flow — 4 modes: topic_reflection, deep_answer, whole_story, cross_context. Quality-gated LLM synthesis." },
      { name: "Cross-topic signals", detail: "Embedding cosine similarity across all thread combinations. Detects when separate life areas are actually connected." },
      { name: "Surface policy", detail: "Per-person policy controlling what continuity surfaces when. Mirror-only gate when detail is blocked." },
    ],
  },
  {
    id: "kala",
    status: "live",
    eyebrow: "Governance Kernel",
    heading: "Kala",
    summary: "A pure-computation governance kernel with zero external dependencies. Kala evaluates every proposed AI action against a constraint set before it is delivered — ensuring the system stays aligned with the person's stated values over time.",
    modules: [
      { name: "Constraint evaluation", detail: "11 operators (equals, range, threshold, rate-of-change, etc.), priority-based HARD/SOFT enforcement." },
      { name: "Drift gating", detail: "Tracks drift % from baseline. Gates responses when drift crosses configured thresholds." },
      { name: "Contradiction detection", detail: "5 typed categories. Surfaces when objectives conflict before they cause harm." },
      { name: "Objective versioning", detail: "v1 → v2 → v3 with full lineage tracking. The system knows how a person's goals evolved." },
      { name: "Temporal substrate", detail: "Timeline, moving averages, trend detection, pattern crystallization — all deterministic." },
      { name: "Event ledger", detail: "Every governance decision logged to governance_events. Fully auditable." },
      { name: "552 tests", detail: "Full coverage suite. Pure computation — no mocks, no external calls, reproducible everywhere." },
    ],
  },
  {
    id: "memory",
    status: "live",
    eyebrow: "Memory Architecture",
    heading: "Three-Tier Memory",
    summary: "Modelled on human memory. Short-term captures the recent signal. Episodic consolidates it into summaries with state vectors. Long-term extracts the patterns and identity themes that persist across months.",
    modules: [
      { name: "Short-term (24–48h)", detail: "Recent conversations and journal entries. High-recall via hybrid search (0.7 vector + 0.3 BM25 keyword)." },
      { name: "Episodic (days–weeks)", detail: "Daily episode summaries with dosha/guna state vectors. Produced by episodic_consolidation_v21 worker." },
      { name: "Long-term (weeks–months)", detail: "Persistent patterns, values, identity themes, soul state. Stored in personal_model.long_term." },
      { name: "Hybrid search", detail: "pgvector semantic search + BM25 keyword scoring. Exact matches boosted 5.5× over pure semantic." },
      { name: "1536-dim embeddings", detail: "OpenAI text-embedding-3-small. Stored in PostgreSQL via pgvector extension." },
    ],
  },
  {
    id: "context",
    status: "live",
    eyebrow: "Intelligence Routing",
    heading: "Context Router — 13 Modules",
    summary: "Every message is routed through a tiered system. Tier 1 is always-on, cheap, deterministic — a 360° awareness scan. Tier 2 fires only the modules that are relevant, keeping prompt cost low while ensuring no context is missed.",
    modules: [
      { name: "Tier 1 — 360° scan", detail: "Identity momentum, emotional state, moment mode, friction state, morning/evening cache, reflection status. ~0ms, pure functions." },
      { name: "Tier 2 — Deep modules", detail: "Full LLM + DB sections only for active modules: identity, emotional_depth, moment, recommendations, scheduling, email, causal, micro_flow, vision, agentic." },
      { name: "Deterministic classifier", detail: "Keyword/pattern classifier + intent routing + time-based routing (morning/evening rituals)." },
      { name: "LLM fallback", detail: "GPT-4o-mini invoked only when classifier confidence < 0.5." },
      { name: "Response latency", detail: "Synchronous response < 500ms. Background workers update intelligence for the next turn." },
    ],
  },
  {
    id: "engines",
    status: "live",
    eyebrow: "Computation Layer",
    heading: "34 Engines",
    summary: "Standalone deterministic engines that produce pre-computed intelligence. Each has its own engine.py. They run in the background and feed the context system — so the main conversation pipeline reads from computed state rather than computing on-demand.",
    modules: [
      { name: "State & Identity", detail: "alignment, coherence, identity_drift, identity_momentum — tracks how a person is changing." },
      { name: "Emotion & Soul", detail: "emotion_loop, empathy, microreg, inner_conflict, inner_dialogue — emotional attunement layer." },
      { name: "Daily Flows", detail: "morning_ask, morning_momentum, morning_preview, evening_closure, daily_reflection — rhythm-aware intelligence." },
      { name: "Narrative & Patterns", detail: "narrative, reflection_trace, pattern_sense, forecast, continuity — pattern detection and arc building." },
      { name: "Micro Interventions", detail: "micro_journey, micro_momentum, micro_recovery, mini_flow — small targeted nudges." },
      { name: "Planning & Action", detail: "focus_path, hands, nudge, tone, task_routing — execution and action routing." },
      { name: "Reasoning", detail: "deliberation_scaffold, evidence_pack, moment_model — structured reasoning frameworks." },
    ],
  },
  {
    id: "workers",
    status: "live",
    eyebrow: "Background Pipeline",
    heading: "Async Worker Queue",
    summary: "After every conversation turn, a set of workers run asynchronously via Redis + RQ. The main turn returns in < 500ms. Workers update intelligence in the background so the next turn starts with a richer model.",
    modules: [
      { name: "turn_memory_update", detail: "Ingests the user message into memory_short_term immediately." },
      { name: "ayurvedic_pipeline", detail: "Extracts Ayurvedic signals — dosha drift, elemental state, energy state." },
      { name: "episodic_consolidation_v21", detail: "Creates daily episode summaries with state vectors." },
      { name: "emotion_soul_rhythm_deep", detail: "Deep ESR integration — emotion, soul, and rhythm state in one pass." },
      { name: "identity_momentum_deep", detail: "Tracks identity evolution across turns. Updates identity_state." },
      { name: "pattern_crystallization", detail: "Detects when a repeating signal has solidified into a durable pattern." },
      { name: "longitudinal_update", detail: "Weekly learning pass — updates long-term model from accumulated episodes." },
      { name: "50+ workers total", detail: "Including rhythm_forecast, soul_refresh, theme_inference, weekly_signals, tone_continuity, and more." },
    ],
  },
  {
    id: "personal-model",
    status: "live",
    eyebrow: "Data Model",
    heading: "Personal Model — 179 Tables",
    summary: "The personal_model table is the single source of truth for all user intelligence. 179 tables total, organized by domain. Every conversation enriches this model — it is what makes the next conversation smarter.",
    modules: [
      { name: "operating_system", detail: "Constitutional type (Vata/Pitta/Kapha → Adaptive/Performance/Conservation). Set during onboarding, refined over time." },
      { name: "short_term / long_term", detail: "Current dosha drift + persistent emotional, mind, and soul layers." },
      { name: "soul_state / identity_state", detail: "Shadow, light, conflicts, identity momentum — the deeper model of who the person is becoming." },
      { name: "rhythm_state / energy_state", detail: "Chronobiological patterns. Time-of-day awareness baked into every response." },
      { name: "coherence_state / alignment_state", detail: "Are actions matching values? Is thinking coherent across domains? Tracked continuously." },
      { name: "30+ cache tables", detail: "Pre-computed context for morning, evening, micro-flow, reflection — so the main turn reads, not computes." },
    ],
  },

  // ── NEXT STEP ─────────────────────────────────────────────────────────────
  {
    id: "mobile",
    status: "next",
    eyebrow: "Next — Mobile",
    heading: "iOS + Android Apps",
    summary: "React Native (Expo) app. The API, memory, continuity, and personalization engine are fully built — the mobile app is the surface layer that makes this accessible anywhere. Currently in active build.",
    modules: [
      { name: "React Native (Expo)", detail: "Cross-platform — iOS and Android from a single codebase." },
      { name: "Core screens", detail: "Conversation, reflection, continuity arc, profile. Flow matches web exactly." },
      { name: "Auth bypass for dev", detail: "EXPO_PUBLIC_DEV_BYPASS_PERSON_ID for development builds. Production uses Supabase auth." },
      { name: "Voice interface", detail: "STT → Sakhi → TTS pipeline already built on the API side. Mobile surface is the next connection." },
    ],
  },
  {
    id: "proactive",
    status: "next",
    eyebrow: "Next — Intelligence",
    heading: "Proactive Intelligence",
    summary: "The infrastructure for proactive nudges is built — morning/evening ritual engines, nudge_worker, rhythm_scheduler, send_rhythm_nudge all exist. The next step is surfacing them as scheduled push notifications.",
    modules: [
      { name: "Morning briefing", detail: "morning_ask + morning_momentum engines pre-compute the brief. Delivery to mobile is the remaining step." },
      { name: "Relationship nudges", detail: "nudge_worker already runs. Surface as a daily thread suggestion." },
      { name: "Google Calendar sync", detail: "calendar.py route and scheduling service built. OAuth integration is the next connection." },
      { name: "Daily digest", detail: "Continuity + episode summary + nudge — assembled and pushed to the user each morning." },
    ],
  },

  // ── FOUNDATION ─────────────────────────────────────────────────────────────
  {
    id: "mesh",
    status: "foundation",
    eyebrow: "Foundation — Network",
    heading: "Sakhi Mesh",
    summary: "The protocol for Sakhi-to-Sakhi coordination. Two Sakhis can schedule between people, coordinate on shared decisions, and share structured context — with explicit trust levels controlling what is shared.",
    modules: [
      { name: "Mesh entities", detail: "People + businesses as first-class entities in the mesh." },
      { name: "Trust levels", detail: "minimal / standard / full. Controls what each Sakhi shares with another." },
      { name: "Coordination protocol", detail: "Scheduling, inquiry, transaction — structured message types between Sakhis." },
      { name: "Privacy-respecting availability", detail: "Each person controls exactly what their Sakhi shares. Nothing is automatic." },
    ],
  },
  {
    id: "agent",
    status: "foundation",
    eyebrow: "Foundation — Execution",
    heading: "Desktop Agent + Browser Automation",
    summary: "Sakhi can act on behalf of the user in the real world. The desktop agent runs on macOS. Browser automation via Playwright handles 90% of tasks using DOM selectors before falling back to vision.",
    modules: [
      { name: "Desktop agent (Electron)", detail: "macOS DMG. Accessibility + Screen Recording permissions. navigate, click, type, scroll actions." },
      { name: "Browser automation", detail: "Playwright-based. DOM-first strategy (free CSS/XPath/text). Vision fallback via Claude Sonnet for complex UIs." },
      { name: "Session management", detail: "Persistent browser contexts, credential vault, session locking via PostgreSQL advisory locks." },
      { name: "3-layer retry", detail: "Exponential backoff, timeout clamping, 50-item action history with compaction." },
    ],
  },
  {
    id: "email",
    status: "foundation",
    eyebrow: "Foundation — Signals",
    heading: "Email Intelligence",
    summary: "Gmail OAuth integration that extracts behavioural signals from email patterns — not content. Subscriptions, avoidance patterns, boundary erosion, cognitive load. These signals feed the continuity model.",
    modules: [
      { name: "Gmail OAuth sync", detail: "Full OAuth flow with incremental sync. Stores normalized metadata in email_events." },
      { name: "Signal extractors", detail: "subscription, avoidance, boundary, cognitive_load — each a standalone extractor module." },
      { name: "Email digest", detail: "GPT-4o-mini triage — action items, FYI, noise, commitments. Batch size 3, per-item validation." },
      { name: "Conversation integration", detail: "email context module feeds the Context Router's Tier 2 when email signals are active." },
    ],
  },
  {
    id: "governance-future",
    status: "foundation",
    eyebrow: "Foundation — Alignment",
    heading: "Long-Term Alignment via Kala",
    summary: "As Sakhi grows, Kala becomes the alignment layer that ensures the system stays consistent with who the person is becoming — not just who they were when they onboarded. The ledger and objective versioning are already built for this.",
    modules: [
      { name: "Objective evolution", detail: "A person's goals change. Kala tracks v1 → v2 → v3 with lineage. The system knows when a goal was replaced, and why." },
      { name: "Governance event ledger", detail: "Every decision logged to governance_events. Future: user-visible audit trail of how Sakhi reasoned." },
      { name: "Drift as a feature", detail: "Drift % is not just a safety gate — it is a signal that something is changing. Future: surface drift to the user as self-knowledge." },
      { name: "Multi-Sakhi governance", detail: "When Sakhis coordinate via Mesh, Kala ensures each agent's actions respect the other person's constraints. The groundwork is in the constraint model." },
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
            <p className="text-[10px] font-semibold uppercase tracking-[0.3em] text-white/30">{section.eyebrow}</p>
            <h3 className="mt-1.5 text-[clamp(1.2rem,2vw,1.6rem)] font-bold leading-[1.1] tracking-[-0.04em] text-white">
              {section.heading}
            </h3>
          </div>
          <StatusBadge status={section.status} />
        </div>

        <p className="mt-4 text-[0.88rem] leading-[1.7] text-slate-400 max-w-3xl">
          {section.summary}
        </p>

        {section.anchor && (
          <p className="mt-3 text-[0.82rem] font-semibold tracking-[-0.01em] text-[#8cb7ff]/70">
            ↳ {section.anchor}
          </p>
        )}

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
            What is live and tested in production, what is actively being built, and what is already baked in as the foundation for where this goes next.
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

        {/* Legend + Filter */}
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
                81 API routes · 34 engines · 50+ background workers · 179 database tables · 552 governance tests
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
