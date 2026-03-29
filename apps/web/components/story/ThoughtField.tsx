"use client";

import { motion, useReducedMotion } from "framer-motion";

const fragments = [
  { text: "what if", left: "8%", top: "12%", delay: 0, duration: 11 },
  { text: "later tonight", left: "58%", top: "16%", delay: 0.8, duration: 13 },
  { text: "did I miss something", left: "20%", top: "30%", delay: 1.2, duration: 12 },
  { text: "call her back", left: "62%", top: "38%", delay: 0.4, duration: 10 },
  { text: "I should remember this", left: "14%", top: "56%", delay: 1.6, duration: 14 },
  { text: "why does this keep repeating", left: "42%", top: "66%", delay: 0.6, duration: 12 },
  { text: "tomorrow", left: "68%", top: "78%", delay: 1.4, duration: 11 },
  { text: "not now", left: "10%", top: "24%", delay: 0.9, duration: 9 },
  { text: "maybe later", left: "74%", top: "28%", delay: 1.8, duration: 12 },
  { text: "don't forget", left: "48%", top: "46%", delay: 0.2, duration: 10 },
  { text: "say something", left: "18%", top: "72%", delay: 1, duration: 13 },
  { text: "what am I missing", left: "54%", top: "84%", delay: 0.5, duration: 12 },
  { text: "again?", left: "34%", top: "18%", delay: 1.3, duration: 9 },
] as const;

const whisperFragments = [
  { text: "later", left: "28%", top: "10%", delay: 0.3, duration: 10 },
  { text: "respond", left: "80%", top: "46%", delay: 1.1, duration: 9 },
  { text: "why again", left: "24%", top: "42%", delay: 0.7, duration: 11 },
  { text: "not yet", left: "62%", top: "54%", delay: 1.5, duration: 10 },
  { text: "remember", left: "40%", top: "90%", delay: 0.4, duration: 12 },
  { text: "what now", left: "6%", top: "82%", delay: 1.7, duration: 11 },
] as const;

const nodes = [
  { left: "18%", top: "20%", delay: 0.1 },
  { left: "48%", top: "30%", delay: 0.6 },
  { left: "72%", top: "24%", delay: 0.9 },
  { left: "30%", top: "54%", delay: 0.4 },
  { left: "62%", top: "60%", delay: 1.1 },
  { left: "46%", top: "80%", delay: 0.7 },
] as const;

const threads = [
  { left: "18%", top: "22%", width: "34%", rotate: "12deg" },
  { left: "46%", top: "31%", width: "24%", rotate: "-10deg" },
  { left: "30%", top: "56%", width: "30%", rotate: "8deg" },
  { left: "43%", top: "74%", width: "18%", rotate: "-18deg" },
] as const;

const rings = [
  { left: "22%", top: "18%", size: "8rem", delay: 0.2 },
  { left: "58%", top: "44%", size: "10rem", delay: 1.2 },
  { left: "36%", top: "70%", size: "7rem", delay: 0.8 },
] as const;

export default function ThoughtField() {
  const reduceMotion = useReducedMotion();

  return (
    <div className="relative mx-auto aspect-[4/5] w-full max-w-[26rem] overflow-hidden rounded-[32px] bg-[radial-gradient(circle_at_20%_20%,rgba(95,118,180,0.14),transparent_34%),radial-gradient(circle_at_82%_18%,rgba(184,201,255,0.08),transparent_28%),linear-gradient(180deg,rgba(14,17,24,0.88),rgba(10,12,18,0.94))] shadow-[0_24px_80px_rgba(3,6,14,0.42)]">
      <div className="absolute inset-0 rounded-[32px] bg-[radial-gradient(circle_at_center,transparent_0%,transparent_58%,rgba(7,9,14,0.18)_84%,rgba(7,9,14,0.42)_100%)]" />
      <div className="absolute inset-0 rounded-[32px] ring-1 ring-inset ring-white/[0.035]" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,transparent_44%,rgba(7,9,14,0.32)_78%,rgba(7,9,14,0.72)_100%)]" />
      <div className="absolute inset-0 bg-[linear-gradient(180deg,transparent,rgba(8,10,16,0.32)_100%)]" />
      <div className="absolute inset-0 bg-[linear-gradient(135deg,rgba(255,255,255,0.04),transparent_22%,transparent_78%,rgba(255,255,255,0.03))]" />

      <motion.div
        animate={
          reduceMotion
            ? undefined
            : {
                opacity: [0.22, 0.34, 0.22],
              }
        }
        transition={{ duration: 8, repeat: Number.POSITIVE_INFINITY, ease: "easeInOut" }}
        className="absolute left-[14%] top-[14%] h-40 w-40 rounded-full bg-[#879eff]/10 blur-3xl"
      />
      <motion.div
        animate={
          reduceMotion
            ? undefined
            : {
                opacity: [0.08, 0.2, 0.08],
              }
        }
        transition={{ duration: 10, repeat: Number.POSITIVE_INFINITY, ease: "easeInOut", delay: 1.5 }}
        className="absolute right-[10%] top-[42%] h-48 w-48 rounded-full bg-white/6 blur-3xl"
      />

      {rings.map((ring) => (
        <motion.div
          key={`${ring.left}-${ring.top}`}
          animate={
            reduceMotion
              ? undefined
              : {
                  scale: [0.94, 1.04, 0.94],
                  opacity: [0.08, 0.22, 0.08],
                }
          }
          transition={{
            duration: 7.5,
            repeat: Number.POSITIVE_INFINITY,
            ease: "easeInOut",
            delay: ring.delay,
          }}
          className="absolute rounded-full border border-white/8"
          style={{
            left: ring.left,
            top: ring.top,
            width: ring.size,
            height: ring.size,
          }}
        />
      ))}

      {threads.map((thread) => (
        <div
          key={`${thread.left}-${thread.top}`}
          className="absolute h-px rounded-full bg-gradient-to-r from-transparent via-white/14 to-transparent"
          style={{
            left: thread.left,
            top: thread.top,
            width: thread.width,
            transform: `rotate(${thread.rotate})`,
            transformOrigin: "left center",
          }}
        />
      ))}

      {nodes.map((node) => (
        <motion.div
          key={`${node.left}-${node.top}`}
          animate={
            reduceMotion
              ? undefined
              : {
                  scale: [1, 1.35, 1],
                  opacity: [0.3, 0.85, 0.3],
                }
          }
          transition={{
            duration: 4.5,
            repeat: Number.POSITIVE_INFINITY,
            ease: "easeInOut",
            delay: node.delay,
          }}
          className="absolute h-2 w-2 rounded-full bg-[#d8e1ff]"
          style={{ left: node.left, top: node.top }}
        />
      ))}

      {fragments.map((fragment) => (
        <motion.div
          key={fragment.text}
          animate={
            reduceMotion
              ? undefined
              : {
                  x: [0, 6, -4, 0],
                  y: [0, -8, 5, 0],
                  opacity: [0.3, 0.78, 0.48, 0.3],
                }
          }
          transition={{
            duration: fragment.duration,
            repeat: Number.POSITIVE_INFINITY,
            ease: "easeInOut",
            delay: fragment.delay,
          }}
          className="absolute max-w-[11rem] text-[0.98rem] font-medium leading-[1.22] tracking-[-0.02em] text-slate-100/85 [text-shadow:0_0_18px_rgba(8,10,18,0.42)]"
          style={{ left: fragment.left, top: fragment.top }}
        >
          {fragment.text}
        </motion.div>
      ))}

      {whisperFragments.map((fragment) => (
        <motion.div
          key={fragment.text}
          animate={
            reduceMotion
              ? undefined
              : {
                  x: [0, 4, -3, 0],
                  y: [0, -5, 3, 0],
                  opacity: [0.1, 0.28, 0.14, 0.1],
                }
          }
          transition={{
            duration: fragment.duration,
            repeat: Number.POSITIVE_INFINITY,
            ease: "easeInOut",
            delay: fragment.delay,
          }}
          className="absolute max-w-[8rem] text-[0.78rem] font-medium leading-[1.2] tracking-[-0.015em] text-slate-300/48"
          style={{ left: fragment.left, top: fragment.top }}
        >
          {fragment.text}
        </motion.div>
      ))}

      <motion.div
        animate={
          reduceMotion
            ? undefined
            : {
                opacity: [0.05, 0.14, 0.05],
                x: ["-8%", "10%", "-8%"],
              }
        }
        transition={{ duration: 12, repeat: Number.POSITIVE_INFINITY, ease: "easeInOut" }}
        className="absolute inset-y-0 left-[-20%] w-[48%] bg-[linear-gradient(90deg,transparent,rgba(255,255,255,0.12),transparent)] blur-2xl"
      />

      <motion.div
        animate={
          reduceMotion
            ? undefined
            : {
                scale: [0.96, 1.02, 0.96],
                opacity: [0.18, 0.38, 0.18],
              }
        }
        transition={{ duration: 6, repeat: Number.POSITIVE_INFINITY, ease: "easeInOut", delay: 0.8 }}
        className="absolute left-1/2 top-1/2 h-28 w-28 -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/10 bg-white/[0.03] shadow-[0_0_80px_rgba(125,148,255,0.08)]"
      />
    </div>
  );
}
