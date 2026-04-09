"use client";

export default function SakhiOnePager() {
  return (
    <div className="min-h-screen bg-[#020617] text-white flex flex-col px-5 py-6 sm:px-8 sm:py-8 md:px-12 md:py-10">
      <div className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-5 md:gap-6">

        {/* Header */}
        <div className="flex items-end justify-between shrink-0">
          <div>
            <div className="mb-2 text-[10px] font-semibold uppercase tracking-[0.3em] text-[#8ab0ff]/70 sm:text-[11px] sm:tracking-[0.38em]">Sakhi · Pre-Seed · 2026</div>
            <h1 className="text-[clamp(1.5rem,4vw,2.6rem)] font-bold leading-[1.05] tracking-[-0.04em] text-white sm:tracking-[-0.05em]">
              Sakhi is the continuity layer for the human mind.
            </h1>
            <p className="mt-2 text-[0.82rem] text-slate-400 tracking-[-0.01em] sm:text-[clamp(0.8rem,1vw,0.9rem)]">
              An AI that remembers the thread, not just the prompt.
            </p>
          </div>
        </div>

        <div className="h-px bg-white/[0.07] shrink-0" />

        {/* Body — single col on mobile, two cols on md+ */}
        <div className="grid flex-1 grid-cols-1 gap-y-5 md:grid-cols-2 md:gap-x-10 md:gap-y-5">

          {/* LEFT COLUMN */}
          <div className="flex flex-col gap-5">

            {/* Problem */}
            <section>
              <div className="mb-2 inline-flex items-center rounded-full border border-rose-400/20 bg-rose-400/[0.06] px-2.5 py-0.5 text-[9px] font-semibold uppercase tracking-[0.3em] text-rose-400/70">Problem</div>
              <p className="text-[0.88rem] leading-[1.65] text-slate-400">
                Why do even smart people make bad decisions and execute inconsistently? Not from lack of intelligence, but because their thinking fragments.
              </p>
              <p className="mt-2 text-[0.85rem] font-semibold text-white/60">Money leaks. Performance slips. Clarity fades. Self-trust erodes.</p>
              <p className="mt-2 text-[0.85rem] font-semibold text-white/40">Every tool compounds progress in the outside world. None compound your thinking.</p>
              <p className="mt-2 text-[0.82rem] text-slate-500">The problem is not capture. It is losing the thread when you return.</p>
            </section>

            {/* Solution */}
            <section>
              <div className="mb-2 inline-flex items-center rounded-full border border-[#8cb7ff]/20 bg-[#8cb7ff]/[0.06] px-2.5 py-0.5 text-[9px] font-semibold uppercase tracking-[0.3em] text-[#8cb7ff]/70">Solution</div>
              <p className="text-[0.88rem] font-semibold leading-[1.65] text-white/65">
                Sakhi keeps your thoughts connected across time.
              </p>
              <p className="mt-2 text-[0.88rem] leading-[1.65] text-slate-400">
                It captures what matters, brings it back when it matters, and helps you continue instead of restart.
              </p>
              <p className="mt-2 text-[0.85rem] font-semibold text-[#8cb7ff]/80">
                Your thinking compounds.
              </p>
            </section>

            {/* Why Now */}
            <section>
              <div className="mb-2 inline-flex items-center rounded-full border border-emerald-400/20 bg-emerald-400/[0.06] px-2.5 py-0.5 text-[9px] font-semibold uppercase tracking-[0.3em] text-emerald-400/70">Why Now</div>
              <div className="space-y-2">
                {[
                  { tag: "Model Shift", body: "AI can now hold conversations rich enough to make a continuity layer possible." },
                  { tag: "Behavior Shift", body: "People now externalize thoughts and decisions into AI as a natural behavior." },
                  { tag: "Category Gap", body: "Notes apps store. AI chats respond. Nobody compounds thought over time." },
                ].map((w) => (
                  <div key={w.tag} className="flex gap-2 text-[0.84rem] leading-[1.5]">
                    <span className="w-[6.75rem] shrink-0 font-semibold text-emerald-400/70">{w.tag}:</span>
                    <span className="text-slate-400">{w.body}</span>
                  </div>
                ))}
              </div>
              <p className="mt-2 text-[0.78rem] text-slate-500 italic">Nobody owns the continuity layer. That gap is the company.</p>
            </section>

            {/* Business Model */}
            <section>
              <div className="mb-2 inline-flex items-center rounded-full border border-violet-400/20 bg-violet-400/[0.06] px-2.5 py-0.5 text-[9px] font-semibold uppercase tracking-[0.3em] text-violet-400/70">Business Model</div>
              <div className="space-y-2">
                {[
                  { tier: "Free", desc: "Limited continuity." },
                  { tier: "Pro · $20/mo", desc: "Full continuity across time. Your thinking compounds." },
                  { tier: "Collective · $30/user/mo", desc: "Continuity across people. Year 2." },
                ].map((t) => (
                  <div key={t.tier} className="flex gap-2.5 text-[0.84rem] leading-[1.5]">
                    <span className="shrink-0 font-semibold text-white/65 w-[9.5rem]">{t.tier}</span>
                    <span className="text-slate-500">{t.desc}</span>
                  </div>
                ))}
              </div>
              <p className="mt-3 text-[0.84rem] font-semibold text-[#8cb7ff]/70">
                Not a subscription for usage. A subscription for thinking that compounds.
              </p>
            </section>

          </div>

          {/* RIGHT COLUMN */}
          <div className="flex flex-col gap-5">

            {/* Metrics */}
            <section>
              <div className="mb-2 inline-flex items-center rounded-full border border-amber-400/20 bg-amber-400/[0.06] px-2.5 py-0.5 text-[9px] font-semibold uppercase tracking-[0.3em] text-amber-400/70">12-Month Targets</div>
              <div className="grid grid-cols-3 gap-1.5 sm:gap-2">
                {[
                  { val: "10K+", label: "Active users" },
                  { val: "2K+", label: "Paying" },
                  { val: "$35–40K", label: "MRR" },
                ].map((m) => (
                  <div key={m.label} className="rounded-xl border border-white/[0.07] bg-white/[0.02] px-3 py-3 text-center">
                    <div className="text-[1.25rem] font-bold tracking-[-0.04em] text-white">{m.val}</div>
                    <div className="mt-0.5 text-[8px] font-semibold uppercase tracking-[0.16em] text-white/35">{m.label}</div>
                  </div>
                ))}
              </div>
              <p className="mt-2 text-[0.78rem] text-slate-500">60%+ Day-90 retention. Seed target: Month 12–15 · $4–5M · $15–20M valuation.</p>
            </section>

            {/* The Ask */}
            <section className="rounded-2xl border border-[#8cb7ff]/15 bg-[#8cb7ff]/[0.04] px-5 py-4">
              <div className="mb-1 inline-flex items-center rounded-full border border-[#8cb7ff]/20 bg-[#8cb7ff]/[0.06] px-2.5 py-0.5 text-[9px] font-semibold uppercase tracking-[0.3em] text-[#8cb7ff]/60">Pre-Seed Ask</div>
              <div className="text-[2.1rem] font-bold leading-none tracking-[-0.06em] text-white">$1,250,000</div>
              <p className="mt-2 text-[0.84rem] leading-[1.6] text-slate-400">To prove continuity can become a retained consumer behavior and a real subscription business.</p>
              <div className="mt-3 grid grid-cols-1 gap-y-1.5 sm:grid-cols-2 sm:gap-x-4">
                {[
                  { label: "Product + Engineering", amt: "$600K · 48%" },
                  { label: "Growth", amt: "$275K · 22%" },
                  { label: "Runway + Buffer", amt: "$250K · 20%" },
                  { label: "Legal + Ops", amt: "$125K · 10%" },
                ].map((a) => (
                  <div key={a.label} className="flex justify-between text-[0.78rem]">
                    <span className="text-slate-500">{a.label}</span>
                    <span className="font-semibold text-white/45">{a.amt}</span>
                  </div>
                ))}
              </div>
            </section>

            {/* Founders */}
            <section>
              <div className="mb-2">
                <a
                  href="/founder-story" target="_blank" rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 rounded-full border border-[#8cb7ff]/25 bg-[#8cb7ff]/[0.06] px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#8cb7ff]/70 animate-[cta-pulse_2.5s_ease-in-out_infinite] [animation-delay:2s] transition hover:border-[#8cb7ff]/50 hover:text-[#8cb7ff]"
                >
                  <svg viewBox="0 0 24 24" className="h-2.5 w-2.5 fill-none stroke-current shrink-0" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <path d="M5 3l14 9-14 9V3z" />
                  </svg>
                  Meet Founders
                </a>
              </div>
              <div className="space-y-2">
                {[
                  { name: "Vidhya Padmanabhan", role: "CEO", bio: "20+ years partnering with executives and C-suite at a $4B public company and a high-growth SaaS firm serving large enterprises, building systems that turned ambiguity into structured decisions. Sakhi is the system she wished existed when she needed it most." },
                  { name: "Ravi Shankar", role: "CTO", bio: "Engineering, product, and AI systems thinker. Technical depth meets lived human understanding." },
                ].map((f) => (
                  <div key={f.name} className="flex flex-col gap-0.5 text-[0.84rem] leading-[1.5] sm:flex-row sm:gap-4">
                    <div className="shrink-0 sm:w-[7.5rem]">
                      <span className="font-semibold text-white/70">{f.name}</span>
                      <span className="ml-2 text-[0.75rem] text-white/30 sm:ml-0 sm:block">{f.role}</span>
                    </div>
                    <span className="text-slate-500">{f.bio}</span>
                  </div>
                ))}
              </div>
              {/* CTAs below the founders */}
              <div className="mt-4 flex items-center gap-3 border-t border-white/[0.07] pt-4">
                <a
                  href="/story" target="_blank" rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 rounded-full border border-[#8cb7ff]/25 bg-[#8cb7ff]/[0.06] px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#8cb7ff]/70 animate-[cta-pulse_2.5s_ease-in-out_infinite] transition hover:border-[#8cb7ff]/50 hover:text-[#8cb7ff]"
                >
                  <svg viewBox="0 0 24 24" className="h-2.5 w-2.5 fill-none stroke-current" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round"><path d="M5 3l14 9-14 9V3z" /></svg>
                  What&apos;s Sakhi
                </a>
                <a
                  href="/company-deck" target="_blank" rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 rounded-full border border-[#8cb7ff]/25 bg-[#8cb7ff]/[0.06] px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#8cb7ff]/70 animate-[cta-pulse_2.5s_ease-in-out_infinite] [animation-delay:1s] transition hover:border-[#8cb7ff]/50 hover:text-[#8cb7ff]"
                >
                  Company Deck
                  <svg viewBox="0 0 24 24" className="h-2.5 w-2.5 fill-none stroke-current" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round"><path d="M9 6l6 6-6 6" /></svg>
                </a>
              </div>
            </section>

          </div>
        </div>

        {/* Vision statement — gradient rule + elevated text */}
        <div className="shrink-0 pt-1 pb-2">
          {/* Gradient separator */}
          <div className="mb-4 h-px w-full" style={{ background: "linear-gradient(to right, transparent, #8cb7ff55 30%, #a78bfa55 55%, #8cb7ff55 70%, transparent)" }} />
          <p className="text-center text-[clamp(1.2rem,3vw,2.6rem)] font-bold leading-[1.1] tracking-[-0.04em] text-white/60 sm:leading-[1.05] sm:tracking-[-0.05em]">
            The physical world has infrastructure. The mind has none.{" "}
            <span className="text-[#8cb7ff]">Sakhi is built to become it.</span>
          </p>
        </div>

      </div>
    </div>
  );
}
