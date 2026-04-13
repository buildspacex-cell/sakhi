import type { Metadata } from "next";
import SakhiOnePagerV1 from "@/components/pitch/SakhiOnePagerV1";

export const metadata: Metadata = {
  title: "Sakhi — One Pager v1 · Pre-Seed 2026",
  description: "Sakhi one pager. Pre-seed 2026.",
};

export default function OnePagerV1Page() {
  return <SakhiOnePagerV1 />;
}
