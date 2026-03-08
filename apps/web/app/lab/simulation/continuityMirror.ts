import type { CompiledContinuityArc } from "./types";

export interface MirrorRecap {
  start: string;
  pivots: string;
  current: string;
}

type PhaseTag = {
  label: string;
  confidence: number;
};

type PhaseMode = "quiet" | "active" | "steady" | "back_and_forth";

type PhaseProfile = {
  index: number;
  durationDays: number;
  elementDensity: number;
  mode: PhaseMode;
  tag: PhaseTag | null;
};

function roundSpanDays(spanDays: number): number {
  return Math.max(1, Math.round(spanDays || 0));
}

function phaseLead(phaseCount: number): string {
  if (phaseCount <= 1) return "One continuous span";
  if (phaseCount === 2) return "Two phases";
  if (phaseCount === 3) return "Three phases";
  return `${phaseCount} phases`;
}

function pluralize(count: number, singular: string, plural: string): string {
  return count === 1 ? singular : plural;
}

function pivotCount(arc: CompiledContinuityArc): number {
  const explicit = arc.features?.change_points?.length ?? 0;
  if (explicit > 0) return explicit;
  const phaseCount = arc.phase_count || arc.phases.length || 0;
  return Math.max(0, phaseCount - 1);
}

function clampSentence(value: string, maxLength = 120): string {
  if (value.length <= maxLength) return value;
  const sliced = value.slice(0, maxLength - 1);
  const boundary = sliced.lastIndexOf(" ");
  return `${(boundary > 40 ? sliced.slice(0, boundary) : sliced).trimEnd()}.`;
}

function safeDaySpan(startTs: string, endTs: string): number {
  const startMs = new Date(startTs).getTime();
  const endMs = new Date(endTs).getTime();
  if (!Number.isFinite(startMs) || !Number.isFinite(endMs) || endMs < startMs) return 1;
  return Math.max(1, (endMs - startMs) / 86_400_000);
}

function extractPhaseTagValue(raw: unknown): PhaseTag | null {
  if (!raw) return null;
  if (typeof raw === "string") {
    return raw.trim() ? { label: raw.trim(), confidence: 1 } : null;
  }
  if (Array.isArray(raw)) {
    for (const item of raw) {
      const extracted = extractPhaseTagValue(item);
      if (extracted) return extracted;
    }
    return null;
  }
  if (typeof raw === "object") {
    const record = raw as Record<string, unknown>;
    const label = [record.label, record.name, record.tag, record.value].find(
      (value): value is string => typeof value === "string" && value.trim().length > 0,
    );
    if (!label) return null;
    const confidenceValue = [record.confidence, record.score].find(
      (value): value is number => typeof value === "number" && Number.isFinite(value),
    );
    return {
      label: label.trim(),
      confidence: confidenceValue ?? 1,
    };
  }
  return null;
}

function pickPhaseTag(stats: Record<string, any>): PhaseTag | null {
  const candidates = [
    stats.dominant_tag,
    stats.top_tag,
    stats.dominant_facet,
    stats.primary_facet,
    stats.top_tags,
    stats.tags,
  ];

  for (const candidate of candidates) {
    const extracted = extractPhaseTagValue(candidate);
    if (extracted && extracted.confidence >= 0.7) {
      return extracted;
    }
  }

  return null;
}

function classifyPhaseMode(
  density: number,
  averageDensity: number,
  oscillation: number | null,
): PhaseMode {
  if (oscillation != null && oscillation >= 0.5) return "back_and_forth";
  if (averageDensity <= 0) return "steady";
  if (density <= averageDensity * 0.75) return "quiet";
  if (density >= averageDensity * 1.35) return "active";
  return "steady";
}

function buildPhaseProfiles(arc: CompiledContinuityArc): PhaseProfile[] {
  const oscillation = arc.features?.oscillation ?? null;

  if (!arc.phases.length) {
    return [
      {
        index: 0,
        durationDays: Math.max(1, arc.span_days || 1),
        elementDensity: arc.element_count / Math.max(1, arc.span_days || 1),
        mode: oscillation != null && oscillation >= 0.5 ? "back_and_forth" : "steady",
        tag: null,
      },
    ];
  }

  const baseProfiles = arc.phases.map((phase) => {
    const durationDays = safeDaySpan(phase.start_ts, phase.end_ts);
    const elementDensity = phase.element_count / durationDays;
    return {
      index: phase.index,
      durationDays,
      elementDensity,
      tag: pickPhaseTag(phase.stats ?? {}),
    };
  });

  const averageDensity =
    baseProfiles.reduce((sum, phase) => sum + phase.elementDensity, 0) / Math.max(baseProfiles.length, 1);

  return baseProfiles.map((phase) => ({
    ...phase,
    mode: classifyPhaseMode(phase.elementDensity, averageDensity, oscillation),
  }));
}

function describeMode(mode: PhaseMode): string {
  switch (mode) {
    case "quiet":
      return "quiet and sparse";
    case "active":
      return "active and dense";
    case "back_and_forth":
      return "in visible back-and-forth";
    default:
      return "with a steady thread";
  }
}

function humanizeTag(label: string): string {
  return label.replace(/_/g, " ").trim();
}

export function makeMirrorTitle(topicLabel: string, arc: CompiledContinuityArc): string {
  return `${topicLabel} — One unfolding over ~${roundSpanDays(arc.span_days)} days`;
}

export function makeAnchorLine(arc: CompiledContinuityArc): string {
  const phaseCount = arc.phase_count || arc.phases.length || 0;
  const pivots = pivotCount(arc);
  const features = arc.features;

  let sentence = "";

  if (phaseCount <= 1) {
    sentence = "One continuous thread with steady continuity.";
  } else if (features?.oscillation != null && features.oscillation >= 0.5) {
    sentence =
      pivots > 0
        ? `Recurring return to the same theme, with ${pivots} visible ${pluralize(pivots, "pivot", "pivots")}.`
        : "Recurring return to the same theme, with visible back-and-forth.";
  } else if (features?.stability != null && features.stability >= 0.7) {
    if (pivots >= 2) {
      sentence = "The core thread stayed intact; focus reorganized twice.";
    } else if (pivots === 1) {
      sentence = "The core thread stayed intact; focus reorganized once.";
    } else {
      sentence = "The same thread held steady across the full span.";
    }
  } else if (pivots > 0) {
    sentence =
      pivots === 1
        ? "One continuous thread with one visible pivot."
        : `One continuous thread with ${pivots} visible pivots.`;
  } else if (features?.direction === "falling") {
    sentence = "The same thread held, with a gradual loosening later.";
  } else if (features?.direction === "rising") {
    sentence = "The same thread held, with consistency gathering over time.";
  } else {
    sentence = "The same thread held, with a gradual shift in emphasis.";
  }

  return clampSentence(sentence);
}

export function makeMirrorSummary(arc: CompiledContinuityArc): string {
  const phaseCount = arc.phase_count || arc.phases.length || 0;
  const lead = phaseLead(phaseCount);
  const pivots = pivotCount(arc);
  const features = arc.features;

  if (phaseCount <= 1) return `${lead}, holding as one thread.`;
  if (features?.oscillation != null && features.oscillation >= 0.5) {
    return `${lead}, with recurring back-and-forth still visible.`;
  }
  if (pivots > 1) {
    return `${lead}, with a few visible pivots reorganizing the thread.`;
  }
  if (pivots === 1) {
    return `${lead}, with one visible pivot reorganizing the thread.`;
  }
  if (features?.stability != null && features.stability >= 0.7) {
    return `${lead}, with a consistent thread across the span.`;
  }
  if (features?.direction === "rising") {
    return `${lead}, with consistency gathering over time.`;
  }
  if (features?.direction === "falling") {
    return `${lead}, with consistency loosening over time.`;
  }
  return `${lead}, with the thread holding together.`;
}

export function makeRecap(arc: CompiledContinuityArc): MirrorRecap {
  const profiles = buildPhaseProfiles(arc);
  const startProfile = profiles[0];
  const currentProfile = profiles[profiles.length - 1];
  const pivots = pivotCount(arc);

  const start = startProfile?.tag
    ? `Started around ${humanizeTag(startProfile.tag.label)}.`
    : `Started ${describeMode(startProfile?.mode ?? "steady")}.`;

  let pivotsLine = "";
  const nextTaggedPhase = profiles.slice(1).find((profile) => profile.tag);
  if (pivots <= 0) {
    pivotsLine = "No sharp pivots; the thread shifted gradually.";
  } else if (nextTaggedPhase?.tag) {
    const pivotLead =
      pivots === 1
        ? "Then pivoted toward"
        : `Then ${pivots} pivots shifted toward`;
    pivotsLine = `${pivotLead} ${humanizeTag(nextTaggedPhase.tag.label)}.`;
  } else {
    pivotsLine =
      pivots === 1
        ? "Then one pivot reorganized the thread."
        : `Then ${pivots} pivots reorganized the thread.`;
  }

  let current = "";
  if (currentProfile?.tag) {
    current = `Now centered on ${humanizeTag(currentProfile.tag.label)}.`;
  } else if (
    startProfile &&
    currentProfile &&
    startProfile.mode === "quiet" &&
    currentProfile.mode === "active"
  ) {
    current = "Now more dense and consistent.";
  } else if (
    startProfile &&
    currentProfile &&
    startProfile.mode === "active" &&
    currentProfile.mode === "quiet"
  ) {
    current = "Now quieter and more selective.";
  } else if (currentProfile?.mode === "back_and_forth") {
    current = "Now still in visible back-and-forth.";
  } else if (currentProfile?.mode === "active") {
    current = "Now active and more tightly grouped.";
  } else if (currentProfile?.mode === "quiet") {
    current = "Now quieter, with wider spacing.";
  } else {
    current = "Now holding a more consistent thread.";
  }

  return {
    start: clampSentence(start),
    pivots: clampSentence(pivotsLine),
    current: clampSentence(current),
  };
}
