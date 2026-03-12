/**
 * Typed analytics event callers.
 *
 * Rules enforced here:
 * - No free text (no message content, journal text, prompt text)
 * - No raw user input in any property value
 * - All callers go through trackEvent() — no raw posthog.capture() from screens
 */

import { trackEvent } from "./client";

export const Analytics = {
  // ─── Chat ────────────────────────────────────────────────────────────────

  /** User tapped send on a message. */
  messageSent: () =>
    trackEvent("message_sent"),

  /** API turn completed (success or non-2xx). */
  turnCompleted: (props: {
    latency_ms: number;
    status: number;
    request_id?: string;
    has_continuity: boolean;
  }) => trackEvent("turn_completed", props),

  /** API turn failed (network error, timeout, non-recoverable). */
  turnFailed: (props: {
    status: number;
    latency_ms: number;
    reason: "timeout" | "network" | "http_error" | "unknown";
    request_id?: string;
  }) => trackEvent("turn_failed", props),

  /** Deep Reflect / Whole Story button became visible to user. */
  deepButtonShown: (props: { mode: "whole_story" | "deep_reflect" }) =>
    trackEvent("deep_button_shown", props),

  /** User tapped the Deep Reflect / Whole Story button. */
  deepStarted: (props: { mode: "whole_story" | "deep_reflect" }) =>
    trackEvent("deep_started", props),

  /** Deep reflection completed and result displayed. */
  deepCompleted: (props: {
    mode: "whole_story" | "deep_reflect";
    latency_ms: number;
    request_id?: string;
  }) => trackEvent("deep_completed", props),

  // ─── Reflection ──────────────────────────────────────────────────────────

  /** User opened the topic reflection screen. */
  reflectionOpened: () =>
    trackEvent("reflection_opened"),

  /** User tapped a topic bubble to select it. */
  topicSelected: (props: { topic_key: string }) =>
    trackEvent("topic_selected", props),

  /** Topic story (single topic deep reflect) completed. */
  topicStoryCompleted: (props: { latency_ms: number; request_id?: string }) =>
    trackEvent("topic_story_completed", props),

  /** Me Story (cross-context) completed. */
  meStoryCompleted: (props: {
    topic_count: number;
    latency_ms: number;
    request_id?: string;
  }) => trackEvent("me_story_completed", props),

  // ─── Support ─────────────────────────────────────────────────────────────

  /** User submitted a support report. */
  supportReportCreated: (props: { diagnostics_enabled: boolean }) =>
    trackEvent("support_report_created", props),

  /** User started a live debug session. */
  supportDebugSessionStarted: () =>
    trackEvent("support_debug_session_started"),
};
