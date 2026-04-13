import type { Metadata } from "next";
import { CompanyDeckV1 } from "@/components/pitch/CompanyDeckV1";

export const metadata: Metadata = {
  title: "Sakhi — Company Deck v1 · Pre-Seed 2026",
  description: "Sakhi company deck v1. Pre-seed 2026.",
};

export default function CompanyDeckV1Page() {
  return <CompanyDeckV1 />;
}
