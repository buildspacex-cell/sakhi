import type { NextRequest } from "next/server";

export const DEFAULT_LOCALHOST_BYPASS_IDENTIFIER =
  "1df54e91-d585-475a-b375-c0a4221588db";

function isDevelopmentRuntime(): boolean {
  return process.env.NODE_ENV === "development";
}

function readConfiguredIdentifier(): string | null {
  if (!isDevelopmentRuntime()) {
    return null;
  }

  // Explicit env var always wins (including explicit disable via empty string).
  // The value may be either the canonical person_id or the Supabase user id.
  if (Object.prototype.hasOwnProperty.call(process.env, "DEV_AUTH_BYPASS_PERSON_ID")) {
    const explicitIdentifier = process.env.DEV_AUTH_BYPASS_PERSON_ID?.trim();
    return explicitIdentifier || null;
  }

  // Keep a deterministic default for local development unless explicitly disabled.
  return process.env.NODE_ENV === "development"
    ? DEFAULT_LOCALHOST_BYPASS_IDENTIFIER
    : null;
}

function isLocalHostname(hostname: string): boolean {
  const normalized = hostname.toLowerCase();
  return (
    normalized === "localhost" ||
    normalized === "127.0.0.1" ||
    normalized === "::1" ||
    normalized === "[::1]"
  );
}

export function getDevAuthBypassPersonId(): string | null {
  return readConfiguredIdentifier();
}

export function isDevAuthBypassEnabled(request: NextRequest): boolean {
  if (!isDevelopmentRuntime()) {
    return false;
  }

  const identifier = readConfiguredIdentifier();
  if (!identifier) {
    return false;
  }

  return isLocalHostname(request.nextUrl.hostname);
}
