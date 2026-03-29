"use client";

import { useRef } from "react";

import { motion, useScroll, useTransform } from "framer-motion";
import useStoryFocusOffsets from "@/components/story/useStoryFocusOffsets";

export default function CommunicationContinuitySection() {
  const ref = useRef<HTMLElement | null>(null);
  const offsets = useStoryFocusOffsets();
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: [...offsets.phase],
  });

  const headerOpacity = useTransform(scrollYProgress, [0, 0.16], [0.18, 1]);
  const headerY = useTransform(scrollYProgress, [0, 0.16], [24, 0]);

  const messagesOpacity = useTransform(scrollYProgress, [0, 0.2, 0.34, 0.46], [1, 1, 0.6, 0.22]);
  const messagesY = useTransform(scrollYProgress, [0, 0.2, 0.46], [0, 0, -18]);

  const timelineOpacity = useTransform(scrollYProgress, [0.16, 0.32, 0.5, 0.62], [0, 1, 1, 0.34]);
  const timelineY = useTransform(scrollYProgress, [0.16, 0.32, 0.62], [32, 0, -14]);

  const patternOpacity = useTransform(scrollYProgress, [0.34, 0.52, 0.7, 0.82], [0, 1, 1, 0.42]);
  const patternY = useTransform(scrollYProgress, [0.34, 0.52, 0.82], [24, 0, -10]);

  const decisionOpacity = useTransform(scrollYProgress, [0.56, 0.76, 1], [0, 1, 1]);
  const decisionScale = useTransform(scrollYProgress, [0.56, 0.76, 1], [0.96, 1.03, 1.02]);
  const decisionY = useTransform(scrollYProgress, [0.56, 0.76], [28, 0]);

  const connectorOpacity = useTransform(scrollYProgress, [0.18, 0.4, 0.74], [0.18, 0.55, 0.32]);
  const connectorScale = useTransform(scrollYProgress, [0.18, 0.4], [0.76, 1]);

  return (
    <section ref={ref} className="space-y-8">
      <div className="max-w-4xl">
        <motion.div
          style={{ opacity: headerOpacity, y: headerY }}
          className="text-[11px] font-semibold uppercase tracking-[0.32em] text-slate-400"
        >
          Communication continuity
        </motion.div>
        <motion.h2
          style={{ opacity: headerOpacity, y: headerY }}
          className="mt-4 max-w-[12ch] text-4xl font-semibold leading-[1.02] tracking-[-0.05em] text-white sm:text-5xl lg:text-6xl"
        >
          Communication becomes continuity.
        </motion.h2>
        <motion.p
          style={{ opacity: headerOpacity }}
          className="mt-5 max-w-3xl text-base leading-8 text-slate-300 sm:text-lg"
        >
          Sakhi turns messages into continuity, so decisions don&apos;t disappear
          inside scattered threads. Continuity becomes pattern awareness.
          Pattern awareness becomes better judgment.
        </motion.p>
      </div>

      <div className="overflow-hidden rounded-[32px] bg-[linear-gradient(180deg,rgba(17,22,32,0.72),rgba(10,13,20,0.94))] px-6 py-8 backdrop-blur-xl sm:px-8 sm:py-10">
        <div className="relative flex flex-col items-start justify-between gap-10 xl:flex-row xl:items-center xl:gap-12">
          <motion.div
            style={{ opacity: messagesOpacity, y: messagesY }}
            className="w-full max-w-[18rem] space-y-4"
          >
            <div className="text-[10px] font-semibold uppercase tracking-[0.28em] text-[#c4d2ff]">
              Sense
            </div>
            <h3 className="text-[1.9rem] font-semibold leading-[1.06] tracking-[-0.04em] text-white">
              Messages become part of your memory.
            </h3>
            <p className="text-sm leading-7 text-slate-300">
              Sakhi ingests communication and extracts what matters, turning
              messages into structured memory, not just summaries.
            </p>
            <div className="space-y-3">
              {[
                {
                  sender: "John",
                  message: "Can you take this on? Need quick turnaround.",
                },
                {
                  sender: "Maya",
                  message: "Can we revisit the partnership terms this week?",
                },
                {
                  sender: "Team",
                  message: "Following up on the deck. Can you send it tonight?",
                },
              ].map((item) => (
                <div
                  key={item.sender + item.message}
                  className="rounded-[18px] bg-white/5 px-4 py-3"
                >
                  <div className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
                    {item.sender}
                  </div>
                  <div className="mt-2 text-sm leading-6 text-slate-200">
                    {item.message}
                  </div>
                  {item.sender === "John" ? (
                    <div className="mt-3 text-sm text-white/60">
                      Similar asks have led to overload in the past.
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          </motion.div>

          <motion.div
            style={{ opacity: connectorOpacity, scaleX: connectorScale }}
            className="hidden h-px flex-1 origin-left bg-gradient-to-r from-white/10 via-[#9eb2ff]/45 to-transparent xl:block"
          />

          <div className="flex w-full max-w-[22rem] flex-col gap-8">
            <motion.div
              style={{ opacity: timelineOpacity, y: timelineY }}
              className="rounded-[24px] bg-white/5 p-5 backdrop-blur-xl"
            >
              <div className="text-[10px] font-semibold uppercase tracking-[0.28em] text-[#c4d2ff]">
                Connect
              </div>
              <h3 className="mt-4 text-[1.9rem] font-semibold leading-[1.06] tracking-[-0.04em] text-white">
                Continuity reveals what&apos;s actually happening.
              </h3>
              <p className="mt-4 text-sm leading-7 text-slate-300">
                Sakhi groups communication by true topic, tracks how it evolves,
                and brings relationship context into view.
              </p>
              <div className="mt-4 rounded-[20px] bg-black/20 p-4">
                <div className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
                  Partnership thread
                </div>
                <div className="mt-4 space-y-2 text-sm text-white/70">
                  <div>Week 1 - initial ask</div>
                  <div>Week 2 - scope changed</div>
                  <div>Week 3 - urgency increased</div>
                </div>
              </div>
            </motion.div>

            <motion.div
              style={{ opacity: patternOpacity, y: patternY }}
              className="rounded-[24px] bg-white/5 p-5 backdrop-blur-xl shadow-[0_0_12px_rgba(120,160,255,0.4)]"
            >
              <div className="text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-400">
                Pattern
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {[
                  "3 weeks of context",
                  "Repeated pressure pattern",
                  "Overcommitment history",
                  "Relationship memory",
                ].map((label) => (
                  <div
                    key={label}
                    className="rounded-full bg-white/5 px-3 py-1.5 text-[0.8rem] leading-none text-slate-200"
                  >
                    {label}
                  </div>
                ))}
              </div>
            </motion.div>
          </div>

          <motion.div
            style={{ opacity: decisionOpacity, scale: decisionScale, y: decisionY }}
            className="w-full max-w-[18.5rem] rounded-[28px] bg-white/5 p-6 backdrop-blur-xl"
          >
            <div className="text-[10px] font-semibold uppercase tracking-[0.28em] text-[#c4d2ff]">
              Decide
            </div>
            <h3 className="mt-4 text-[1.9rem] font-semibold leading-[1.06] tracking-[-0.04em] text-white">
              You see what to do, and why.
            </h3>
            <p className="mt-4 text-sm leading-7 text-slate-300">
              Sakhi frames what&apos;s happening, what your options are, and what
              patterns are repeating, so you can act clearly.
            </p>

            <div className="mt-4 rounded-[22px] bg-[#90a8ff]/[0.045] p-4">
              <div className="text-[10px] font-semibold uppercase tracking-[0.26em] text-[#c8d6ff]">
                Decision frame
              </div>
              <div className="mt-3 space-y-3">
                <div className="text-sm leading-6 text-slate-100">
                  You have said yes to similar urgent asks 4 times.
                </div>
                <div className="text-sm leading-6 text-slate-300">
                  The pattern is pressure, then agreement, then overload.
                </div>
              </div>
            </div>

            <div className="mt-4 space-y-2 text-sm">
              <div className="text-white/80">Options:</div>
              <ul className="ml-4 list-disc space-y-2 text-white/60">
                <li>Accept with revised timeline</li>
                <li>Push back on scope</li>
                <li>Decline</li>
              </ul>
            </div>

            <div className="mt-4 rounded-[18px] bg-white/5 px-4 py-3">
              <div className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
                Suggested move
              </div>
              <div className="mt-2 text-sm leading-6 text-slate-100">
                Propose a timeline instead of saying yes immediately.
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
