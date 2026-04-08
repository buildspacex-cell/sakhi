import type { Metadata } from "next";
import SakhiOnePager from "@/components/pitch/SakhiOnePager";

export const metadata: Metadata = {
  title: "Sakhi — One Pager · Pre-Seed 2026",
  description: "Sakhi one pager. Pre-seed 2026.",
};

export default function OnePagerPage() {
  return <SakhiOnePager />;
}
