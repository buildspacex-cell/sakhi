import type { Metadata } from "next";
import SakhiOnePager from "@/components/pitch/SakhiOnePager";

export const metadata: Metadata = {
  title: "Sakhi — Base Investor Version · One Pager",
  description: "Sakhi base investor version one pager.",
};

export default function OnePagerPage() {
  return <SakhiOnePager />;
}
