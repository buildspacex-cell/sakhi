import AsyncStorage from "@react-native-async-storage/async-storage";

const STORAGE_KEY = "sakhi.auth.debug.v1";
const MAX_ENTRIES = 40;

export type AuthDebugLevel = "info" | "error";

export interface AuthDebugEntry {
  id: string;
  at: string;
  level: AuthDebugLevel;
  message: string;
  details?: Record<string, unknown>;
}

type Listener = (entries: AuthDebugEntry[]) => void;

let entries: AuthDebugEntry[] = [];
let hydrated = false;
let hydratePromise: Promise<void> | null = null;
const listeners = new Set<Listener>();

function emit() {
  const snapshot = [...entries];
  for (const listener of listeners) {
    listener(snapshot);
  }
}

async function persist() {
  try {
    await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
  } catch {
    // Best-effort only.
  }
}

async function hydrate() {
  if (hydrated) {
    return;
  }
  if (!hydratePromise) {
    hydratePromise = (async () => {
      try {
        const raw = await AsyncStorage.getItem(STORAGE_KEY);
        if (raw) {
          const parsed = JSON.parse(raw) as AuthDebugEntry[];
          if (Array.isArray(parsed)) {
            entries = parsed.slice(-MAX_ENTRIES);
          }
        }
      } catch {
        entries = [];
      } finally {
        hydrated = true;
        emit();
      }
    })();
  }
  await hydratePromise;
}

void hydrate();

export function getAuthDebugEntries(): AuthDebugEntry[] {
  return [...entries];
}

export function subscribeAuthDebug(listener: Listener): () => void {
  listeners.add(listener);
  void hydrate().finally(() => listener(getAuthDebugEntries()));
  return () => {
    listeners.delete(listener);
  };
}

export async function clearAuthDebug(): Promise<void> {
  entries = [];
  emit();
  try {
    await AsyncStorage.removeItem(STORAGE_KEY);
  } catch {
    // Best-effort only.
  }
}

export function formatAuthDebugEntries(source: AuthDebugEntry[]): string {
  return source
    .map((entry) => {
      const details = entry.details ? ` ${JSON.stringify(entry.details)}` : "";
      return `[${entry.at}] ${entry.level.toUpperCase()} ${entry.message}${details}`;
    })
    .join("\n");
}

export async function recordAuthDebug(
  message: string,
  details?: Record<string, unknown>,
  level: AuthDebugLevel = "info",
): Promise<void> {
  await hydrate();

  const entry: AuthDebugEntry = {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    at: new Date().toISOString(),
    level,
    message,
    details,
  };

  if (level === "error") {
    console.error("[auth]", message, details || {});
  } else {
    console.log("[auth]", message, details || {});
  }

  entries = [...entries, entry].slice(-MAX_ENTRIES);
  emit();
  await persist();
}
