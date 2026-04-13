"use client";

export default function SakhiOnePagerV1() {
  return (
    <div className="min-h-screen bg-[#020617] text-white flex flex-col px-5 py-5 sm:px-8 sm:py-6 md:px-12 md:py-8">
      <div className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-4 md:gap-5">

        {/* Header */}
        <div className="shrink-0">
          <div className="mb-1.5 text-[10px] font-semibold uppercase tracking-[0.3em] text-[#8ab0ff]/70 sm:text-[11px] sm:tracking-[0.38em]">Sakhi · Pre-Seed · 2026</div>
          <h1 className="text-[clamp(1.35rem,3.5vw,2.2rem)] font-bold leading-[1.05] tracking-[-0.04em] text-white sm:tracking-[-0.05em]">
            Sakhi is the continuity layer for the human mind.
          </h1>
          <p className="mt-2 text-[0.82rem] text-slate-400 tracking-[-0.01em] sm:text-[clamp(0.8rem,1vw,0.9rem)]">
            Your thinking compounds. Your life stays connected, across time.
          </p>
        </div>

        <div className="h-px bg-white/[0.07] shrink-0" />

        {/* Problem + Solution — two columns */}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 md:gap-8 shrink-0">

          {/* Problem */}
          <section>
            <div className="mb-1.5 inline-flex items-center rounded-full border border-rose-400/20 bg-rose-400/[0.06] px-2.5 py-0.5 text-[9px] font-semibold uppercase tracking-[0.3em] text-rose-400/70">Problem</div>
            <p className="text-[0.86rem] leading-[1.6] text-slate-400">
              ChatGPT and Claude respond, and they remember context. But they don&apos;t carry your discussions forward over time.
            </p>
            <p className="mt-1.5 text-[0.86rem] leading-[1.6] text-slate-400">
              Continuity depends on you. You have to maintain the thread.
            </p>
            <p className="mt-1.5 text-[0.86rem] leading-[1.6] text-slate-400">
              Come back later, rewrite the prompt, restate the context. Sometimes it works. Often it doesn&apos;t.
            </p>
            <p className="mt-1.5 text-[0.84rem] font-semibold text-white/40">So nothing really builds. Patterns are missed, and the answer never really becomes yours.</p>
          </section>

          {/* Solution */}
          <section>
            <div className="mb-1.5 inline-flex items-center rounded-full border border-[#8cb7ff]/20 bg-[#8cb7ff]/[0.06] px-2.5 py-0.5 text-[9px] font-semibold uppercase tracking-[0.3em] text-[#8cb7ff]/70">Solution</div>
            <p className="text-[0.86rem] leading-[1.6] text-slate-400">
              Sakhi carries the thread. Across days, across topics, it tracks where your discussions go and knows which parts matter to what you&apos;re asking now.
            </p>
            <p className="mt-1.5 text-[0.86rem] leading-[1.6] text-slate-400">
              You don&apos;t restate. You don&apos;t restructure. You just continue.
            </p>
            <p className="mt-1.5 text-[0.84rem] font-semibold text-[#8cb7ff]/80">The answer becomes yours.</p>
          </section>

        </div>

        <div className="h-px bg-white/[0.07] shrink-0" />

        {/* Experience — two proof stories */}
        <section className="shrink-0">
          <div className="mb-2 inline-flex items-center rounded-full border border-teal-400/20 bg-teal-400/[0.06] px-2.5 py-0.5 text-[9px] font-semibold uppercase tracking-[0.3em] text-teal-400/70">Experience</div>
          <div className="grid grid-cols-1 gap-2 md:grid-cols-2">

            <div className="rounded-lg border border-teal-400/[0.15] bg-teal-400/[0.03] px-4 py-3.5">
              <div className="flex items-center gap-1.5 mb-2">
                <span className="h-1.5 w-1.5 rounded-full bg-teal-400/50 shrink-0" />
                <span className="text-[9px] font-semibold uppercase tracking-[0.28em] text-teal-400/70">Health · Priya</span>
              </div>
              <p className="text-[0.84rem] leading-[1.65] text-slate-400">
                She described what she&apos;d been feeling. Vaguely, because she didn&apos;t have the pattern yet. Routine tests. Nothing conclusive.
              </p>
              <p className="mt-2 text-[0.84rem] leading-[1.6] text-slate-400">
                That night, she opened Sakhi. Eight months of health, sleep, and energy threads, held together while she lived them. She saw it for the first time.
              </p>
              <div className="my-2.5 rounded-md border border-white/[0.06] bg-white/[0.02] px-3 py-2 flex flex-col gap-1.5">
                {[
                  { month: "Month 1", items: ["Sleep down", "Fatigue up", "Cycle delay"] },
                  { month: "Month 3", items: ["Sleep down", "Fatigue up", "Cycle delay"] },
                  { month: "Month 6", items: ["Sleep down", "Fatigue up", "Cycle delay"] },
                ].map((row) => (
                  <div key={row.month} className="flex items-start gap-2">
                    <span className="mt-[0.2em] w-[4.5rem] shrink-0 whitespace-nowrap text-[9px] font-semibold uppercase tracking-[0.12em] text-teal-400">{row.month}</span>
                    <div className="flex items-center gap-1 flex-wrap">
                      {row.items.map((item, i) => (
                        <span key={item} className="flex items-center gap-1">
                          <span className="text-[0.7rem] font-medium text-slate-400">{item}</span>
                          {i < row.items.length - 1 && <span className="text-slate-600 text-[0.65rem]">&#8594;</span>}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
                <p className="text-[0.66rem] font-semibold text-teal-400/60 mt-0.5">Same sequence. Every time.</p>
              </div>
              <p className="text-[0.84rem] leading-[1.6] text-slate-400">
                She goes back. <span className="italic">&ldquo;Same pattern, three times. Can we test for thyroid?&rdquo;</span> They test. Diagnosis confirmed. Nothing missed.
              </p>
              <p className="mt-2.5 text-[0.76rem] font-semibold text-teal-400/60">Continuity held eight months together. The answer was already there.</p>
            </div>

            <div className="rounded-lg border border-purple-400/[0.12] bg-purple-400/[0.02] px-4 py-3.5">
              <div className="flex items-center gap-1.5 mb-2">
                <span className="h-1.5 w-1.5 rounded-full bg-purple-400/50 shrink-0" />
                <span className="text-[9px] font-semibold uppercase tracking-[0.28em] text-purple-400/70">Life · Nadia</span>
              </div>
              <p className="text-[0.84rem] leading-[1.65] text-slate-400">
                Her father suffers a TBI. Weeks in the ICU. Her days collapse into hospital rounds, doctor calls, and late-night updates. Work, kids, meals, sleep, all start slipping.
              </p>
              <p className="mt-2 text-[0.84rem] leading-[1.6] text-slate-400">
                Then she starts waking at 2 a.m. with her heart racing. She doesn&apos;t understand why it&apos;s happening. She opens Sakhi: <span className="italic">&ldquo;I&apos;m not giving up. I&apos;m doing everything I can to keep things going. What&apos;s happening at night? Why do I wake up in a panic?&rdquo;</span>
              </p>
              <div className="my-2.5 rounded-md border border-white/[0.06] bg-white/[0.02] px-3 py-2 flex flex-col gap-1.5">
                {[
                  { label: "Before", tags: ["Work steady", "Kids covered", "Sleeping normally"] },
                  { label: "Now", tags: ["ICU first", "Sleep gone", "Waking panicked"] },
                ].map((row) => (
                  <div key={row.label} className="flex items-center gap-1.5">
                    <span className="w-[4.8rem] shrink-0 text-[0.6rem] font-semibold text-purple-400/50">{row.label}</span>
                    <div className="flex gap-1 flex-wrap">
                      {row.tags.map((tag) => (
                        <span key={tag} className="rounded px-1.5 py-0.5 text-[0.6rem] font-medium bg-purple-400/[0.07] text-purple-300/60">{tag}</span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
              <p className="text-[0.84rem] leading-[1.6] text-slate-400">
                Sakhi doesn&apos;t invent an answer. It brings back what helped the last time her system went off balance: morning walks, yoga, and the notes she wrote when she finally started to steady.
              </p>
              <p className="mt-2.5 text-[0.76rem] font-semibold text-purple-400/60">Continuity held the path back, until she needed it again.</p>
            </div>

          </div>
        </section>

        <div className="h-px bg-white/[0.05] shrink-0" />

        {/* Body — two columns */}
        <div className="grid flex-1 grid-cols-1 gap-y-4 md:grid-cols-2 md:gap-x-10 md:gap-y-0">

          {/* LEFT COLUMN */}
          <div className="flex flex-col justify-between gap-4">

            {/* Why Now */}
            <section>
              <div className="mb-1.5 inline-flex items-center rounded-full border border-emerald-400/20 bg-emerald-400/[0.06] px-2.5 py-0.5 text-[9px] font-semibold uppercase tracking-[0.3em] text-emerald-400/70">Why Now</div>
              <div className="space-y-1.5">
                {[
                  { tag: "Model Shift", body: "AI can now hold conversations rich enough to make a continuity layer possible." },
                  { tag: "Behavior Shift", body: "People now externalize thoughts and decisions into AI as a natural behavior." },
                  { tag: "Category Gap", body: "Notes apps store. AI chats respond. Nobody compounds thought over time." },
                ].map((w) => (
                  <div key={w.tag} className="flex gap-2 text-[0.83rem] leading-[1.5]">
                    <span className="w-[6.5rem] shrink-0 font-semibold text-emerald-400/70">{w.tag}:</span>
                    <span className="text-slate-400">{w.body}</span>
                  </div>
                ))}
              </div>
              <p className="mt-1.5 text-[0.76rem] text-slate-500 italic">Nobody owns the continuity layer. That gap is the company.</p>
            </section>

            {/* Business Model */}
            <section>
              <div className="mb-1.5 inline-flex items-center rounded-full border border-violet-400/20 bg-violet-400/[0.06] px-2.5 py-0.5 text-[9px] font-semibold uppercase tracking-[0.3em] text-violet-400/70">Business Model</div>
              <div className="space-y-1.5">
                {[
                  { tier: "Free", desc: "Limited continuity." },
                  { tier: "Pro · $20/mo", desc: "Full continuity across time. Your thinking compounds." },
                  { tier: "Collective · $30/user/mo", desc: "Continuity across people. Year 2." },
                ].map((t) => (
                  <div key={t.tier} className="flex gap-2.5 text-[0.83rem] leading-[1.5]">
                    <span className="shrink-0 font-semibold text-white/65 w-[9.5rem]">{t.tier}</span>
                    <span className="text-slate-500">{t.desc}</span>
                  </div>
                ))}
              </div>
              <p className="mt-2 text-[0.83rem] font-semibold text-[#8cb7ff]/70">
                Not a subscription for usage. A subscription for thinking that compounds.
              </p>
            </section>

            {/* CTAs */}
            <div className="flex flex-wrap items-center gap-2">
              <a
                href="/founder-story" target="_blank" rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 rounded-full border border-[#8cb7ff]/25 bg-[#8cb7ff]/[0.06] px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#8cb7ff]/70 animate-[cta-pulse_2.5s_ease-in-out_infinite] transition hover:border-[#8cb7ff]/50 hover:text-[#8cb7ff]"
              >
                <svg viewBox="0 0 24 24" className="h-2.5 w-2.5 fill-none stroke-current shrink-0" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M5 3l14 9-14 9V3z" /></svg>
                Meet Founders
              </a>
              <a
                href="/story" target="_blank" rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 rounded-full border border-[#8cb7ff]/25 bg-[#8cb7ff]/[0.06] px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#8cb7ff]/70 animate-[cta-pulse_2.5s_ease-in-out_infinite] transition hover:border-[#8cb7ff]/50 hover:text-[#8cb7ff]"
              >
                <svg viewBox="0 0 24 24" className="h-2.5 w-2.5 fill-none stroke-current shrink-0" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M5 3l14 9-14 9V3z" /></svg>
                What&apos;s Sakhi
              </a>
              <a
                href="/company-deck-v1" target="_blank" rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 rounded-full border border-[#8cb7ff]/25 bg-[#8cb7ff]/[0.06] px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#8cb7ff]/70 animate-[cta-pulse_2.5s_ease-in-out_infinite] [animation-delay:1s] transition hover:border-[#8cb7ff]/50 hover:text-[#8cb7ff]"
              >
                Company Deck
                <svg viewBox="0 0 24 24" className="h-2.5 w-2.5 fill-none stroke-current shrink-0" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M9 6l6 6-6 6" /></svg>
              </a>
            </div>

          </div>

          {/* RIGHT COLUMN */}
          <div className="flex flex-col justify-between gap-4">

            {/* Metrics */}
            <section>
              <div className="mb-1.5 inline-flex items-center rounded-full border border-amber-400/20 bg-amber-400/[0.06] px-2.5 py-0.5 text-[9px] font-semibold uppercase tracking-[0.3em] text-amber-400/70">12-Month Targets</div>
              <div className="grid grid-cols-3 gap-1.5">
                {[
                  { val: "10K+", label: "Active users" },
                  { val: "2K+", label: "Paying" },
                  { val: "$35–40K", label: "MRR" },
                ].map((m) => (
                  <div key={m.label} className="rounded-xl border border-white/[0.07] bg-white/[0.02] px-3 py-2.5 text-center">
                    <div className="text-[1.2rem] font-bold tracking-[-0.04em] text-white">{m.val}</div>
                    <div className="mt-0.5 text-[8px] font-semibold uppercase tracking-[0.16em] text-white/35">{m.label}</div>
                  </div>
                ))}
              </div>
              <p className="mt-1.5 text-[0.76rem] text-slate-500">60%+ Day-90 retention. Seed: Month 12–15 · $4–5M · $15–20M valuation.</p>
            </section>

            {/* The Ask */}
            <section className="rounded-2xl border border-[#8cb7ff]/15 bg-[#8cb7ff]/[0.04] px-4 py-3.5">
              <div className="mb-1 inline-flex items-center rounded-full border border-[#8cb7ff]/20 bg-[#8cb7ff]/[0.06] px-2.5 py-0.5 text-[9px] font-semibold uppercase tracking-[0.3em] text-[#8cb7ff]/60">Pre-Seed Ask</div>
              <div className="text-[2rem] font-bold leading-none tracking-[-0.06em] text-white">$1,250,000</div>
              <p className="mt-1.5 text-[0.83rem] leading-[1.55] text-slate-400">To prove continuity becomes a retained consumer behavior and a real subscription business.</p>
              <div className="mt-2.5 grid grid-cols-2 gap-x-4 gap-y-1">
                {[
                  { label: "Product + Engineering", amt: "$600K · 48%" },
                  { label: "Growth", amt: "$275K · 22%" },
                  { label: "Runway + Buffer", amt: "$250K · 20%" },
                  { label: "Legal + Ops", amt: "$125K · 10%" },
                ].map((a) => (
                  <div key={a.label} className="flex justify-between text-[0.76rem]">
                    <span className="text-slate-500">{a.label}</span>
                    <span className="font-semibold text-white/45">{a.amt}</span>
                  </div>
                ))}
              </div>
            </section>

          </div>
        </div>

        {/* Vision statement */}
        <div className="shrink-0 pt-0.5 pb-1">
          <div className="mb-3 h-px w-full" style={{ background: "linear-gradient(to right, transparent, #8cb7ff55 30%, #a78bfa55 55%, #8cb7ff55 70%, transparent)" }} />
          <p className="text-center text-[clamp(0.95rem,2vw,1.5rem)] font-bold leading-[1.15] tracking-[-0.03em] text-white/55 sm:tracking-[-0.04em]">
            The physical world has infrastructure. The mind has none.{" "}
            <span className="text-[#8cb7ff]">Sakhi is built to become it.</span>
          </p>
        </div>

      </div>
    </div>
  );
}
