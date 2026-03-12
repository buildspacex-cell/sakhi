import * as SecureStore from "expo-secure-store";

export type SupportDebugEventType = "screen_view" | "action" | "api_start" | "api_end" | "ui_error";

export interface SupportDebugSession {
  sessionId: string;
  supportCode: string;
  personId: string;
  status: string;
  startedAt?: string;
  lastEventAt?: string;
  stoppedAt?: string;
  expiresAt?: string;
  eventCount?: number;
}

export interface SupportDebugEventInput {
  type: SupportDebugEventType;
  name: string;
  screen?: string;
  route?: string;
  method?: string;
  status?: number;
  requestId?: string;
  latencyMs?: number;
  seq?: number;
  metadata?: Record<string, unknown>;
}

const STORAGE_KEY = "sakhi_support_debug_session_v1";
const MAX_METADATA_KEYS = 20;
const MAX_STRING_LEN = 180;

function toSession(payload: unknown): SupportDebugSession | null {
  if (!payload || typeof payload !== "object") return null;
  const row = payload as Record<string, unknown>;
  const sessionId = String(row.session_id || "").trim();
  const supportCode = String(row.support_code || "").trim();
  const personId = String(row.person_id || "").trim();
  if (!sessionId || !supportCode || !personId) return null;
  return {
    sessionId,
    supportCode,
    personId,
    status: String(row.status || "active"),
    startedAt: String(row.started_at || ""),
    lastEventAt: String(row.last_event_at || ""),
    stoppedAt: String(row.stopped_at || ""),
    expiresAt: String(row.expires_at || ""),
    eventCount: Number(row.event_count || 0),
  };
}

function isActive(session: SupportDebugSession | null): boolean {
  if (!session) return false;
  if (String(session.status || "").toLowerCase() !== "active") return false;
  const expiresAt = String(session.expiresAt || "").trim();
  if (!expiresAt) return true;
  const parsed = Date.parse(expiresAt);
  if (!Number.isFinite(parsed)) return true;
  return parsed > Date.now();
}

function sanitizeString(value: unknown, maxLen = MAX_STRING_LEN): string {
  return String(value || "").trim().slice(0, maxLen);
}

function sanitizeMetadata(input: Record<string, unknown> | undefined): Record<string, unknown> {
  if (!input || typeof input !== "object") return {};
  const out: Record<string, unknown> = {};
  Object.entries(input).slice(0, MAX_METADATA_KEYS).forEach(([key, value]) => {
    const cleanKey = sanitizeString(key, 48);
    if (!cleanKey) return;
    if (value === null || value === undefined) return;
    if (typeof value === "string") {
      out[cleanKey] = sanitizeString(value);
      return;
    }
    if (typeof value === "number" || typeof value === "boolean") {
      out[cleanKey] = value;
      return;
    }
    out[cleanKey] = sanitizeString(JSON.stringify(value));
  });
  return out;
}

async function readStoredSession(): Promise<SupportDebugSession | null> {
  try {
    const raw = await SecureStore.getItemAsync(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    const session = toSession(parsed);
    if (!isActive(session)) {
      await SecureStore.deleteItemAsync(STORAGE_KEY);
      return null;
    }
    return session;
  } catch {
    return null;
  }
}

async function writeStoredSession(session: SupportDebugSession): Promise<void> {
  await SecureStore.setItemAsync(
    STORAGE_KEY,
    JSON.stringify({
      session_id: session.sessionId,
      support_code: session.supportCode,
      person_id: session.personId,
      status: session.status,
      started_at: session.startedAt,
      last_event_at: session.lastEventAt,
      stopped_at: session.stoppedAt,
      expires_at: session.expiresAt,
      event_count: session.eventCount,
    }),
  );
}

export async function getActiveSupportDebugSession(): Promise<SupportDebugSession | null> {
  return readStoredSession();
}

export async function clearActiveSupportDebugSession(): Promise<void> {
  try {
    await SecureStore.deleteItemAsync(STORAGE_KEY);
  } catch {
    // noop
  }
}

export async function startSupportDebugSession(params: {
  backendUrl: string;
  authToken?: string;
  personId: string;
  supportCode: string;
  durationMinutes?: number;
  clientContext?: Record<string, unknown>;
}): Promise<SupportDebugSession> {
  const backend = params.backendUrl.replace(/\/+$/, "");
  const response = await fetch(`${backend}/support/session/start`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(params.authToken ? { Authorization: `Bearer ${params.authToken}` } : {}),
    },
    body: JSON.stringify({
      person_id: params.personId,
      support_code: params.supportCode,
      duration_minutes: params.durationMinutes,
      client_context: sanitizeMetadata(params.clientContext),
    }),
  });
  const payload = await response.json().catch(() => ({} as Record<string, unknown>));
  if (!response.ok) {
    const detail = typeof payload.detail === "string" ? payload.detail : "support_session_start_failed";
    throw new Error(detail);
  }
  const session = toSession({ ...(payload as Record<string, unknown>), person_id: params.personId });
  if (!session) throw new Error("support_session_start_invalid_payload");
  await writeStoredSession(session);
  return session;
}

export async function stopSupportDebugSession(params: {
  backendUrl: string;
  authToken?: string;
  personId: string;
  supportCode: string;
  sessionId: string;
}): Promise<SupportDebugSession | null> {
  const backend = params.backendUrl.replace(/\/+$/, "");
  const response = await fetch(`${backend}/support/session/stop`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(params.authToken ? { Authorization: `Bearer ${params.authToken}` } : {}),
    },
    body: JSON.stringify({
      person_id: params.personId,
      support_code: params.supportCode,
      session_id: params.sessionId,
    }),
  });
  const payload = await response.json().catch(() => ({} as Record<string, unknown>));
  if (!response.ok) {
    const detail = typeof payload.detail === "string" ? payload.detail : "support_session_stop_failed";
    if (response.status === 404 || response.status === 409) {
      await clearActiveSupportDebugSession();
    }
    throw new Error(detail);
  }
  const session = toSession({ ...(payload as Record<string, unknown>), person_id: params.personId });
  await clearActiveSupportDebugSession();
  return session;
}

export async function trackSupportDebugEvent(params: {
  backendUrl: string;
  authToken?: string;
  personId: string;
  event: SupportDebugEventInput;
}): Promise<boolean> {
  const session = await readStoredSession();
  if (!session || !isActive(session)) return false;
  if (session.personId !== params.personId) return false;

  const backend = params.backendUrl.replace(/\/+$/, "");
  const eventPayload = {
    type: params.event.type,
    name: sanitizeString(params.event.name, 80),
    ts: new Date().toISOString(),
    seq: params.event.seq,
    screen: sanitizeString(params.event.screen, 64) || undefined,
    route: sanitizeString(params.event.route, 140) || undefined,
    method: sanitizeString(params.event.method, 12) || undefined,
    status: params.event.status,
    request_id: sanitizeString(params.event.requestId, 120) || undefined,
    latency_ms: params.event.latencyMs,
    metadata: sanitizeMetadata(params.event.metadata),
  };

  try {
    const response = await fetch(`${backend}/support/session/event`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(params.authToken ? { Authorization: `Bearer ${params.authToken}` } : {}),
      },
      body: JSON.stringify({
        person_id: params.personId,
        support_code: session.supportCode,
        session_id: session.sessionId,
        events: [eventPayload],
      }),
    });
    const payload = await response.json().catch(() => ({} as Record<string, unknown>));
    if (!response.ok) {
      if (response.status === 404 || response.status === 409) {
        await clearActiveSupportDebugSession();
      }
      return false;
    }
    const sessionPayload = (payload as { session?: unknown }).session;
    const next = toSession({ ...(sessionPayload as Record<string, unknown>), person_id: params.personId });
    if (next && isActive(next)) {
      await writeStoredSession(next);
    }
    return true;
  } catch {
    return false;
  }
}
