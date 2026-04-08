import type { Metadata } from "next";
import { CompanyDeck } from "@/components/pitch/CompanyDeck";

export const metadata: Metadata = {
  title: "Sakhi — Company Deck · Pre-Seed 2026",
  description: "Sakhi company deck. Pre-seed 2026.",
};

export default function CompanyDeckPage() {
  return <CompanyDeck />;
}
