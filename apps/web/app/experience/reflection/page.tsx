"use client";

import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import type React from "react";
import type { Route } from "next";

export const dynamic = "force-dynamic";

interface AuthUser {
  person_id: string;
  full_name: string | null;
  email: string;
}

interface ContinuityTopicSummary {
  anchor: string;
  label: string;
  confidence: number;
  selected_count: number;
  span_days: number;
  direction: string;
  surface?: {
    mirror_allowed?: boolean;
    detail_allowed?: boolean;
  };
}

interface ContinuityMoment {
  source_ref?: string;
  ts?: string;
  short_snippet?: string;
  confidence?: number;
  facet?: string;
  stance?: string;
}

interface ContinuityArcResponse {
  label?: string;
  topic_confidence?: number;
  surface?: {
    mirror_allowed?: boolean;
    detail_allowed?: boolean;
  };
  arc?: {
    element_count?: number;
    span_days?: number;
    phase_count?: number;
    features?: {
      direction?: string;
    };
  };
  included_moments?: ContinuityMoment[];
}

const palette = {
  bg: "#060a13",
  fg: "#f5f7fb",
  muted: "#a7b0c0",
  border: "rgba(231, 239, 255, 0.16)",
  glass: "rgba(20, 28, 40, 0.72)",
  card: "rgba(13, 21, 34, 0.92)",
  bubble: "rgba(255,255,255,0.08)",
  bubbleActive: "rgba(203, 233, 255, 0.25)",
  button: "rgba(74, 58, 36, 0.75)",
  buttonText: "#f5dcb2",
  warning: "#f3b4bc",
};

const REFLECT_POLL_INTERVAL_MS = 2000;
const REFLECT_POLL_MAX_ATTEMPTS = 70;
const MIN_TOPIC_STORY_MOMENTS = 3;  // <Topic> Story: matches backend min_len=3
const MIN_CROSS_CONTEXT_MOMENTS = 6;
const MIN_RELATED_TOPIC_MOMENTS = 6; // My Story: matches backend cross_context_min_moments=6
const MAX_CROSS_CONTEXT_TOPICS = 3;
const MOMENT_CARD_WIDTH = 246;
const MOMENT_CARD_GAP = 12;
const FLOW_CARD_WIDTH = 184;

type MomentDensity = "focus" | "flow" | "atlas";

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function toFiniteNumber(value: unknown, fallback = 0): number {
  const num = Number(value);
  return Number.isFinite(num) ? num : fallback;
}

function shortDate(input?: string): string {
  if (!input) return "";
  const parsed = new Date(input);
  if (Number.isNaN(parsed.getTime())) return "";
  return parsed.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function monthYearLabel(input?: string): string {
  if (!input) return "Undated";
  const parsed = new Date(input);
  if (Number.isNaN(parsed.getTime())) return "Undated";
  return parsed.toLocaleDateString(undefined, { month: "short", year: "numeric" });
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function formatTopicReflectionResult(payload: Record<string, unknown>): string {
  const result = (payload.result as Record<string, unknown> | undefined) || {};
  const chatResponse = String(result.chat_response || "").trim();
  if (chatResponse) {
    return chatResponse;
  }

  const originStory = String(result.origin_story || "").trim();
  const currentStage = String(result.current_stage || "").trim();
  const keyPivots = Array.isArray(result.key_pivots) ? result.key_pivots : [];
  const recurring = Array.isArray(result.recurring_tensions) ? result.recurring_tensions : [];

  return [
    originStory,
    typeof keyPivots[0] === "string" ? String(keyPivots[0]).trim() : "",
    currentStage,
    typeof recurring[0] === "string" ? String(recurring[0]).trim() : "",
  ]
    .filter((item) => item.length > 0)
    .join(" ");
}

function buildMomentObservation(moment: ContinuityMoment): string {
  const facet = String(moment.facet || "").trim().replace(/_/g, " ");
  const stance = String(moment.stance || "").trim().toLowerCase();

  if (facet) {
    return `Sakhi noticed this moment was tied to your ${facet} thread.`;
  }
  if (stance === "toward") {
    return "Sakhi noticed you were moving toward this direction.";
  }
  if (stance === "away") {
    return "Sakhi noticed a pull away from this direction.";
  }
  return "Sakhi noticed this added important context to your ongoing story.";
}

export default function ReflectionPage() {
  return (
    <Suspense fallback={<PageFallback />}>
      <ReflectionPageContent />
    </Suspense>
  );
}

function ReflectionPageContent() {
  const router = useRouter();
  const search = useSearchParams();

  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [authLoading, setAuthLoading] = useState(true);

  const [topics, setTopics] = useState<ContinuityTopicSummary[]>([]);
  const [selectedAnchor, setSelectedAnchor] = useState("");
  const [arc, setArc] = useState<ContinuityArcResponse | null>(null);
  const [loadingTopics, setLoadingTopics] = useState(false);
  const [loadingArc, setLoadingArc] = useState(false);
  const [error, setError] = useState("");

  const [threadOpen, setThreadOpen] = useState(false);
  const [selectedMoment, setSelectedMoment] = useState<ContinuityMoment | null>(null);
  const [momentOpening, setMomentOpening] = useState(false);

  const [deepReflectLoading, setDeepReflectLoading] = useState(false);
  const [deepReflectText, setDeepReflectText] = useState("");
  const [deepReflectError, setDeepReflectError] = useState("");

  const [meStoryLoading, setMeStoryLoading] = useState(false);
  const [meStoryText, setMeStoryText] = useState("");
  const [meStoryError, setMeStoryError] = useState("");

  const [activeMomentMonth, setActiveMomentMonth] = useState("Timeline");
  const momentLaneRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const loadAuth = async () => {
      try {
        const res = await fetch("/api/auth/me", { cache: "no-store" });
        if (res.ok) {
          const data = await res.json();
          setAuthUser({
            person_id: data.person_id,
            full_name: data.full_name,
            email: data.email,
          });
        }
      } catch (err) {
        console.error("Failed to load auth:", err);
      } finally {
        setAuthLoading(false);
      }
    };
    void loadAuth();
  }, []);

  const personId = useMemo(() => {
    const fromAuth = String(authUser?.person_id || "").trim();
    if (fromAuth) return fromAuth;
    return String(search?.get("user") || "").trim();
  }, [authUser?.person_id, search]);

  const pollTopicReflection = useCallback(async (reflectionId: string, person: string): Promise<string | null> => {
    const fetchResult = async (): Promise<string | null> => {
      const params = new URLSearchParams({
        id: reflectionId,
        person_id: person,
        t: String(Date.now()),
      });
      const resultRes = await fetch(`/api/continuity/reflection/result?${params.toString()}`, {
        cache: "no-store",
      });
      if (!resultRes.ok) return null;
      const resultData = (await resultRes.json()) as Record<string, unknown>;
      if (String(resultData.status || "queued") !== "done") return null;
      return formatTopicReflectionResult(resultData);
    };

    for (let attempt = 0; attempt < REFLECT_POLL_MAX_ATTEMPTS; attempt += 1) {
      try {
        const statusParams = new URLSearchParams({
          id: reflectionId,
          person_id: person,
          t: String(Date.now()),
        });
        const statusRes = await fetch(`/api/continuity/reflection/status?${statusParams.toString()}`, {
          cache: "no-store",
        });
        if (!statusRes.ok) break;
        const statusData = (await statusRes.json()) as Record<string, unknown>;
        const status = String(statusData.status || "queued");

        if (status === "done") {
          return await fetchResult();
        }
        if (status === "failed") {
          return null;
        }

        if (attempt % 3 === 0) {
          const optimistic = await fetchResult();
          if (optimistic) return optimistic;
        }
      } catch {
        break;
      }
      await sleep(REFLECT_POLL_INTERVAL_MS);
    }

    try {
      return await fetchResult();
    } catch {
      return null;
    }
  }, []);

  const loadArc = useCallback(async (anchor: string) => {
    if (!personId || !anchor) return;
    setLoadingArc(true);
    setSelectedMoment(null);
    setDeepReflectText("");
    setDeepReflectError("");
    try {
      const params = new URLSearchParams({ person_id: personId, anchor, window: "3650d" });
      const res = await fetch(`/api/continuity/arc?${params.toString()}`, { cache: "no-store" });
      if (!res.ok) {
        throw new Error(`Arc fetch failed (${res.status})`);
      }
      const payload = (await res.json()) as ContinuityArcResponse;
      setArc(payload);
    } catch (err) {
      console.error("[topic-reflection] arc load error", err);
      setArc(null);
    } finally {
      setLoadingArc(false);
    }
  }, [personId]);

  const fetchTopics = useCallback(async (): Promise<ContinuityTopicSummary[]> => {
    if (!personId) return [];
    const params = new URLSearchParams({ person_id: personId, window: "3650d" });
    const res = await fetch(`/api/continuity/topics?${params.toString()}`, {
      cache: "no-store",
    });
    if (!res.ok) {
      const errorState = new Error(`Topics fetch failed (${res.status})`) as Error & { status?: number };
      errorState.status = res.status;
      throw errorState;
    }
    const payload = (await res.json()) as { topics?: ContinuityTopicSummary[] };
    return payload.topics || [];
  }, [personId]);

  const ensureContinuityPolicyEnabled = useCallback(async (): Promise<boolean> => {
    if (!personId) return false;
    try {
      const res = await fetch(`/api/continuity/policy/enable`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ person_id: personId }),
      });
      return res.ok;
    } catch {
      return false;
    }
  }, [personId]);

  const loadTopics = useCallback(async () => {
    if (!personId) return;
    setLoadingTopics(true);
    setError("");
    setMeStoryError("");
    setMeStoryText("");

    try {
      let topicItems: ContinuityTopicSummary[] = [];
      try {
        topicItems = await fetchTopics();
      } catch (err) {
        const status = Number((err as { status?: number })?.status || 0);
        if (status === 403) {
          const enabled = await ensureContinuityPolicyEnabled();
          if (enabled) {
            topicItems = await fetchTopics();
          } else {
            throw err;
          }
        } else {
          throw err;
        }
      }

      const sorted = [...topicItems].sort((a, b) => {
        if (b.selected_count !== a.selected_count) {
          return b.selected_count - a.selected_count;
        }
        return b.confidence - a.confidence;
      });

      setTopics(sorted);
      if (sorted.length > 0) {
        const initialAnchor = sorted[0].anchor;
        setSelectedAnchor(initialAnchor);
        await loadArc(initialAnchor);
      } else {
        setSelectedAnchor("");
        setArc(null);
      }
    } catch (err) {
      console.error("[topic-reflection] topics load error", err);
      setTopics([]);
      setSelectedAnchor("");
      setArc(null);
      setError("Could not load continuity topics yet. Try sending a few chat turns first.");
    } finally {
      setLoadingTopics(false);
    }
  }, [ensureContinuityPolicyEnabled, fetchTopics, loadArc, personId]);

  useEffect(() => {
    if (!personId) return;
    void loadTopics();
  }, [loadTopics, personId]);

  const openThread = useCallback((anchor: string) => {
    setSelectedAnchor(anchor);
    setThreadOpen(true);
    void loadArc(anchor);
  }, [loadArc]);

  const openMoment = useCallback((moment: ContinuityMoment) => {
    setMomentOpening(true);
    setSelectedMoment(moment);
    window.setTimeout(() => setMomentOpening(false), 220);
  }, []);

  const totalTopicWeight = useMemo(
    () => topics.reduce((sum, topic) => sum + Math.max(0, topic.selected_count), 0),
    [topics],
  );

  const selectedTopic = useMemo(
    () => topics.find((topic) => topic.anchor === selectedAnchor) || null,
    [selectedAnchor, topics],
  );

  const moments = useMemo(
    () =>
      [...(arc?.included_moments || [])].sort((a, b) => {
        const aTs = new Date(String(a.ts || "")).getTime();
        const bTs = new Date(String(b.ts || "")).getTime();
        return aTs - bTs;
      }),
    [arc?.included_moments],
  );

  const depthMomentCount = useMemo(() => {
    const topicCount = toFiniteNumber(selectedTopic?.selected_count, 0);
    const arcCount = toFiniteNumber(arc?.arc?.element_count, 0);
    const includedCount = moments.length;
    return Math.max(topicCount, arcCount, includedCount);
  }, [arc?.arc?.element_count, moments.length, selectedTopic?.selected_count]);

  const momentDensity = useMemo<MomentDensity>(() => {
    if (depthMomentCount <= 8) return "focus";
    if (depthMomentCount <= 24) return "flow";
    return "atlas";
  }, [depthMomentCount]);

  const horizontalCardWidth = momentDensity === "flow" ? FLOW_CARD_WIDTH : MOMENT_CARD_WIDTH;
  const horizontalSnapInterval = horizontalCardWidth + MOMENT_CARD_GAP;

  const monthGroups = useMemo(() => {
    const groups: { month: string; items: ContinuityMoment[] }[] = [];
    for (const moment of moments) {
      const month = monthYearLabel(moment.ts);
      const last = groups[groups.length - 1];
      if (!last || last.month !== month) {
        groups.push({ month, items: [moment] });
      } else {
        last.items.push(moment);
      }
    }
    return groups;
  }, [moments]);

  const updateActiveMonthFromOffset = useCallback((offsetX: number) => {
    if (momentDensity === "atlas" || moments.length === 0) return;
    const rawIndex = Math.round(offsetX / Math.max(horizontalSnapInterval, 1));
    const index = clamp(rawIndex, 0, moments.length - 1);
    const nextMonth = monthYearLabel(moments[index]?.ts);
    setActiveMomentMonth((previous) => (previous === nextMonth ? previous : nextMonth));
  }, [horizontalSnapInterval, momentDensity, moments]);

  useEffect(() => {
    if (momentDensity === "atlas") {
      setActiveMomentMonth(monthGroups[0]?.month || "Timeline");
      return;
    }
    setActiveMomentMonth(monthYearLabel(moments[0]?.ts));
  }, [momentDensity, monthGroups, moments]);

  const topicStoryReady = useMemo(() => depthMomentCount >= MIN_TOPIC_STORY_MOMENTS, [depthMomentCount]);

  const myStoryEligibleTopics = useMemo(
    () =>
      topics.filter((topic) => {
        const mirrorAllowed = topic.surface?.mirror_allowed;
        if (mirrorAllowed === false) {
          return false;
        }
        return toFiniteNumber(topic.selected_count, 0) >= MIN_RELATED_TOPIC_MOMENTS;
      }),
    [topics],
  );

  const selectedAnchorEligibleForMyStory = useMemo(
    () =>
      myStoryEligibleTopics.some(
        (topic) =>
          topic.anchor === selectedAnchor
          && toFiniteNumber(topic.selected_count, 0) >= MIN_CROSS_CONTEXT_MOMENTS,
      ),
    [myStoryEligibleTopics, selectedAnchor],
  );

  const myStoryTopicKeys = useMemo(() => {
    if (!selectedAnchorEligibleForMyStory || !selectedAnchor) return [];
    const related = myStoryEligibleTopics
      .map((topic) => topic.anchor)
      .filter((anchor) => anchor && anchor !== selectedAnchor);
    return [selectedAnchor, ...related].slice(0, MAX_CROSS_CONTEXT_TOPICS);
  }, [myStoryEligibleTopics, selectedAnchor, selectedAnchorEligibleForMyStory]);

  const myStoryReady = selectedAnchorEligibleForMyStory && myStoryTopicKeys.length >= 2;

  const myStoryUnlockHint = (() => {
    const selectedLabel = selectedTopic?.label || selectedAnchor || "This thread";
    if (!selectedAnchorEligibleForMyStory) {
      return `${selectedLabel} needs more depth before My Story can anchor here.`;
    }
    if (myStoryTopicKeys.length < 2) {
      return "My Story unlocks after one more topic appears.";
    }
    return "";
  })();

  const runDeepReflect = useCallback(async () => {
    if (!personId || !selectedAnchor || deepReflectLoading) return;
    setDeepReflectLoading(true);
    setDeepReflectError("");

    try {
      const res = await fetch(`/api/continuity/reflection/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          person_id: personId,
          topic_key: selectedAnchor,
          window: "3650d",
          mode: "topic_reflection",
        }),
      });
      if (!res.ok) {
        throw new Error(`Topic story request failed (${res.status})`);
      }

      const data = (await res.json()) as Record<string, unknown>;
      const reflectionId = String(data.reflection_id || "");
      if (!reflectionId) {
        throw new Error("Topic story response missing reflection id");
      }

      const story = await pollTopicReflection(reflectionId, personId);
      if (story) {
        setDeepReflectText(story);
      } else {
        setDeepReflectError("Whole-story summary did not complete this time. Please try again.");
      }
    } catch (err) {
      console.error("run topic story failed", err);
      setDeepReflectError("Could not summarize this story right now.");
    } finally {
      setDeepReflectLoading(false);
    }
  }, [deepReflectLoading, personId, pollTopicReflection, selectedAnchor]);

  const runMeStory = useCallback(async () => {
    if (!personId || meStoryLoading || myStoryTopicKeys.length < 2) return;

    const primaryTopic = myStoryTopicKeys[0];
    setMeStoryLoading(true);
    setMeStoryError("");
    setMeStoryText("");

    try {
      const res = await fetch(`/api/continuity/reflection/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          person_id: personId,
          topic_key: primaryTopic,
          topic_keys: myStoryTopicKeys,
          window: "3650d",
          mode: "cross_context",
        }),
      });

      if (!res.ok) {
        throw new Error(`My Story request failed (${res.status})`);
      }

      const data = (await res.json()) as Record<string, unknown>;
      const reflectionId = String(data.reflection_id || "");
      if (!reflectionId) {
        throw new Error("My Story response missing reflection id");
      }

      const storyText = await pollTopicReflection(reflectionId, personId);
      if (storyText) {
        setMeStoryText(storyText);
      } else {
        setMeStoryError("My Story did not complete this time. Please try again.");
      }
    } catch (err) {
      console.error("run me story failed", err);
      setMeStoryError("Could not build My Story right now.");
    } finally {
      setMeStoryLoading(false);
    }
  }, [meStoryLoading, myStoryTopicKeys, personId, pollTopicReflection]);

  const threadLabel = selectedTopic?.label || arc?.label || selectedAnchor || "Thread";
  const threadLoadingText = deepReflectLoading
    ? "Building story..."
    : loadingArc
      ? "Loading moments..."
      : "Opening moment...";

  const backTarget = `/experience/converse${personId ? `?user=${encodeURIComponent(personId)}` : ""}`;

  if (authLoading) {
    return (
      <div style={{ ...styles.container, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <p style={{ color: palette.muted }}>Loading...</p>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.auroraA} />
      <div style={styles.auroraB} />

      <header style={styles.header}>
        <button style={styles.iconButton} onClick={() => router.push(backTarget as Route)}>
          ←
        </button>
        <div style={{ textAlign: "center" }}>
          <div style={styles.kicker}>Profile</div>
          <div style={styles.title}>Reflection</div>
        </div>
        <button style={styles.iconButton} onClick={() => void loadTopics()}>↻</button>
      </header>

      <main style={styles.content}>
        <section style={styles.glassCard}>
          <h2 style={styles.cardTitle}>Life Occupancy</h2>
          <p style={styles.cardSubtitle}>Bubble size reflects how much each thread has occupied your attention.</p>

          {loadingTopics ? (
            <div style={styles.loadingRow}>Loading topics...</div>
          ) : topics.length === 0 ? (
            <p style={styles.emptyText}>No topic arcs yet. Add more conversation turns and return here.</p>
          ) : (
            <div style={styles.topicCloud}>
              {topics.map((topic, index) => {
                const weight = totalTopicWeight > 0 ? topic.selected_count / totalTopicWeight : 0;
                const diameter = Math.round(clamp(88 + weight * 180 + topic.confidence * 16, 92, 196));
                const isActive = topic.anchor === selectedAnchor;
                return (
                  <button
                    key={`${topic.anchor}-${index}`}
                    style={{
                      ...styles.topicBubble,
                      ...(isActive ? styles.topicBubbleActive : {}),
                      width: diameter,
                      height: diameter,
                      background: isActive
                        ? palette.bubbleActive
                        : `rgba(255,255,255, ${0.07 + weight * 0.18})`,
                    }}
                    onClick={() => openThread(topic.anchor)}
                  >
                    <div style={styles.topicLabel}>{topic.label || topic.anchor}</div>
                    <div style={styles.topicShare}>{Math.max(1, Math.round(weight * 100))}%</div>
                    <div style={styles.topicCount}>{topic.selected_count} moments</div>
                  </button>
                );
              })}
            </div>
          )}

          {error ? <p style={styles.errorText}>{error}</p> : null}
        </section>

        <section style={styles.glassCard}>
          <h2 style={styles.cardTitle}>My Story</h2>
          <p style={styles.cardSubtitle}>Cross-context reflection across your active topics.</p>

          <div style={styles.storyActionBlock}>
            <button
              style={{
                ...styles.deepButton,
                ...((!myStoryReady || meStoryLoading || loadingTopics) ? styles.deepButtonDisabled : {}),
              }}
              onClick={() => void runMeStory()}
              disabled={!myStoryReady || meStoryLoading || loadingTopics}
            >
              {meStoryLoading ? "Building My Story..." : "My Story"}
            </button>
            {!myStoryReady ? <p style={styles.depthHint}>{myStoryUnlockHint}</p> : null}
          </div>

          {meStoryError ? <p style={styles.errorText}>{meStoryError}</p> : null}
          {meStoryText ? <p style={styles.deepReflectText}>{meStoryText}</p> : null}
        </section>
      </main>

      {threadOpen ? (
        <div style={styles.threadOverlay}>
          <div style={styles.threadScreen}>
            <header style={styles.header}>
              <button style={styles.iconButton} onClick={() => setThreadOpen(false)}>←</button>
              <div style={{ textAlign: "center" }}>
                <div style={styles.kicker}>Reflection</div>
                <div style={styles.title}>{threadLabel}</div>
              </div>
              <button style={styles.iconButton} onClick={() => void loadArc(selectedAnchor)}>↻</button>
            </header>

            <div style={styles.content}>
              <section style={styles.glassCard}>
                <div style={styles.arcHeader}>
                  <div>
                    <h2 style={styles.cardTitle}>Moments</h2>
                    <p style={styles.cardSubtitle}>Tap a moment to open the full snapshot.</p>
                  </div>
                  {loadingArc ? <div style={styles.inlineSpinner}>• • •</div> : null}
                </div>

                {!loadingArc && moments.length === 0 ? (
                  <p style={styles.emptyText}>No moments yet for this thread.</p>
                ) : (
                  <>
                    <div style={styles.momentLaneHeader}>
                      <div style={styles.monthReflectorPill}>
                        <span style={styles.monthReflectorText}>
                          {momentDensity === "atlas" ? "Timeline by month" : activeMomentMonth}
                        </span>
                      </div>
                      <span style={styles.momentLaneHint}>
                        {momentDensity === "atlas" ? "Scroll memories" : "Swipe memories"}
                      </span>
                    </div>

                    {momentDensity === "atlas" ? (
                      <div style={styles.atlasList}>
                        {monthGroups.map((group, groupIndex) => (
                          <div key={`month-group-${group.month}-${groupIndex}`} style={styles.monthBlock}>
                            <div style={styles.monthStickyWrap}>
                              <span style={styles.monthStickyText}>{group.month}</span>
                            </div>
                            <div style={styles.photoGrid}>
                              {group.items.map((moment, itemIndex) => {
                                const snippet = String(moment.short_snippet || "Moment").trim();
                                return (
                                  <button
                                    key={`${group.month}-${moment.source_ref || "moment"}-${itemIndex}`}
                                    style={styles.photoCard}
                                    onClick={() => openMoment(moment)}
                                  >
                                    <span style={styles.photoDate}>{shortDate(moment.ts) || "Undated"}</span>
                                    <span style={styles.photoText}>{snippet}</span>
                                  </button>
                                );
                              })}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div
                        ref={momentLaneRef}
                        style={styles.momentRow}
                        onScroll={(event) => {
                          const target = event.currentTarget;
                          updateActiveMonthFromOffset(target.scrollLeft);
                        }}
                      >
                        {moments.map((moment, index) => {
                          const snippet = String(moment.short_snippet || "Moment").trim();
                          return (
                            <button
                              key={`${moment.source_ref || "moment"}-${index}`}
                              style={{
                                ...styles.momentCard,
                                ...(momentDensity === "flow" ? styles.momentCardFlow : {}),
                                width: horizontalCardWidth,
                              }}
                              onClick={() => openMoment(moment)}
                            >
                              <div style={styles.momentHeaderRow}>
                                <span style={styles.momentIndex}>Moment {index + 1}</span>
                                <span style={styles.momentDatePill}>{shortDate(moment.ts) || "Undated"}</span>
                              </div>
                              <div style={styles.momentTextLeft}>{snippet}</div>
                              <div style={styles.momentMetaRow}>
                                <span style={styles.momentMetaLeft}>
                                  {(moment.facet || moment.stance || "thread").toString().replace(/_/g, " ")}
                                </span>
                                <span style={{ color: "#cfe1ff" }}>⤢</span>
                              </div>
                            </button>
                          );
                        })}
                      </div>
                    )}
                  </>
                )}
              </section>

              <section style={styles.glassCard}>
                <button
                  style={{
                    ...styles.deepButton,
                    ...((!topicStoryReady || deepReflectLoading) ? styles.deepButtonDisabled : {}),
                  }}
                  onClick={() => void runDeepReflect()}
                  disabled={!topicStoryReady || deepReflectLoading}
                >
                  {deepReflectLoading ? "Building Story..." : `${threadLabel} Story`}
                </button>
                {!topicStoryReady ? (
                  <p style={styles.depthHint}>{`${threadLabel} needs more depth for a story...`}</p>
                ) : null}
                {deepReflectError ? <p style={styles.errorText}>{deepReflectError}</p> : null}
                {deepReflectText ? <p style={styles.deepReflectText}>{deepReflectText}</p> : null}
              </section>
            </div>

            {(loadingArc || momentOpening || deepReflectLoading) ? (
              <div style={styles.threadLoadingOverlay}>
                <div style={styles.loadingSpinner}>⏳</div>
                <div style={styles.threadLoadingText}>{threadLoadingText}</div>
              </div>
            ) : null}
          </div>
        </div>
      ) : null}

      {selectedMoment ? (
        <div style={styles.momentModalBackdrop}>
          <div style={styles.momentModalCard}>
            <h3 style={styles.cardTitle}>{shortDate(selectedMoment.ts) || "Moment"}</h3>
            {momentOpening ? (
              <div style={styles.momentLoadingRow}>
                <span style={styles.loadingSpinner}>⏳</span>
                <span style={styles.momentLoadingText}>Opening moment...</span>
              </div>
            ) : (
              <>
                <p style={styles.momentDetailText}>
                  {String(selectedMoment.short_snippet || "").trim() || "No details available for this moment yet."}
                </p>
                <p style={styles.momentDetailMeta}>
                  Tag: {String(selectedMoment.facet || selectedMoment.stance || "thread").replace(/_/g, " ")}
                </p>
                <p style={styles.momentObservation}>{buildMomentObservation(selectedMoment)}</p>
              </>
            )}
            <button style={styles.momentClose} onClick={() => setSelectedMoment(null)}>
              Close
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function PageFallback() {
  return (
    <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", background: palette.bg, color: palette.muted }}>
      Loading...
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: "100vh",
    background: palette.bg,
    color: palette.fg,
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, sans-serif',
    position: "relative",
  },
  auroraA: {
    position: "absolute",
    top: -90,
    left: -70,
    width: 260,
    height: 260,
    borderRadius: "50%",
    background: "rgba(120, 210, 239, 0.16)",
    pointerEvents: "none",
  },
  auroraB: {
    position: "absolute",
    bottom: 120,
    right: -80,
    width: 220,
    height: 220,
    borderRadius: "50%",
    background: "rgba(255, 192, 128, 0.14)",
    pointerEvents: "none",
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "12px 16px",
    borderBottom: `1px solid ${palette.border}`,
    position: "relative",
    zIndex: 2,
  },
  iconButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    display: "grid",
    placeItems: "center",
    border: `1px solid ${palette.border}`,
    background: "rgba(255,255,255,0.08)",
    color: palette.fg,
    cursor: "pointer",
  },
  kicker: {
    color: palette.muted,
    fontSize: 11,
    letterSpacing: "0.11em",
    textTransform: "uppercase",
  },
  title: {
    color: palette.fg,
    fontSize: 28,
    fontWeight: 600,
  },
  content: {
    padding: "14px",
    display: "grid",
    gap: "12px",
    position: "relative",
    zIndex: 1,
  },
  glassCard: {
    borderRadius: 24,
    border: `1px solid ${palette.border}`,
    background: palette.glass,
    padding: 14,
    boxShadow: "0 8px 18px rgba(0,0,0,0.25)",
  },
  cardTitle: {
    margin: 0,
    color: palette.fg,
    fontSize: 28,
    fontWeight: 600,
  },
  cardSubtitle: {
    margin: "6px 0 0",
    color: palette.muted,
    fontSize: 15,
    lineHeight: 1.4,
  },
  loadingRow: {
    marginTop: 14,
    color: palette.muted,
  },
  emptyText: {
    marginTop: 12,
    color: palette.muted,
    fontSize: 15,
  },
  errorText: {
    marginTop: 12,
    color: palette.warning,
    fontSize: 14,
  },
  topicCloud: {
    marginTop: 14,
    display: "flex",
    flexWrap: "wrap",
    gap: 12,
    alignItems: "center",
  },
  topicBubble: {
    borderRadius: "50%",
    border: `1px solid rgba(226, 239, 255, 0.28)`,
    color: palette.fg,
    display: "grid",
    placeItems: "center",
    textAlign: "center",
    cursor: "pointer",
    padding: 8,
    lineHeight: 1.2,
  },
  topicBubbleActive: {
    borderColor: "rgba(197, 230, 255, 0.62)",
    boxShadow: "0 0 0 1px rgba(197,230,255,0.2)",
  },
  topicLabel: {
    fontSize: 18,
    fontWeight: 600,
    marginBottom: 4,
  },
  topicShare: {
    fontSize: 38,
    fontWeight: 700,
    color: "#d4edf8",
    marginBottom: 2,
  },
  topicCount: {
    fontSize: 14,
    color: palette.muted,
  },
  storyActionBlock: {
    marginTop: 14,
    display: "grid",
    gap: 8,
  },
  deepButton: {
    borderRadius: 999,
    border: `1px solid rgba(215, 175, 118, 0.6)`,
    background: palette.button,
    color: palette.buttonText,
    padding: "13px 18px",
    fontSize: 30,
    fontWeight: 600,
    cursor: "pointer",
  },
  deepButtonDisabled: {
    opacity: 0.58,
    cursor: "default",
  },
  depthHint: {
    margin: "2px 0 0",
    color: palette.muted,
    fontSize: 14,
  },
  deepReflectText: {
    marginTop: 14,
    color: palette.fg,
    fontSize: 16,
    lineHeight: 1.6,
    whiteSpace: "pre-wrap",
  },
  threadOverlay: {
    position: "fixed",
    inset: 0,
    background: palette.bg,
    zIndex: 20,
    overflow: "auto",
  },
  threadScreen: {
    minHeight: "100vh",
    position: "relative",
    background: palette.bg,
  },
  arcHeader: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 10,
  },
  inlineSpinner: {
    color: palette.muted,
    letterSpacing: 2,
  },
  momentLaneHeader: {
    marginTop: 14,
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 10,
  },
  monthReflectorPill: {
    borderRadius: 999,
    border: `1px solid rgba(181, 201, 237, 0.35)`,
    background: "rgba(69, 84, 112, 0.45)",
    padding: "7px 12px",
  },
  monthReflectorText: {
    color: "#cfd8ea",
    textTransform: "uppercase",
    letterSpacing: "0.08em",
    fontSize: 12,
    fontWeight: 600,
  },
  momentLaneHint: {
    color: palette.muted,
    fontSize: 14,
  },
  momentRow: {
    marginTop: 14,
    display: "flex",
    gap: `${MOMENT_CARD_GAP}px`,
    overflowX: "auto",
    paddingBottom: 4,
    scrollbarWidth: "thin",
  },
  momentCard: {
    borderRadius: 18,
    border: `1px solid rgba(186, 208, 244, 0.25)`,
    background: "rgba(34, 45, 65, 0.92)",
    color: palette.fg,
    padding: 12,
    textAlign: "left",
    cursor: "pointer",
    display: "grid",
    gap: 10,
    flexShrink: 0,
  },
  momentCardFlow: {
    minHeight: 190,
  },
  momentHeaderRow: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 8,
  },
  momentIndex: {
    color: "#cad5ea",
    fontSize: 13,
    textTransform: "uppercase",
    letterSpacing: "0.08em",
  },
  momentDatePill: {
    borderRadius: 999,
    border: `1px solid rgba(177, 200, 233, 0.35)`,
    padding: "3px 8px",
    fontSize: 12,
    color: "#d7e4fb",
  },
  momentTextLeft: {
    fontSize: 15,
    lineHeight: 1.45,
    color: palette.fg,
  },
  momentMetaRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: 8,
  },
  momentMetaLeft: {
    color: palette.muted,
    fontSize: 13,
    textTransform: "capitalize",
  },
  atlasList: {
    marginTop: 14,
    display: "grid",
    gap: 18,
  },
  monthBlock: {
    display: "grid",
    gap: 10,
  },
  monthStickyWrap: {
    position: "sticky",
    top: 0,
    zIndex: 1,
  },
  monthStickyText: {
    fontSize: 13,
    color: "#d7e4fb",
    textTransform: "uppercase",
    letterSpacing: "0.09em",
    fontWeight: 600,
  },
  photoGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
    gap: 10,
  },
  photoCard: {
    borderRadius: 16,
    border: `1px solid rgba(185, 207, 239, 0.24)`,
    background: "rgba(35, 45, 66, 0.9)",
    textAlign: "left",
    color: palette.fg,
    padding: 12,
    cursor: "pointer",
    display: "grid",
    gap: 8,
  },
  photoDate: {
    color: "#d8e6ff",
    fontSize: 12,
    textTransform: "uppercase",
    letterSpacing: "0.08em",
  },
  photoText: {
    color: palette.fg,
    fontSize: 14,
    lineHeight: 1.45,
  },
  threadLoadingOverlay: {
    position: "fixed",
    inset: 0,
    background: "rgba(6, 10, 19, 0.62)",
    display: "grid",
    placeItems: "center",
    gap: 10,
    zIndex: 25,
  },
  loadingSpinner: {
    fontSize: 22,
  },
  threadLoadingText: {
    color: "#f5dcb2",
    fontSize: 18,
  },
  momentModalBackdrop: {
    position: "fixed",
    inset: 0,
    background: "rgba(6, 10, 19, 0.72)",
    display: "grid",
    placeItems: "center",
    zIndex: 30,
    padding: 16,
  },
  momentModalCard: {
    width: "min(640px, 100%)",
    borderRadius: 20,
    border: `1px solid ${palette.border}`,
    background: palette.card,
    padding: 16,
    boxShadow: "0 14px 30px rgba(0,0,0,0.35)",
  },
  momentLoadingRow: {
    marginTop: 10,
    display: "flex",
    alignItems: "center",
    gap: 8,
  },
  momentLoadingText: {
    color: palette.muted,
    fontSize: 14,
  },
  momentDetailText: {
    marginTop: 10,
    color: palette.fg,
    fontSize: 16,
    lineHeight: 1.55,
  },
  momentDetailMeta: {
    marginTop: 10,
    color: palette.muted,
    fontSize: 14,
    textTransform: "capitalize",
  },
  momentObservation: {
    marginTop: 10,
    color: "#d5e8fa",
    fontSize: 14,
    lineHeight: 1.45,
  },
  momentClose: {
    marginTop: 14,
    borderRadius: 999,
    border: `1px solid ${palette.border}`,
    background: "rgba(255,255,255,0.06)",
    color: palette.fg,
    padding: "10px 16px",
    cursor: "pointer",
  },
};
