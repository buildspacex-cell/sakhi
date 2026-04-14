import AsyncStorage from "@react-native-async-storage/async-storage";
import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { AppState } from "react-native";

import { useAuth } from "../auth/AuthContext";
import { config } from "../config";

export type OffloadSyncStatus =
  | "saved"
  | "saved_offline"
  | "syncing"
  | "synced"
  | "needs_retry";

export interface OffloadItem {
  clientId: string;
  personId: string;
  text: string;
  createdAt: string;
  syncStatus: OffloadSyncStatus;
  retryCount: number;
  entryId?: string;
  syncedAt?: string;
}

type ConnectivityState = "checking" | "online" | "offline";

type OffloadContextValue = {
  items: OffloadItem[];
  isReady: boolean;
  isSyncing: boolean;
  connectivity: ConnectivityState;
  pendingCount: number;
  saveOffload: (text: string) => Promise<OffloadItem | null>;
  syncPending: () => Promise<void>;
  refreshConnectivity: () => Promise<boolean>;
};

const STORAGE_KEY_PREFIX = "sakhi.mobile.offload.v1";
const BACKEND_URL = (config.backendUrl || "").replace(/\/+$/, "");

const OffloadContext = createContext<OffloadContextValue | null>(null);

function getStorageKey(personId: string): string {
  return `${STORAGE_KEY_PREFIX}:${personId}`;
}

function makeClientId(): string {
  return `offload-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function classifySyncError(error: unknown): "offline" | "retry" {
  if (error instanceof Error) {
    if (error.name === "AbortError") return "offline";
    if (error.message.startsWith("offline:")) return "offline";
  }
  return "retry";
}

async function checkBackendReachable(): Promise<boolean> {
  if (!BACKEND_URL) return false;

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 2500);
  try {
    const response = await fetch(`${BACKEND_URL}/health/live`, {
      method: "GET",
      signal: controller.signal,
    });
    return response.ok;
  } catch {
    return false;
  } finally {
    clearTimeout(timeout);
  }
}

export function OffloadProvider({ children }: { children: React.ReactNode }) {
  const { user, session } = useAuth();
  const personId = String(user?.personId || "").trim();
  const authToken = String(session?.access_token || "").trim();
  const storageKey = personId ? getStorageKey(personId) : "";

  const [items, setItems] = useState<OffloadItem[]>([]);
  const [isReady, setIsReady] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [connectivity, setConnectivity] = useState<ConnectivityState>("checking");

  const itemsRef = useRef<OffloadItem[]>([]);
  const syncingRef = useRef(false);

  useEffect(() => {
    itemsRef.current = items;
  }, [items]);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      if (!storageKey) {
        if (!cancelled) {
          setItems([]);
          setIsReady(true);
        }
        return;
      }

      setIsReady(false);
      try {
        const raw = await AsyncStorage.getItem(storageKey);
        if (cancelled) return;
        if (!raw) {
          setItems([]);
          return;
        }
        const parsed = JSON.parse(raw) as OffloadItem[];
        setItems(Array.isArray(parsed) ? parsed : []);
      } catch {
        if (!cancelled) {
          setItems([]);
        }
      } finally {
        if (!cancelled) {
          setIsReady(true);
        }
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, [storageKey]);

  useEffect(() => {
    if (!storageKey || !isReady) return;
    void AsyncStorage.setItem(storageKey, JSON.stringify(items)).catch(() => {});
  }, [isReady, items, storageKey]);

  const refreshConnectivity = useCallback(async (): Promise<boolean> => {
    setConnectivity((current) => (current === "checking" ? current : "checking"));
    const online = await checkBackendReachable();
    setConnectivity(online ? "online" : "offline");
    return online;
  }, []);

  const submitRemoteOffload = useCallback(
    async (item: OffloadItem): Promise<{ entryId?: string }> => {
      if (!personId || !authToken || !BACKEND_URL) {
        throw new Error("offline:missing_context");
      }

      const response = await fetch(`${BACKEND_URL}/v2/turn?user=${encodeURIComponent(personId)}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify({
          text: item.text,
          capture_only: true,
          source: "offload",
          ts: item.createdAt,
          client_id: item.clientId,
        }),
      });

      if (!response.ok) {
        throw new Error(`http:${response.status}`);
      }

      const payload = (await response.json()) as { entry_id?: string };
      return { entryId: payload.entry_id };
    },
    [authToken, personId],
  );

  const syncPending = useCallback(async () => {
    if (!isReady || !personId || !authToken || !BACKEND_URL || syncingRef.current) {
      return;
    }

    const candidates = itemsRef.current.filter((item) => (
      item.personId === personId
      && (item.syncStatus === "saved_offline" || item.syncStatus === "needs_retry")
    ));
    if (candidates.length === 0) {
      return;
    }

    syncingRef.current = true;
    setIsSyncing(true);

    try {
      const online = await checkBackendReachable();
      setConnectivity(online ? "online" : "offline");
      if (!online) return;

      for (const candidate of candidates) {
        setItems((current) => current.map((item) => (
          item.clientId === candidate.clientId
            ? { ...item, syncStatus: "syncing" }
            : item
        )));

        try {
          const result = await submitRemoteOffload(candidate);
          setItems((current) => current.map((item) => (
            item.clientId === candidate.clientId
              ? {
                  ...item,
                  entryId: result.entryId || item.entryId,
                  syncStatus: "synced",
                  syncedAt: new Date().toISOString(),
                }
              : item
          )));
        } catch (error) {
          const kind = classifySyncError(error);
          if (kind === "offline") {
            setConnectivity("offline");
            setItems((current) => current.map((item) => (
              item.clientId === candidate.clientId
                ? {
                    ...item,
                    retryCount: item.retryCount + 1,
                    syncStatus: "saved_offline",
                  }
                : item
            )));
            break;
          }

          setItems((current) => current.map((item) => (
            item.clientId === candidate.clientId
              ? {
                  ...item,
                  retryCount: item.retryCount + 1,
                  syncStatus: "needs_retry",
                }
              : item
          )));
        }
      }
    } finally {
      syncingRef.current = false;
      setIsSyncing(false);
    }
  }, [authToken, isReady, personId, submitRemoteOffload]);

  useEffect(() => {
    if (!personId || !authToken || !BACKEND_URL) {
      setConnectivity("offline");
      return;
    }
    void refreshConnectivity().then((online) => {
      if (online) {
        void syncPending();
      }
    });
  }, [authToken, personId, refreshConnectivity, syncPending]);

  useEffect(() => {
    const subscription = AppState.addEventListener("change", (state) => {
      if (state !== "active") return;
      void refreshConnectivity().then((online) => {
        if (online) {
          void syncPending();
        }
      });
    });
    return () => subscription.remove();
  }, [refreshConnectivity, syncPending]);

  const pendingCount = useMemo(
    () => items.filter((item) => item.syncStatus === "saved_offline" || item.syncStatus === "needs_retry").length,
    [items],
  );

  useEffect(() => {
    if (pendingCount === 0) return;
    const interval = setInterval(() => {
      void syncPending();
    }, 15000);
    return () => clearInterval(interval);
  }, [pendingCount, syncPending]);

  const saveOffload = useCallback(async (text: string): Promise<OffloadItem | null> => {
    const trimmed = text.trim();
    if (!trimmed || !personId) return null;

    const now = new Date().toISOString();
    const baseItem: OffloadItem = {
      clientId: makeClientId(),
      personId,
      text: trimmed,
      createdAt: now,
      retryCount: 0,
      syncStatus: "saved_offline",
    };

    const online = connectivity === "online" ? true : await checkBackendReachable();
    setConnectivity(online ? "online" : "offline");

    if (!online) {
      setItems((current) => [baseItem, ...current].slice(0, 100));
      return baseItem;
    }

    try {
      const result = await submitRemoteOffload(baseItem);
      const savedItem: OffloadItem = {
        ...baseItem,
        entryId: result.entryId,
        syncStatus: "saved",
        syncedAt: now,
      };
      setItems((current) => [savedItem, ...current].slice(0, 100));
      return savedItem;
    } catch (error) {
      const kind = classifySyncError(error);
      const fallback: OffloadItem = {
        ...baseItem,
        retryCount: kind === "retry" ? 1 : 0,
        syncStatus: kind === "offline" ? "saved_offline" : "needs_retry",
      };
      if (kind === "offline") {
        setConnectivity("offline");
      }
      setItems((current) => [fallback, ...current].slice(0, 100));
      return fallback;
    }
  }, [connectivity, personId, submitRemoteOffload]);

  const value = useMemo<OffloadContextValue>(() => ({
    items,
    isReady,
    isSyncing,
    connectivity,
    pendingCount,
    saveOffload,
    syncPending,
    refreshConnectivity,
  }), [connectivity, isReady, isSyncing, items, pendingCount, refreshConnectivity, saveOffload, syncPending]);

  return (
    <OffloadContext.Provider value={value}>
      {children}
    </OffloadContext.Provider>
  );
}

export function useOffload() {
  const context = useContext(OffloadContext);
  if (!context) {
    throw new Error("useOffload must be used within an OffloadProvider");
  }
  return context;
}
