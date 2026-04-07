import type { Metadata } from "next";
import FounderStoryContainer from "@/components/story/FounderStoryContainer";

export const metadata: Metadata = {
  title: "Sakhi — Founder Story",
  description: "The minds behind Sakhi.",
};

export default function FounderStoryPage() {
  return <FounderStoryContainer autoPlay />;
}
