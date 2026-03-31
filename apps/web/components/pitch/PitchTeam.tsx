"use client";

import Image from "next/image";
import { FadeIn } from "@/components/pitch/FadeIn";

const founders = [
  {
    image: "/story/v-pic-20260327.png",
    imageStyle: {},
    name: "Vidhya",
    role: "Founder & CEO",
    bioLabel: "About Vidhya",
    bio: "Built systems for companies. Now building one for humans.",
    opening:
      "I've spent 20+ years helping organizations make better decisions. I realized we haven't solved this for individuals.",
    closing: "Sakhi is the system I wish existed when I needed it most.",
    beats: [
      {
        label: "Operator at Scale",
        body: "Worked alongside CEOs and COOs, building systems that turned ambiguity into structured decisions.",
      },
      {
        label: "Personal Inflection Point",
        body: "In 2024, caregiving, leadership, and life complexity collided. What was missing was continuity at the level of a real human life.",
      },
      {
        label: "Insight to Sakhi",
        body: "Small, personalized interventions changed everything. Timing and personalization mattered more than generic advice. The question became: can this be built as a system?",
      },
    ],
  },
  {
    image: "/story/r-pic.png",
    imageStyle: { objectPosition: "50% 24%" },
    name: "Ravi Shankar",
    role: "Co-founder & CTO",
    bioLabel: "About Ravi",
    bio: "Built systems across engineering, product, and AI. Now building one for the self.",
    opening:
      "I'm a systems thinker at heart, grounded in deep technical expertise and driven to simplify complexity.",
    closing: "That gives me the clarity to build Sakhi.",
    beats: [
      {
        label: "Evolution",
        body: "I started with engineering, building systems and applications, then kept moving closer to the question of what actually makes systems work.",
      },
      {
        label: "Realization",
        body: "Systems do not succeed just because they are built well. They succeed because people understand them, trust them, and use them.",
      },
      {
        label: "Expansion",
        body: "That pulled me across engineering, product, and product marketing, while yoga and meditation deepened how I think about human behavior over time.",
      },
      {
        label: "Convergence",
        body: "Technical depth, systems thinking, product narrative, and lived understanding of people now converge in building Sakhi.",
      },
    ],
  },
];

export function PitchTeam() {
  return (
    <section id="founders-story" className="border-t border-white/[0.06] bg-[#020617] px-8 py-32 sm:px-16 lg:px-24">
      <div className="mx-auto max-w-6xl">
        <FadeIn>
          <p className="text-[10px] sm:text-[11px] font-semibold uppercase tracking-[0.3em] text-[#8ab0ff]/80">
            Founders
          </p>
        </FadeIn>
        <FadeIn delay={100}>
          <h2 className="mt-5 font-semibold text-white max-w-[20ch] leading-[1.08] -tracking-[0.04em]" style={{ fontSize: "clamp(2.5rem, 5vw, 4.5rem)" }}>
            Built from lived experience.
          </h2>
        </FadeIn>
        <div className="mt-16 space-y-10">
          {founders.map((member, i) => (
            <FadeIn key={member.name} delay={200 + i * 120}>
              <div className="rounded-[40px] border border-white/10 bg-[linear-gradient(155deg,rgba(16,23,39,0.95),rgba(7,11,21,0.84))] p-8 sm:p-10">
                <div className="grid gap-8 lg:grid-cols-[220px_minmax(0,1fr)] lg:gap-10">
                  <div className="relative mx-auto aspect-[3/4] w-[170px] overflow-hidden rounded-[28px] border border-white/10 sm:w-[200px] lg:mx-0">
                    <Image
                      src={member.image}
                      alt={member.name}
                      fill
                      className="object-cover"
                      style={member.imageStyle}
                    />
                  </div>
                  <div className="min-w-0">
                    <p className="text-2xl font-semibold text-white -tracking-[0.03em]">
                      {member.name}
                    </p>
                    <p className="mt-1 text-sm font-medium text-[#8ab0ff]/70 uppercase tracking-[0.15em]">
                      {member.role}
                    </p>
                    <div className="mt-5 inline-flex max-w-xl flex-col rounded-[18px] border border-white/[0.08] bg-white/[0.03] px-4 py-3">
                      <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-white/34">
                        {member.bioLabel}
                      </p>
                      <p className="mt-2 text-[0.95rem] leading-[1.55] tracking-[-0.01em] text-white/62">
                        {member.bio}
                      </p>
                    </div>
                    <div className="mt-6 max-w-3xl rounded-[24px] border border-[#8ab0ff]/16 bg-[linear-gradient(160deg,rgba(140,176,255,0.08),rgba(255,255,255,0.02))] px-5 py-5 shadow-[0_24px_60px_rgba(0,0,0,0.18)]">
                      <p className="text-balance text-[1.26rem] font-semibold leading-[1.45] tracking-[-0.03em] text-white">
                        {member.opening}
                      </p>
                    </div>

                    <div className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                      {member.beats.map((beat) => (
                        <div
                          key={beat.label}
                          className="rounded-[24px] border border-white/[0.08] bg-white/[0.03] px-5 py-5"
                        >
                          <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-[#8ab0ff]/68">
                            {beat.label}
                          </p>
                          <p className="mt-3 text-[0.95rem] leading-[1.65] text-white/55">
                            {beat.body}
                          </p>
                        </div>
                      ))}
                    </div>

                    <p className="mt-8 text-[1.06rem] font-medium leading-7 tracking-[-0.02em] text-white">
                      {member.closing}
                    </p>
                  </div>
                </div>
              </div>
            </FadeIn>
          ))}
        </div>
      </div>
    </section>
  );
}
