import * as SecureStore from "expo-secure-store";

const LEGACY_PERSON_ID_KEY = "sakhi_person_id";
const PERSON_ID_KEY_PREFIX = "sakhi_person_id:";

function getPersonIdKey(supabaseUserId: string): string {
  return `${PERSON_ID_KEY_PREFIX}${supabaseUserId}`;
}

export async function readCachedPersonId(supabaseUserId: string): Promise<string | undefined> {
  try {
    const cached = await SecureStore.getItemAsync(getPersonIdKey(supabaseUserId));
    return cached || undefined;
  } catch {
    return undefined;
  }
}

export async function writeCachedPersonId(
  supabaseUserId: string,
  personId: string,
): Promise<void> {
  try {
    await SecureStore.setItemAsync(getPersonIdKey(supabaseUserId), personId);
  } catch {
    // Best-effort cache only.
  }
}

export async function clearLegacyPersonIdCache(): Promise<void> {
  try {
    await SecureStore.deleteItemAsync(LEGACY_PERSON_ID_KEY);
  } catch {
    // Best-effort cleanup only.
  }
}
