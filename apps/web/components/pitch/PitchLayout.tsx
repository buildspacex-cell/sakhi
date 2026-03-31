"use client";

import { PitchNav } from "@/components/pitch/PitchNav";
import { PitchHero } from "@/components/pitch/PitchHero";
import { PitchProblem } from "@/components/pitch/PitchProblem";
import { PitchSolution } from "@/components/pitch/PitchSolution";
import { PitchContinuity } from "@/components/pitch/PitchContinuity";
import { PitchProduct } from "@/components/pitch/PitchProduct";
import { PitchVision } from "@/components/pitch/PitchVision";
import { PitchFounderBridge } from "@/components/pitch/PitchFounderBridge";
import { PitchTeam } from "@/components/pitch/PitchTeam";
import { PitchAsk } from "@/components/pitch/PitchAsk";

export function PitchLayout() {
  return (
    <div className="relative bg-[#020617] text-white">
      <PitchNav />
      <PitchHero />
      <PitchProblem />
      <PitchSolution />
      <PitchContinuity />
      <PitchProduct />
      <PitchVision />
      <PitchFounderBridge />
      <PitchTeam />
      <PitchAsk />
    </div>
  );
}
