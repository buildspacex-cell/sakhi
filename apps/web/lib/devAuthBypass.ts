import type { NextRequest } from "next/server";

export const DEFAULT_LOCALHOST_BYPASS_PERSON_ID =
  "a1b2c3d4-1111-4000-8000-000000000001";

function isDevelopmentRuntime(): boolean {
  return process.env.NODE_ENV === "development";
}

function readConfiguredPersonId(): string | null {
  if (!isDevelopmentRuntime()) {
    return null;
  }

  // Explicit env var always wins (including explicit disable via empty string).
  if (Object.prototype.hasOwnProperty.call(process.env, "DEV_AUTH_BYPASS_PERSON_ID")) {
    const explicitPersonId = process.env.DEV_AUTH_BYPASS_PERSON_ID?.trim();
    return explicitPersonId || null;
  }

  // Keep a deterministic default for local development unless explicitly disabled.
  return process.env.NODE_ENV === "development"
    ? DEFAULT_LOCALHOST_BYPASS_PERSON_ID
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
  return readConfiguredPersonId();
}

export function isDevAuthBypassEnabled(request: NextRequest): boolean {
  if (!isDevelopmentRuntime()) {
    return false;
  }

  const personId = readConfiguredPersonId();
  if (!personId) {
    return false;
  }

  return isLocalHostname(request.nextUrl.hostname);
}
