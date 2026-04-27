import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { Platform } from "react-native";
import { Session, User } from "@supabase/supabase-js";
import * as AppleAuthentication from "expo-apple-authentication";
import * as WebBrowser from "expo-web-browser";
import * as AuthSession from "expo-auth-session";
import { supabase } from "../supabase";
import { config } from "../config";
import {
  clearCachedPersonId,
  clearLegacyPersonIdCache,
  readCachedPersonId,
  writeCachedPersonId,
} from "./personCache";
import { recordAuthDebug } from "./authDebug";
import { completeMobileAuthRedirect, parseAuthRedirectUrl } from "./oauthRedirect";

// Required for web browser auth session
WebBrowser.maybeCompleteAuthSession();

// =============================================================================
// AUTH CONTEXT
// =============================================================================

const BYPASS_PROFILE_LABELS: Record<string, string> = {
  "a1b2c3d4-1111-4000-8000-000000000001": "Vidhya",
  "4ea551dc-517c-443b-8f1f-d1f528ac10ba": "Ravi",
};

interface AuthUser {
  id: string;
  email: string;
  fullName?: string;
  avatarUrl?: string;
  personId?: string;
}

interface AuthContextType {
  user: AuthUser | null;
  session: Session | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  authExitIntent: "none" | "signed_out" | "expired";
  isAppleAuthAvailable: boolean;
  signInWithGoogle: () => Promise<"success" | "cancelled">;
  signInWithApple: () => Promise<void>;
  signInWithEmail: (email: string) => Promise<void>;
  signOut: () => Promise<void>;
  refreshSession: () => Promise<void>;
  hydrateLinkedProfile: (profile: {
    personId: string;
    email?: string;
    fullName?: string | null;
    avatarUrl?: string | null;
  }, options?: { supabaseUserId?: string }) => Promise<void>;
  clearAuthExitIntent: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// =============================================================================
// AUTH PROVIDER
// =============================================================================

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [authExitIntent, setAuthExitIntent] = useState<"none" | "signed_out" | "expired">("none");
  const [isAppleAuthAvailable, setIsAppleAuthAvailable] = useState(false);
  const devBypassPersonId = (config.devBypassPersonId || "").trim();
  const isDevBypassActive = __DEV__ && !!devBypassPersonId;
  const activeBypassPersonId = devBypassPersonId;
  const isBypassActive = isDevBypassActive;
  const intentionalSignOutRef = React.useRef(false);
  const hadSessionRef = React.useRef(false);

  useEffect(() => {
    if (Platform.OS === "ios") {
      AppleAuthentication.isAvailableAsync().then(setIsAppleAuthAvailable);
    }
  }, []);

  // Development-only auth bypass for end-to-end profile testing in iOS simulator.
  useEffect(() => {
    if (!isBypassActive) return;
    const bypassName =
      BYPASS_PROFILE_LABELS[activeBypassPersonId]
      || "Sakhi User";
    setSession(null);
    setUser({
      id: activeBypassPersonId,
      email: "dev-bypass@sakhi.local",
      fullName: bypassName,
      personId: activeBypassPersonId,
    });
    setAuthExitIntent("none");
    setIsLoading(false);
  }, [activeBypassPersonId, isBypassActive]);

  const transformUser = useCallback((supabaseUser: User | null): AuthUser | null => {
    if (!supabaseUser) return null;
    return {
      id: supabaseUser.id,
      email: supabaseUser.email || "",
      fullName: supabaseUser.user_metadata?.full_name || supabaseUser.user_metadata?.name,
      avatarUrl: supabaseUser.user_metadata?.avatar_url || supabaseUser.user_metadata?.picture,
    };
  }, []);

  // Fetch personId from DB and cache it locally
  const fetchAndCachePersonId = useCallback(async (supabaseUserId: string): Promise<string | undefined> => {
    const cached = await readCachedPersonId(supabaseUserId);
    if (cached) return cached;

    // Fetch from DB
    try {
      const { data, error } = await supabase
        .from("auth_users")
        .select("id")
        .eq("supabase_user_id", supabaseUserId)
        .single();

      if (error || !data?.id) return undefined;

      // Cache for next time
      await writeCachedPersonId(supabaseUserId, data.id);

      return data.id;
    } catch {
      return undefined;
    }
  }, []);

  const hydrateLinkedProfile = useCallback(async (
    profile: {
      personId: string;
      email?: string;
      fullName?: string | null;
      avatarUrl?: string | null;
    },
    options?: { supabaseUserId?: string },
  ): Promise<void> => {
    const personId = String(profile.personId || "").trim();
    if (!personId) return;

    const supabaseUserId = String(
      options?.supabaseUserId || user?.id || session?.user?.id || "",
    ).trim();

    if (supabaseUserId) {
      await writeCachedPersonId(supabaseUserId, personId);
    }

    setUser((prev) => {
      const base: AuthUser = prev || {
        id: supabaseUserId || personId,
        email: String(profile.email || ""),
      };

      return {
        ...base,
        email: String(profile.email || base.email || ""),
        fullName: profile.fullName ?? base.fullName,
        avatarUrl: profile.avatarUrl ?? base.avatarUrl,
        personId,
      };
    });
    setAuthExitIntent("none");
  }, [session?.user?.id, user?.id]);

  // Two-phase auth init:
  //
  // Phase 1 — getSession() reads directly from the iOS Keychain / AsyncStorage
  // (~5ms, no network). If a cached session exists we unlock the app immediately,
  // even if the access token is already expired. The Supabase client refreshes
  // tokens transparently before outbound API calls, so an expired token never
  // surfaces to the UI.
  //
  // Phase 2 — onAuthStateChange fires after Supabase has refreshed an expired
  // token (network round-trip). It updates the in-memory session and handles
  // sign-out / token expiry. It no longer gates the initial render.
  useEffect(() => {
    if (isBypassActive) return;

    let mounted = true;
    let initialResolved = false;
    void clearLegacyPersonIdCache();

    // Phase 1: fast path from local storage
    supabase.auth.getSession().then(async ({ data: { session: cachedSession } }) => {
      if (!mounted || initialResolved) return;

      if (cachedSession?.user) {
        hadSessionRef.current = true;
        const authUser = transformUser(cachedSession.user);
        if (authUser) {
          const cachedPersonId = await readCachedPersonId(cachedSession.user.id);
          setSession(cachedSession);
          setUser(cachedPersonId ? { ...authUser, personId: cachedPersonId } : authUser);
          setAuthExitIntent("none");

          // Fetch personId in background if not in cache — doesn't block render
          if (!cachedPersonId) {
            fetchAndCachePersonId(cachedSession.user.id).then((fetchedId) => {
              if (mounted && fetchedId) {
                setUser((prev) => prev ? { ...prev, personId: fetchedId } : prev);
              }
            });
          }
        }
      }

      // Unlock the app — don't wait for token refresh
      initialResolved = true;
      setIsLoading(false);
    }).catch(() => {
      if (!mounted || initialResolved) return;
      initialResolved = true;
      setIsLoading(false);
    });

    // Phase 2: background token refresh and ongoing state changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (_event, newSession) => {
        if (!mounted) return;

        const hadSession = hadSessionRef.current;
        hadSessionRef.current = !!newSession?.user;
        setSession(newSession);

        if (newSession?.user) {
          setAuthExitIntent("none");
          const authUser = transformUser(newSession.user);
          if (authUser) {
            const cachedPersonId = await readCachedPersonId(newSession.user.id);
            if (cachedPersonId) {
              setUser({ ...authUser, personId: cachedPersonId });
            } else {
              setUser(authUser);
            }
            if (!cachedPersonId) {
              const fetchedId = await fetchAndCachePersonId(newSession.user.id);
              if (mounted && fetchedId) {
                setUser((prev) => prev ? { ...prev, personId: fetchedId } : prev);
              }
            }
          }
        } else {
          setUser(null);
          if (hadSession) {
            setAuthExitIntent(intentionalSignOutRef.current ? "signed_out" : "expired");
          } else {
            setAuthExitIntent("none");
          }
          intentionalSignOutRef.current = false;
        }

        // Fallback: resolve loading if Phase 1 never completed (e.g. getSession threw)
        if (!initialResolved) {
          initialResolved = true;
          setIsLoading(false);
        }
      }
    );

    // Safety net: if both Phase 1 and onAuthStateChange fail (no network, corrupt storage)
    const timeout = setTimeout(() => {
      if (!initialResolved && mounted) {
        initialResolved = true;
        setIsLoading(false);
      }
    }, 2500);

    return () => {
      mounted = false;
      clearTimeout(timeout);
      subscription.unsubscribe();
    };
  }, [transformUser, fetchAndCachePersonId, isBypassActive]);

  // Sign in with Google
  const signInWithGoogle = useCallback(async (): Promise<"success" | "cancelled"> => {
    const redirectUri = AuthSession.makeRedirectUri({
      scheme: "sakhi",
      path: "auth/callback",
    });
    await recordAuthDebug("Starting Google OAuth", {
      platform: Platform.OS,
      redirectUri,
    });

    const { data, error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: redirectUri,
        skipBrowserRedirect: true,
        queryParams: {
          access_type: "offline",
          prompt: "consent",
        },
      },
    });

    if (error) throw error;
    if (!data?.url) throw new Error("No OAuth URL returned from Supabase");
    await recordAuthDebug("Received Supabase OAuth URL");

    if (Platform.OS === "android") await WebBrowser.warmUpAsync();

    const result = await WebBrowser.openAuthSessionAsync(data.url, redirectUri);
    await recordAuthDebug("Browser auth session returned", {
      resultType: result.type,
      hasUrl: "url" in result && !!result.url,
    });

    if (Platform.OS === "android") await WebBrowser.coolDownAsync();

    if (result.type !== "success" || !result.url) {
      await recordAuthDebug("Google OAuth was cancelled or dismissed", {
        resultType: result.type,
      });
      return "cancelled";
    }
    const payload = parseAuthRedirectUrl(result.url);
    await completeMobileAuthRedirect(payload);
    await recordAuthDebug("Google OAuth completed successfully");
    return "success";
  }, []);

  // Sign in with Apple (iOS only)
  const signInWithApple = useCallback(async () => {
    try {
      const credential = await AppleAuthentication.signInAsync({
        requestedScopes: [
          AppleAuthentication.AppleAuthenticationScope.FULL_NAME,
          AppleAuthentication.AppleAuthenticationScope.EMAIL,
        ],
      });

      if (credential.identityToken) {
        const { error } = await supabase.auth.signInWithIdToken({
          provider: "apple",
          token: credential.identityToken,
        });
        if (error) throw error;
      } else {
        throw new Error("No identity token returned from Apple");
      }
    } catch (error: unknown) {
      if (error && typeof error === "object" && "code" in error) {
        if ((error as { code: string }).code === "ERR_REQUEST_CANCELED") return;
      }
      throw error;
    }
  }, []);

  // Sign in with email (magic link)
  const signInWithEmail = useCallback(async (email: string) => {
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: "sakhi://auth/callback" },
    });
    if (error) throw error;
  }, []);

  // Sign out
  const signOut = useCallback(async () => {
    if (isBypassActive) {
      setUser(null);
      setSession(null);
      setAuthExitIntent("signed_out");
      return;
    }

    const supabaseUserId = String(session?.user?.id || user?.id || "").trim();
    intentionalSignOutRef.current = true;

    // Fire-and-forget — scope:"local" only clears local storage; we don't need
    // to await it. Waiting can block on network or onAuthStateChange handlers,
    // leaving the button stuck at "Signing out…" indefinitely.
    supabase.auth.signOut({ scope: "local" }).catch((err) => {
      console.warn("[auth] sign-out threw unexpectedly", err);
    });

    if (supabaseUserId) {
      try {
        await clearCachedPersonId(supabaseUserId);
      } catch (err) {
        console.warn("[auth] clearCachedPersonId failed", err);
      }
    }

    // Always clear local state regardless of network errors above
    setUser(null);
    setSession(null);
    setAuthExitIntent("signed_out");

    try {
      await clearLegacyPersonIdCache();
    } catch (err) {
      console.warn("[auth] clearLegacyPersonIdCache failed", err);
    }
  }, [isBypassActive, session?.user?.id, user?.id]);

  // Refresh session
  const refreshSession = useCallback(async () => {
    const { data: { session: newSession }, error } = await supabase.auth.refreshSession();
    if (error) throw error;
    setSession(newSession);
  }, []);

  const value: AuthContextType = {
    user,
    session,
    isLoading,
    isAuthenticated: isBypassActive ? !!user?.personId : !!session && !!user?.personId,
    authExitIntent,
    isAppleAuthAvailable,
    signInWithGoogle,
    signInWithApple,
    signInWithEmail,
    signOut,
    refreshSession,
    hydrateLinkedProfile,
    clearAuthExitIntent: () => setAuthExitIntent("none"),
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// =============================================================================
// HOOK
// =============================================================================

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
