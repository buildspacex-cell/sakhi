import type { ContextPack } from "@sakhi/contracts";

export type TonePreference = {
  style?: "warm" | "encouraging" | "focused" | "lowkey";
  pacing?: "slow" | "medium" | "fast";
  voice?: "calm" | "bright" | "steady" | "whisper";
};

export function extractTonePreference(context: ContextPack): TonePreference {
  const preferences = context.semantic_profile?.preferences ?? {};
  const raw = preferences["tone.preference"] ?? preferences["tone.style"];
  if (typeof raw === "string") {
    const normalized = raw.toLowerCase();
    if (normalized.includes("soft")) return { style: "warm", pacing: "slow", voice: "calm" };
    if (normalized.includes("hype")) return { style: "encouraging", pacing: "fast", voice: "bright" };
    if (normalized.includes("lowkey")) return { style: "lowkey", pacing: "slow", voice: "whisper" };
  }
  return {};
}
