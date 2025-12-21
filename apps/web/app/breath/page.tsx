"use client";

import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";

const inhaleDuration = 4;
const exhaleDuration = 7;

export default function BreathPractice() {
  const [phase, setPhase] = useState<"inhale" | "exhale">("inhale");
  const [counter, setCounter] = useState(inhaleDuration);
  const [recordedRates, setRecordedRates] = useState<number[]>([]);
  const phaseRef = useRef<"inhale" | "exhale">("inhale");

  useEffect(() => {
    const interval = setInterval(() => {
      setCounter((count) => {
        if (count > 1) return count - 1;
        const nextPhase = phaseRef.current === "inhale" ? "exhale" : "inhale";
        phaseRef.current = nextPhase;
        setPhase(nextPhase);
        setRecordedRates((rates) => [...rates, 60 / (inhaleDuration + exhaleDuration)]);
        return nextPhase === "inhale" ? inhaleDuration : exhaleDuration;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const finishSession = async () => {
    const totalDuration = Math.max(
      inhaleDuration + exhaleDuration,
      recordedRates.length * (inhaleDuration + exhaleDuration),
    );
    const payload = {
      person_id: "demo-user",
      duration_sec: totalDuration,
      rates: recordedRates,
      pattern: "equal",
    };
    try {
      await fetch("/api/breath/session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      alert("Session logged!");
    } catch {
      alert("Unable to log session right now.");
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-b from-rose-50 to-white space-y-6">
      <motion.div
        animate={{ scale: phase === "inhale" ? 1.3 : 0.9 }}
        transition={{ duration: 3 }}
        className="w-40 h-40 bg-rose-300 rounded-full shadow-inner"
      />
      <div className="text-rose-700 font-medium text-lg capitalize">
        {phase} — {counter}s
      </div>
      <Button onClick={finishSession}>Done</Button>
    </div>
  );
}
