import type { Metadata } from "next";
import StoryContainer from "@/components/story/StoryContainer";

export const metadata: Metadata = {
  title: "Sakhi — Base Investor Version · Story",
  description: "Sakhi base investor version story.",
};

export default function StoryPage() {
  return <StoryContainer autoPlay />;
}
