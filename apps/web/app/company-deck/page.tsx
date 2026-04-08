import type { Metadata } from "next";
import { CompanyDeck } from "@/components/pitch/CompanyDeck";

export const metadata: Metadata = {
  title: "Sakhi — Base Investor Version · Company Deck",
  description: "Sakhi base investor version company deck.",
};

export default function CompanyDeckPage() {
  return <CompanyDeck />;
}
