import type { Metadata } from "next";
import SakhiOnePager from "@/components/pitch/SakhiOnePager";

export const metadata: Metadata = {
  title: "Sakhi — One Pager",
  description: "Sakhi pre-seed one pager.",
};

export default function OnePagerPage() {
  return <SakhiOnePager />;
}
