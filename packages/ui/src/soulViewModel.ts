export type SoulState = {
  core_values?: string[];
  longing?: string[];
  aversions?: string[];
  identity_themes?: string[];
  commitments?: string[];
  shadow?: string[];
  light?: string[];
  conflicts?: string[];
  friction?: string[];
  confidence?: number | null;
  updated_at?: string | null;
};

export type SoulSummary = {
  top_shadow?: string[];
  top_light?: string[];
  dominant_friction?: string | null;
  identity_instability_index?: number | null;
  coherence_score?: number | null;
};

export function normalizeSoulState(data: any): SoulState {
  const def = (v: any) => (Array.isArray(v) ? v : []);
  return {
    core_values: def(data?.core_values),
    longing: def(data?.longing),
    aversions: def(data?.aversions),
    identity_themes: def(data?.identity_themes),
    commitments: def(data?.commitments),
    shadow: def(data?.shadow),
    light: def(data?.light),
    conflicts: def(data?.conflicts),
    friction: def(data?.friction),
    confidence: typeof data?.confidence === "number" ? data.confidence : null,
    updated_at: data?.updated_at ?? null,
  };
}

export function computeCoherence(summary: SoulSummary): number {
  if (typeof summary?.coherence_score === "number") return summary.coherence_score;
  const shadowIntensity = (summary?.top_shadow?.length || 0) + 1;
  const lightIntensity = (summary?.top_light?.length || 0) + 1;
  return Math.max(0, Math.min(1, 1 - shadowIntensity / (lightIntensity + shadowIntensity)));
}

export function imbalanceScore(summary: SoulSummary): number {
  const shadowIntensity = (summary?.top_shadow?.length || 0);
  const lightIntensity = (summary?.top_light?.length || 0);
  const total = shadowIntensity + lightIntensity || 1;
  return Math.max(0, Math.min(1, Math.abs(shadowIntensity - lightIntensity) / total));
}

export function summarizeSoul(state: SoulState, summary: SoulSummary) {
  return {
    values: state.core_values || [],
    identity: state.identity_themes || [],
    shadow: summary.top_shadow || [],
    light: summary.top_light || [],
    friction: summary.dominant_friction || null,
    coherence: computeCoherence(summary),
  };
}

export function timelineSeries(timeline: any[]) {
  return (timeline || []).map((pt) => ({
    ts: pt?.ts || "",
    shadow: pt?.shadow?.length || 0,
    light: pt?.light?.length || 0,
    conflict: pt?.conflict?.length || 0,
    friction: pt?.friction?.length || 0,
  }));
}

export default {
  normalizeSoulState,
  computeCoherence,
  imbalanceScore,
  summarizeSoul,
  timelineSeries,
};
