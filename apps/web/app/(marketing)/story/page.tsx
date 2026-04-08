import type { Metadata } from "next";
import StoryContainer from "@/components/story/StoryContainer";

export const metadata: Metadata = {
  title: "Sakhi — Story · Pre-Seed 2026",
  description: "Sakhi story. Pre-seed 2026.",
};

export default function StoryPage() {
  return <StoryContainer autoPlay />;
}
