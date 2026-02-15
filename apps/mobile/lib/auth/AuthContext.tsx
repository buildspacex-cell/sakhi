import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { Platform } from "react-native";
import { Session, User } from "@supabase/supabase-js";
import * as AppleAuthentication from "expo-apple-authentication";
import * as WebBrowser from "expo-web-browser";
import * as AuthSession from "expo-auth-session";
import * as SecureStore from "expo-secure-store";
import { supabase } from "../supabase";

// Required for web browser auth session
WebBrowser.maybeCompleteAuthSession();

// =============================================================================
// AUTH CONTEXT
// =============================================================================

const PERSON_ID_KEY = "sakhi_person_id";

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

  useEffect(() => {
    if (Platform.OS === "ios") {
      AppleAuthentication.isAvailableAsync().then(setIsAppleAuthAvailable);
    }
  }, []);

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

  // Initialize auth state
  useEffect(() => {
    let mounted = true;

    const initAuth = async () => {
      try {
        // Timeout getSession — if Supabase hangs refreshing an old token, don't block forever
        const sessionResult = await Promise.race([
          supabase.auth.getSession(),
          new Promise<null>((resolve) => setTimeout(() => resolve(null), 5000)),
        ]);

        const existingSession = sessionResult
          ? (sessionResult as { data: { session: Session | null } }).data.session
          : null;

        if (mounted && existingSession) {
          setSession(existingSession);
          const authUser = transformUser(existingSession.user);
          if (authUser) {
            // Try cached personId first (instant) — show UI immediately
            let personId: string | undefined;
            try {
              personId = (await SecureStore.getItemAsync(PERSON_ID_KEY)) || undefined;
            } catch {}

            if (personId) {
              // Cache hit — user is ready instantly
              setUser({ ...authUser, personId });
              if (mounted) setIsLoading(false);
            } else {
              // No cache — show UI immediately, fetch personId in background
              setUser(authUser);
              if (mounted) setIsLoading(false);

              // Fetch and update in background
              const fetchedId = await fetchAndCachePersonId(existingSession.user.id);
              if (mounted && fetchedId) {
                setUser((prev) => prev ? { ...prev, personId: fetchedId } : prev);
              }
            }
            return;
          }
        }
      } catch {
        // Silent fail — user will see login screen
      } finally {
        if (mounted) setIsLoading(false);
      }
    };

    initAuth();

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, newSession) => {
        if (!mounted) return;

        setSession(newSession);

        if (newSession?.user) {
          const authUser = transformUser(newSession.user);
          if (authUser) {
            // Set user immediately, fetch personId in background
            setUser(authUser);
            setIsLoading(false);

            const personId = await fetchAndCachePersonId(newSession.user.id);
            if (mounted && personId) {
              setUser((prev) => prev ? { ...prev, personId } : prev);
            }
          }
        } else {
          setUser(null);
          // Clear cached personId on sign out
          try { await SecureStore.deleteItemAsync(PERSON_ID_KEY); } catch {}
        }

        setIsLoading(false);
      }
    );

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, [transformUser, fetchAndCachePersonId]);

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
    const { error } = await supabase.auth.signOut();
    if (error) throw error;
    setUser(null);
    setSession(null);
    try { await SecureStore.deleteItemAsync(PERSON_ID_KEY); } catch {}
  }, []);

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
    isAuthenticated: !!session && !!user,
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
