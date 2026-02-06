// Soul View Model utilities for mobile app

export interface TimelineEntry {
  conflict?: number;
  friction?: number;
  date?: string;
  [key: string]: unknown;
}

export interface SoulState {
  prakruti?: {
    vata?: number;
    pitta?: number;
    kapha?: number;
  };
  vikriti?: {
    vata?: number;
    pitta?: number;
    kapha?: number;
  };
  dominant_dosha?: string;
  dominant_friction?: string;
  values?: string[];
  shadow_traits?: string[];
  light_traits?: string[];
  [key: string]: unknown;
}

export interface NormalizedSoulState {
  prakruti: { vata: number; pitta: number; kapha: number };
  vikriti: { vata: number; pitta: number; kapha: number };
  dominantDosha: string;
  dominantFriction: string;
  values: string[];
  shadowTraits: string[];
  lightTraits: string[];
}

/**
 * Transform timeline data into series with conflict/friction values
 */
export function timelineSeries(timeline: TimelineEntry[]): TimelineEntry[] {
  return timeline.map((entry) => ({
    conflict: entry.conflict || 0,
    friction: entry.friction || 0,
    date: entry.date,
  }));
}

/**
 * Normalize raw soul state data into a consistent shape
 */
export function normalizeSoulState(state: SoulState | null): NormalizedSoulState {
  const defaultDosha = { vata: 0.33, pitta: 0.33, kapha: 0.34 };

  return {
    prakruti: state?.prakruti || defaultDosha,
    vikriti: state?.vikriti || defaultDosha,
    dominantDosha: state?.dominant_dosha || "balanced",
    dominantFriction: state?.dominant_friction || "none",
    values: state?.values || [],
    shadowTraits: state?.shadow_traits || [],
    lightTraits: state?.light_traits || [],
  };
}

export interface SoulSummary {
  coherence?: number;
  friction?: string;
  shadow?: string[];
  light?: string[];
  [key: string]: unknown;
}

/**
 * Create a summary object from soul state and raw summary data
 */
export function summarizeSoul(
  state: NormalizedSoulState | SoulState | null,
  rawSummary?: SoulSummary | null
): SoulSummary {
  return {
    coherence: rawSummary?.coherence ?? 0.5,
    friction: rawSummary?.friction || (state as SoulState)?.dominant_friction || "none",
    shadow: rawSummary?.shadow || (state as SoulState)?.shadow_traits || [],
    light: rawSummary?.light || (state as SoulState)?.light_traits || [],
  };
}
