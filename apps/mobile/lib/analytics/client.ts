/**
 * Analytics client — thin wrapper over PostHog React Native.
 *
 * Usage:
 *   import { Analytics } from "@/lib/analytics/events";
 *   Analytics.messageSent();
 *
 * Never call posthog.capture() directly from screens.
 * Use the typed callers in events.ts.
 */

import PostHog from "posthog-react-native";
import { Platform } from "react-native";
import Constants from "expo-constants";

const POSTHOG_KEY = (process.env.EXPO_PUBLIC_POSTHOG_KEY || "").trim();
const POSTHOG_HOST = (process.env.EXPO_PUBLIC_POSTHOG_HOST || "https://us.i.posthog.com").trim();
// Set EXPO_PUBLIC_ANALYTICS_ENABLED=0 to hard-disable at build time (e.g. dev builds).
// PostHog dashboard pause acts as the live runtime kill switch in production.
const ANALYTICS_ENABLED = process.env.EXPO_PUBLIC_ANALYTICS_ENABLED !== "0";

export const posthog = new PostHog(POSTHOG_KEY || "noop", {
  host: POSTHOG_HOST,
  // Disabled if: no key set (dev without PostHog) OR analytics explicitly disabled.
  disabled: !POSTHOG_KEY || !ANALYTICS_ENABLED,
  flushAt: 10,
  flushInterval: 30000,
});

// ─── Session ID ──────────────────────────────────────────────────────────────
// One session_id per app-open. Reset on explicit sign-out via resetSessionId().

let _sessionId = _makeSessionId();

function _makeSessionId(): string {
  return `s_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}

export function getSessionId(): string {
  return _sessionId;
}

export function resetSessionId(): void {
  _sessionId = _makeSessionId();
}

// ─── Core ────────────────────────────────────────────────────────────────────

const _appVersion =
  Constants.expoConfig?.version ||
  (Constants.expoConfig?.ios as { buildNumber?: string } | undefined)?.buildNumber ||
  "unknown";

/**
 * Track a named event with standard envelope properties automatically merged.
 * Only call this from events.ts typed callers — never directly from screens.
 */
export function trackEvent(
  name: string,
  props?: Record<string, string | number | boolean | null | undefined>,
): void {
  posthog.capture(name, {
    schema_version: 1,
    session_id: _sessionId,
    platform: Platform.OS,
    app_version: _appVersion,
    ...props,
  });
}

// ─── Identity ────────────────────────────────────────────────────────────────

/** Call once after sign-in so events are tied to person_id in PostHog. */
export function identifyUser(personId: string): void {
  posthog.identify(personId);
}

/** Call on sign-out to detach identity and reset session. */
export function resetUser(): void {
  posthog.reset();
  resetSessionId();
}

// ─── Opt-out ─────────────────────────────────────────────────────────────────
// PostHog persists opt-out state internally via AsyncStorage.

export function optOutAnalytics(): void {
  posthog.optOutCapturing();
}

export function optInAnalytics(): void {
  posthog.optInCapturing();
}

export function isAnalyticsOptedOut(): boolean {
  return posthog.isOptedOutCapturing();
}
