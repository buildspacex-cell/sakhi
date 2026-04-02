import type { Metadata } from "next";
import { CompanyDeck } from "@/components/pitch/CompanyDeck";

export const metadata: Metadata = {
  title: "Sakhi — Company Deck",
  description: "Sakhi pre-seed investor deck.",
};

export default function CompanyDeckPage() {
  return <CompanyDeck />;
}
