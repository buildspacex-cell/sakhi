// =============================================================================
// HEALTHKIT SYNC SERVICE
// =============================================================================
// HealthKit is parked out of the current MVP runtime. These stubs preserve the
// existing import surface without pulling a half-validated native integration
// into the internal TestFlight build.

export interface HealthDataRecord {
  type: string;
  data: Record<string, unknown>;
  recorded_at: string; // ISO 8601
}

export async function isHealthKitAvailable(): Promise<boolean> {
  return false;
}

export async function requestHealthKitAuthorization(): Promise<boolean> {
  return false;
}

export async function syncHealthData(personId: string): Promise<{
  synced: number;
  error?: string;
}> {
  void personId;
  return { synced: 0, error: "HealthKit is parked for the current MVP build" };
}
