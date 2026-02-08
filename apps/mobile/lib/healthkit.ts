// =============================================================================
// HEALTHKIT SYNC SERVICE
// =============================================================================
// Reads health data from Apple HealthKit and syncs to the Sakhi backend.
// Data types: sleep, resting HR, HRV (SDNN), steps, active energy, mindful sessions.

import { Platform } from "react-native";
import * as SecureStore from "expo-secure-store";
import { config } from "./config";

// HealthKit is only available on iOS — guard all imports
let HK: typeof import("@kingstinct/react-native-healthkit") | null = null;

if (Platform.OS === "ios") {
  try {
    HK = require("@kingstinct/react-native-healthkit");
  } catch {
    // HealthKit not available (simulator without entitlement, etc.)
  }
}

// -----------------------------------------------------------------------------
// Types
// -----------------------------------------------------------------------------

export interface HealthDataRecord {
  type: string;
  data: Record<string, unknown>;
  recorded_at: string; // ISO 8601
}

interface SleepSample {
  startDate: string;
  endDate: string;
  value: string; // "InBed", "Asleep", "Deep", "REM", "Core", "Awake"
}

// -----------------------------------------------------------------------------
// Constants
// -----------------------------------------------------------------------------

const LAST_SYNC_KEY = "healthkit_last_sync";
const BATCH_SIZE = 50;
const DEFAULT_LOOKBACK_DAYS = 7;

// -----------------------------------------------------------------------------
// Availability & Authorization
// -----------------------------------------------------------------------------

export async function isHealthKitAvailable(): Promise<boolean> {
  if (Platform.OS !== "ios" || !HK) return false;
  try {
    return await HK.isHealthDataAvailable();
  } catch {
    return false;
  }
}

export async function requestHealthKitAuthorization(): Promise<boolean> {
  if (!HK) return false;
  try {
    const { HKQuantityTypeIdentifier, HKCategoryTypeIdentifier } = HK;
    await HK.requestAuthorization(
      [
        HKQuantityTypeIdentifier.heartRate,
        HKQuantityTypeIdentifier.restingHeartRate,
        HKQuantityTypeIdentifier.heartRateVariabilitySDNN,
        HKQuantityTypeIdentifier.stepCount,
        HKQuantityTypeIdentifier.activeEnergyBurned,
        HKCategoryTypeIdentifier.sleepAnalysis,
        HKCategoryTypeIdentifier.mindfulSession,
      ],
      [], // No write permissions needed
    );
    return true;
  } catch {
    return false;
  }
}

// -----------------------------------------------------------------------------
// Data Fetching
// -----------------------------------------------------------------------------

async function getLastSyncDate(): Promise<Date> {
  try {
    const stored = await SecureStore.getItemAsync(LAST_SYNC_KEY);
    if (stored) return new Date(stored);
  } catch {
    // ignore
  }
  const d = new Date();
  d.setDate(d.getDate() - DEFAULT_LOOKBACK_DAYS);
  return d;
}

async function setLastSyncDate(date: Date): Promise<void> {
  try {
    await SecureStore.setItemAsync(LAST_SYNC_KEY, date.toISOString());
  } catch {
    // ignore
  }
}

async function fetchSleepData(since: Date): Promise<HealthDataRecord[]> {
  if (!HK) return [];
  const { HKCategoryTypeIdentifier } = HK;

  const samples = (await HK.queryCategorySamples(
    HKCategoryTypeIdentifier.sleepAnalysis,
    { from: since, to: new Date() },
  )) as unknown as SleepSample[];

  if (!samples?.length) return [];

  // Group into sessions (30-min gap = new session)
  const sessions: SleepSample[][] = [];
  let current: SleepSample[] = [];

  const sorted = [...samples].sort(
    (a, b) => new Date(a.startDate).getTime() - new Date(b.startDate).getTime(),
  );

  for (const s of sorted) {
    if (current.length === 0) {
      current.push(s);
      continue;
    }
    const lastEnd = new Date(current[current.length - 1].endDate).getTime();
    const thisStart = new Date(s.startDate).getTime();
    if (thisStart - lastEnd > 30 * 60 * 1000) {
      sessions.push(current);
      current = [s];
    } else {
      current.push(s);
    }
  }
  if (current.length) sessions.push(current);

  return sessions.map((session) => {
    const start = new Date(session[0].startDate);
    const end = new Date(session[session.length - 1].endDate);
    const durationHours = (end.getTime() - start.getTime()) / (1000 * 60 * 60);

    const stages: Record<string, number> = {};
    for (const s of session) {
      const dur = (new Date(s.endDate).getTime() - new Date(s.startDate).getTime()) / (1000 * 60);
      const stage = (s.value || "unknown").toLowerCase();
      stages[stage] = (stages[stage] || 0) + dur;
    }

    return {
      type: "sleep",
      data: {
        start: start.toISOString(),
        end: end.toISOString(),
        duration_hours: Math.round(durationHours * 100) / 100,
        stages,
      },
      recorded_at: end.toISOString(),
    };
  });
}

async function fetchQuantitySamples(
  typeId: string,
  since: Date,
  recordType: string,
): Promise<HealthDataRecord[]> {
  if (!HK) return [];

  const samples = await HK.queryQuantitySamples(typeId as any, {
    from: since,
    to: new Date(),
  });

  return (samples || []).map((s: any) => ({
    type: recordType,
    data: { value: s.quantity },
    recorded_at: s.endDate || s.startDate || new Date().toISOString(),
  }));
}

async function fetchMindfulSessions(since: Date): Promise<HealthDataRecord[]> {
  if (!HK) return [];
  const { HKCategoryTypeIdentifier } = HK;

  const samples = (await HK.queryCategorySamples(
    HKCategoryTypeIdentifier.mindfulSession,
    { from: since, to: new Date() },
  )) as unknown as SleepSample[];

  return (samples || []).map((s) => {
    const start = new Date(s.startDate);
    const end = new Date(s.endDate);
    const durationMinutes = (end.getTime() - start.getTime()) / (1000 * 60);
    return {
      type: "mindful_session",
      data: { duration_minutes: Math.round(durationMinutes) },
      recorded_at: end.toISOString(),
    };
  });
}

// -----------------------------------------------------------------------------
// Sync to Backend
// -----------------------------------------------------------------------------

async function postBatch(
  personId: string,
  records: HealthDataRecord[],
): Promise<boolean> {
  try {
    const resp = await fetch(`${config.backendUrl}/health/sync/${personId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ records }),
    });
    return resp.ok;
  } catch {
    return false;
  }
}

// -----------------------------------------------------------------------------
// Main Sync
// -----------------------------------------------------------------------------

export async function syncHealthData(personId: string): Promise<{
  synced: number;
  error?: string;
}> {
  if (!HK || Platform.OS !== "ios") {
    return { synced: 0, error: "HealthKit not available" };
  }

  try {
    const since = await getLastSyncDate();
    const { HKQuantityTypeIdentifier } = HK;

    // Fetch all data types in parallel
    const [sleep, restingHR, hrv, steps, energy, mindful] = await Promise.all([
      fetchSleepData(since),
      fetchQuantitySamples(
        HKQuantityTypeIdentifier.restingHeartRate,
        since,
        "resting_heart_rate",
      ),
      fetchQuantitySamples(
        HKQuantityTypeIdentifier.heartRateVariabilitySDNN,
        since,
        "hrv_sdnn",
      ),
      fetchQuantitySamples(HKQuantityTypeIdentifier.stepCount, since, "steps"),
      fetchQuantitySamples(
        HKQuantityTypeIdentifier.activeEnergyBurned,
        since,
        "active_energy",
      ),
      fetchMindfulSessions(since),
    ]);

    const allRecords = [...sleep, ...restingHR, ...hrv, ...steps, ...energy, ...mindful];

    if (allRecords.length === 0) {
      return { synced: 0 };
    }

    // Send in batches
    let synced = 0;
    for (let i = 0; i < allRecords.length; i += BATCH_SIZE) {
      const batch = allRecords.slice(i, i + BATCH_SIZE);
      const ok = await postBatch(personId, batch);
      if (ok) {
        synced += batch.length;
      }
    }

    // Update last sync timestamp
    await setLastSyncDate(new Date());

    return { synced };
  } catch (e: any) {
    return { synced: 0, error: e?.message || "Sync failed" };
  }
}
