import { supabase } from "../supabase";
import { recordAuthDebug } from "./authDebug";

export interface ParsedAuthRedirect {
  accessToken: string | null;
  refreshToken: string | null;
  code: string | null;
  errorDescription: string | null;
}

export function parseAuthRedirectUrl(responseUrl: string): ParsedAuthRedirect {
  const hashIndex = responseUrl.indexOf("#");
  const queryIndex = responseUrl.indexOf("?");

  let accessToken: string | null = null;
  let refreshToken: string | null = null;
  let code: string | null = null;
  let errorDescription: string | null = null;

  if (hashIndex !== -1) {
    const hashParams = new URLSearchParams(responseUrl.substring(hashIndex + 1));
    accessToken = hashParams.get("access_token");
    refreshToken = hashParams.get("refresh_token");
    errorDescription = hashParams.get("error_description");
  }

  if (!accessToken && queryIndex !== -1) {
    const queryParams = new URLSearchParams(
      responseUrl.substring(queryIndex + 1, hashIndex !== -1 ? hashIndex : undefined),
    );
    code = queryParams.get("code");
    errorDescription = errorDescription || queryParams.get("error_description");
  }

  return { accessToken, refreshToken, code, errorDescription };
}

export async function completeMobileAuthRedirect(payload: ParsedAuthRedirect): Promise<string | null> {
  const { accessToken, refreshToken, code, errorDescription } = payload;
  await recordAuthDebug("Completing OAuth redirect", {
    hasAccessToken: !!accessToken,
    hasRefreshToken: !!refreshToken,
    hasCode: !!code,
    hasErrorDescription: !!errorDescription,
  });

  if (errorDescription) {
    await recordAuthDebug("OAuth redirect contained provider error", {
      errorDescription,
    }, "error");
    throw new Error(errorDescription);
  }

  if (accessToken && refreshToken) {
    await recordAuthDebug("Persisting OAuth session from returned tokens");
    const { error } = await supabase.auth.setSession({
      access_token: accessToken,
      refresh_token: refreshToken,
    });

    if (error) {
      await recordAuthDebug("supabase.auth.setSession failed", {
        message: error.message,
        name: error.name,
        status: (error as { status?: number }).status,
      }, "error");
      throw error;
    }

    await recordAuthDebug("OAuth session persisted from tokens");
    return accessToken;
  }

  if (code) {
    await recordAuthDebug("Exchanging OAuth code for session");
    const { data, error } = await supabase.auth.exchangeCodeForSession(code);

    if (error) {
      await recordAuthDebug("supabase.auth.exchangeCodeForSession failed", {
        message: error.message,
        name: error.name,
        status: (error as { status?: number }).status,
      }, "error");
      throw error;
    }

    await recordAuthDebug("OAuth code exchange completed", {
      hasSession: !!data.session,
      hasAccessToken: !!data.session?.access_token,
    });
    return data.session?.access_token || null;
  }

  await recordAuthDebug("OAuth redirect missing tokens and code", undefined, "error");
  throw new Error("No auth tokens or code found in OAuth callback");
}
