// =============================================================================
// useHealthKit — React hook for HealthKit integration
// =============================================================================
// Manages HealthKit availability, authorization, and auto-sync on foreground.

import { useState, useEffect, useCallback, useRef } from "react";
import { AppState, AppStateStatus, Platform } from "react-native";
import {
  isHealthKitAvailable,
  requestHealthKitAuthorization,
  syncHealthData,
} from "../lib/healthkit";

export interface UseHealthKitReturn {
  /** Whether HealthKit is available on this device */
  available: boolean;
  /** Whether the user has authorized HealthKit access */
  authorized: boolean;
  /** Whether a sync is in progress */
  syncing: boolean;
  /** ISO timestamp of last successful sync */
  lastSync: string | null;
  /** Number of records synced in last sync */
  lastSyncCount: number;
  /** Error from last operation */
  error: string | null;
  /** Request authorization and perform initial sync */
  connect: () => Promise<boolean>;
  /** Trigger a manual sync */
  sync: () => Promise<void>;
}

export function useHealthKit(personId: string | undefined): UseHealthKitReturn {
  const [available, setAvailable] = useState(false);
  const [authorized, setAuthorized] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [lastSync, setLastSync] = useState<string | null>(null);
  const [lastSyncCount, setLastSyncCount] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const syncingRef = useRef(false);

  // Check availability on mount
  useEffect(() => {
    if (Platform.OS !== "ios") return;
    isHealthKitAvailable().then(setAvailable);
  }, []);

  // Sync function
  const sync = useCallback(async () => {
    if (!personId || !available || syncingRef.current) return;
    syncingRef.current = true;
    setSyncing(true);
    setError(null);

    try {
      const result = await syncHealthData(personId);
      if (result.error) {
        setError(result.error);
      } else {
        setLastSync(new Date().toISOString());
        setLastSyncCount(result.synced);
      }
    } catch (e: any) {
      setError(e?.message || "Sync failed");
    } finally {
      setSyncing(false);
      syncingRef.current = false;
    }
  }, [personId, available]);

  // Connect: request auth then sync
  const connect = useCallback(async (): Promise<boolean> => {
    if (!available) return false;
    setError(null);

    const granted = await requestHealthKitAuthorization();
    setAuthorized(granted);

    if (granted && personId) {
      await sync();
    }

    return granted;
  }, [available, personId, sync]);

  // Auto-sync on app foreground
  useEffect(() => {
    if (!authorized || !personId || Platform.OS !== "ios") return;

    const handleAppState = (state: AppStateStatus) => {
      if (state === "active") {
        sync();
      }
    };

    const sub = AppState.addEventListener("change", handleAppState);
    return () => sub.remove();
  }, [authorized, personId, sync]);

  return {
    available,
    authorized,
    syncing,
    lastSync,
    lastSyncCount,
    error,
    connect,
    sync,
  };
}
