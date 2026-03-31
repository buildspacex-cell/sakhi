import type { Metadata } from "next";
import { PitchLayout } from "@/components/pitch/PitchLayout";

export const metadata: Metadata = {
  title: "Sakhi — Investor Pitch",
  description:
    "The full Sakhi investor deck: story, product, GTM, roadmap, and team.",
};

export default function PitchPage() {
  return <PitchLayout />;
}
