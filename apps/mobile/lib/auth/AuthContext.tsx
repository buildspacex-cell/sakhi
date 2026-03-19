import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { Platform } from "react-native";
import { Session, User } from "@supabase/supabase-js";
import * as AppleAuthentication from "expo-apple-authentication";
import * as WebBrowser from "expo-web-browser";
import * as AuthSession from "expo-auth-session";
import * as SecureStore from "expo-secure-store";
import { supabase } from "../supabase";
import { config } from "../config";

// Required for web browser auth session
WebBrowser.maybeCompleteAuthSession();

// =============================================================================
// AUTH CONTEXT
// =============================================================================

const PERSON_ID_KEY = "sakhi_person_id";
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
  isAppleAuthAvailable: boolean;
  signInWithGoogle: () => Promise<void>;
  signInWithApple: () => Promise<void>;
  signInWithEmail: (email: string) => Promise<void>;
  signOut: () => Promise<void>;
  refreshSession: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// =============================================================================
// AUTH PROVIDER
// =============================================================================

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAppleAuthAvailable, setIsAppleAuthAvailable] = useState(false);
  const devBypassPersonId = (config.devBypassPersonId || "").trim();
  const isDevBypassActive = __DEV__ && !!devBypassPersonId;
  const activeBypassPersonId = devBypassPersonId;
  const isBypassActive = isDevBypassActive;

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
    // Try cache first
    try {
      const cached = await SecureStore.getItemAsync(PERSON_ID_KEY);
      if (cached) return cached;
    } catch {}

    // Fetch from DB
    try {
      const { data, error } = await supabase
        .from("auth_users")
        .select("id")
        .eq("supabase_user_id", supabaseUserId)
        .single();

      if (error || !data?.id) return undefined;

      // Cache for next time
      try {
        await SecureStore.setItemAsync(PERSON_ID_KEY, data.id);
      } catch {}

      return data.id;
    } catch {
      return undefined;
    }
  }, []);

  // Initialize auth state — onAuthStateChange is the single source of truth.
  // Supabase fires INITIAL_SESSION immediately when subscribed (handles cached
  // tokens, token refresh, and no-session equally), so we don't need a separate
  // getSession() call that can race/conflict.
  useEffect(() => {
    if (isBypassActive) return;

    let mounted = true;
    let initialResolved = false;

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (_event, newSession) => {
        if (!mounted) return;

        setSession(newSession);

        if (newSession?.user) {
          const authUser = transformUser(newSession.user);
          if (authUser) {
            // Try cached personId first for instant load
            let personId: string | undefined;
            try {
              personId = (await SecureStore.getItemAsync(PERSON_ID_KEY)) || undefined;
            } catch {}

            if (personId) {
              setUser({ ...authUser, personId });
            } else {
              setUser(authUser);
            }

            // Resolve loading on first event
            if (!initialResolved) {
              initialResolved = true;
              setIsLoading(false);
            }

            // Fetch personId in background if not cached
            if (!personId) {
              const fetchedId = await fetchAndCachePersonId(newSession.user.id);
              if (mounted && fetchedId) {
                setUser((prev) => prev ? { ...prev, personId: fetchedId } : prev);
              }
            }
          }
        } else {
          setUser(null);
          // Clear cached personId on sign out
          try { await SecureStore.deleteItemAsync(PERSON_ID_KEY); } catch {}
        }

        // Always resolve loading after first auth event (signed in or not)
        if (!initialResolved) {
          initialResolved = true;
          setIsLoading(false);
        }
      }
    );

    // Safety timeout — if onAuthStateChange never fires (e.g. network issue),
    // don't leave the user stuck on splash forever
    const timeout = setTimeout(() => {
      if (!initialResolved && mounted) {
        initialResolved = true;
        setIsLoading(false);
      }
    }, 5000);

    return () => {
      mounted = false;
      clearTimeout(timeout);
      subscription.unsubscribe();
    };
  }, [transformUser, fetchAndCachePersonId, isBypassActive]);

  // Sign in with Google
  const signInWithGoogle = useCallback(async () => {
    const redirectUri = AuthSession.makeRedirectUri({
      scheme: "sakhi",
      path: "auth/callback",
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

    if (Platform.OS === "android") await WebBrowser.warmUpAsync();

    const result = await WebBrowser.openAuthSessionAsync(data.url, redirectUri);

    if (Platform.OS === "android") await WebBrowser.coolDownAsync();

    if (result.type === "success" && result.url) {
      const responseUrl = result.url;
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
          responseUrl.substring(queryIndex + 1, hashIndex !== -1 ? hashIndex : undefined)
        );
        code = queryParams.get("code");
        errorDescription = errorDescription || queryParams.get("error_description");
      }

      if (errorDescription) throw new Error(errorDescription);

      if (accessToken) {
        // Fire and forget — onAuthStateChange listener handles the state update.
        // setSession is slow (>10s on iOS) but eventually completes.
        supabase.auth.setSession({
          access_token: accessToken,
          refresh_token: refreshToken || "",
        });
      } else if (code) {
        supabase.auth.exchangeCodeForSession(code);
      }
    }
    // cancel/dismiss — do nothing
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
      return;
    }
    const { error } = await supabase.auth.signOut();
    if (error) throw error;
    setUser(null);
    setSession(null);
    try { await SecureStore.deleteItemAsync(PERSON_ID_KEY); } catch {}
  }, [isBypassActive]);

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
    isAuthenticated: isBypassActive ? !!user?.personId : !!session && !!user,
    isAppleAuthAvailable,
    signInWithGoogle,
    signInWithApple,
    signInWithEmail,
    signOut,
    refreshSession,
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
