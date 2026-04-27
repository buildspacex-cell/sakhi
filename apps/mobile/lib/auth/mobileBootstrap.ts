import { config } from "../config";
import { writeCachedPersonId } from "./personCache";
import { recordAuthDebug } from "./authDebug";

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

function extractBootstrapErrorMessage(raw: string, status: number): string {
  const trimmed = raw.trim();
  if (!trimmed) {
    return `Bootstrap failed (${status})`;
  }

  try {
    const parsed = JSON.parse(trimmed) as { detail?: unknown; message?: unknown };
    if (typeof parsed.detail === "string" && parsed.detail.trim()) {
      return parsed.detail.trim();
    }
    if (typeof parsed.message === "string" && parsed.message.trim()) {
      return parsed.message.trim();
    }
  } catch {
    // Fall through to plain text.
  }

  return trimmed;
}

export async function bootstrapMobileAuthProfile(
  authToken: string,
  payload: MobileAuthBootstrapPayload,
  options?: { supabaseUserId?: string },
): Promise<MobileAuthBootstrapResponse> {
  await recordAuthDebug("Starting mobile bootstrap", {
    backendUrl: config.backendUrl,
    hasEmail: !!payload.email,
    hasFullName: !!payload.full_name,
    hasAvatarUrl: !!payload.avatar_url,
    hasSupabaseUserId: !!options?.supabaseUserId,
  });

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
    const message = extractBootstrapErrorMessage(detail, response.status);
    await recordAuthDebug("Mobile bootstrap failed", {
      status: response.status,
      detail: message,
    }, "error");
    throw new Error(message);
  }

  const profile = (await response.json()) as MobileAuthBootstrapResponse;
  await recordAuthDebug("Mobile bootstrap succeeded", {
    personId: profile.person_id,
    isNewUser: profile.is_new_user,
    needsName: profile.needs_name,
  });
  if (profile.person_id && options?.supabaseUserId) {
    void writeCachedPersonId(options.supabaseUserId, profile.person_id).catch(() => {});
  }
  return profile;
}
