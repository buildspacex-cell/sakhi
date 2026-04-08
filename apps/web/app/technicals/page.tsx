import type { Metadata } from "next";
import { TechnicalDeck } from "@/components/pitch/TechnicalDeck";

export const metadata: Metadata = {
  title: "Sakhi — Technical Architecture · Pre-Seed 2026",
  description: "Sakhi technical architecture briefing for investors.",
};

export default function TechnicalsPage() {
  return <TechnicalDeck />;
}
