import { config } from "../config";
import { writeCachedPersonId } from "./personCache";

export interface MobileAuthBootstrapPayload {
  email?: string;
  full_name?: string;
  avatar_url?: string;
}

export interface MobileAuthBootstrapResponse {
  person_id: string;
  email: string;
  full_name?: string | null;
  avatar_url?: string | null;
  is_new_user: boolean;
  needs_name: boolean;
}

export async function bootstrapMobileAuthProfile(
  authToken: string,
  payload: MobileAuthBootstrapPayload,
  options?: { supabaseUserId?: string },
): Promise<MobileAuthBootstrapResponse> {
  const response = await fetch(`${config.backendUrl}/onboarding/mobile/bootstrap`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${authToken}`,
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(detail || `Bootstrap failed (${response.status})`);
  }

  const profile = (await response.json()) as MobileAuthBootstrapResponse;
  if (profile.person_id && options?.supabaseUserId) {
    void writeCachedPersonId(options.supabaseUserId, profile.person_id).catch(() => {});
  }
  return profile;
}
