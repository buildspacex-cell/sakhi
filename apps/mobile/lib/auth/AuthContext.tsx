import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { Platform } from "react-native";
import { Session, User } from "@supabase/supabase-js";
import * as AppleAuthentication from "expo-apple-authentication";
import * as WebBrowser from "expo-web-browser";
import * as AuthSession from "expo-auth-session";
import { supabase } from "../supabase";

// Required for web browser auth session
WebBrowser.maybeCompleteAuthSession();

// =============================================================================
// AUTH CONTEXT
// =============================================================================
// Provides authentication state throughout the app.
// Handles session persistence, refresh, and user state.

interface AuthUser {
  id: string; // This is the Supabase user ID
  email: string;
  fullName?: string;
  avatarUrl?: string;
  personId?: string; // The auth_users.id which is used as person_id
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

  // Check Apple auth availability on mount
  useEffect(() => {
    if (Platform.OS === "ios") {
      AppleAuthentication.isAvailableAsync().then(setIsAppleAuthAvailable);
    }
  }, []);

  // Transform Supabase user to our AuthUser type
  const transformUser = useCallback((supabaseUser: User | null): AuthUser | null => {
    if (!supabaseUser) return null;

    return {
      id: supabaseUser.id,
      email: supabaseUser.email || "",
      fullName: supabaseUser.user_metadata?.full_name || supabaseUser.user_metadata?.name,
      avatarUrl: supabaseUser.user_metadata?.avatar_url || supabaseUser.user_metadata?.picture,
      // personId will be fetched separately from auth_users table
    };
  }, []);

  // Fetch the person_id from auth_users table
  const fetchPersonId = useCallback(async (supabaseUserId: string): Promise<string | undefined> => {
    try {
      const { data, error } = await supabase
        .from("auth_users")
        .select("id")
        .eq("supabase_user_id", supabaseUserId)
        .single();

      if (error) {
        console.error("Error fetching person_id:", error);
        return undefined;
      }

      return data?.id;
    } catch (err) {
      console.error("Error in fetchPersonId:", err);
      return undefined;
    }
  }, []);

  // Initialize auth state
  useEffect(() => {
    let mounted = true;

    const initAuth = async () => {
      try {
        // Get existing session
        const { data: { session: existingSession } } = await supabase.auth.getSession();

        if (mounted && existingSession) {
          setSession(existingSession);
          const authUser = transformUser(existingSession.user);

          if (authUser) {
            // Fetch person_id
            const personId = await fetchPersonId(existingSession.user.id);
            setUser({ ...authUser, personId });
          }
        }
      } catch (error) {
        console.error("Error initializing auth:", error);
      } finally {
        if (mounted) {
          setIsLoading(false);
        }
      }
    };

    initAuth();

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, newSession) => {
        if (!mounted) return;

        setSession(newSession);

        if (newSession?.user) {
          const authUser = transformUser(newSession.user);
          if (authUser) {
            const personId = await fetchPersonId(newSession.user.id);
            setUser({ ...authUser, personId });
          }
        } else {
          setUser(null);
        }

        setIsLoading(false);
      }
    );

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, [transformUser, fetchPersonId]);

  // Sign in with Google using expo-auth-session
  const signInWithGoogle = useCallback(async () => {
    try {
      // Use Expo's proxy for Expo Go - this provides a web-based redirect
      // that then redirects to the app via a more reliable mechanism
      const redirectUri = AuthSession.makeRedirectUri({
        // Use Expo's auth proxy for Expo Go
        preferLocalhost: true,
      });

      console.log("Google OAuth redirect URI:", redirectUri);

      // For Expo Go, we need to use a slightly different approach
      // Get the Supabase OAuth URL
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

      if (error) {
        console.error("Google OAuth setup error:", error);
        throw error;
      }

      if (!data?.url) {
        throw new Error("No OAuth URL returned from Supabase");
      }

      console.log("Opening OAuth URL...");

      // Use warmUpAsync for better performance on Android
      if (Platform.OS === "android") {
        await WebBrowser.warmUpAsync();
      }

      // Open the auth session
      const result = await WebBrowser.openAuthSessionAsync(data.url, redirectUri);

      // Cleanup on Android
      if (Platform.OS === "android") {
        await WebBrowser.coolDownAsync();
      }

      console.log("WebBrowser result:", result.type);

      if (result.type === "success" && result.url) {
        const responseUrl = result.url;
        console.log("OAuth callback URL:", responseUrl);

        // Extract hash fragment (Supabase returns tokens in hash)
        const hashIndex = responseUrl.indexOf("#");
        const queryIndex = responseUrl.indexOf("?");

        let accessToken: string | null = null;
        let refreshToken: string | null = null;
        let code: string | null = null;
        let errorDescription: string | null = null;

        // Parse hash params
        if (hashIndex !== -1) {
          const hashString = responseUrl.substring(hashIndex + 1);
          const hashParams = new URLSearchParams(hashString);
          accessToken = hashParams.get("access_token");
          refreshToken = hashParams.get("refresh_token");
          errorDescription = hashParams.get("error_description");
        }

        // Parse query params if no hash params
        if (!accessToken && queryIndex !== -1) {
          const queryString = responseUrl.substring(queryIndex + 1, hashIndex !== -1 ? hashIndex : undefined);
          const queryParams = new URLSearchParams(queryString);
          code = queryParams.get("code");
          errorDescription = errorDescription || queryParams.get("error_description");
        }

        if (errorDescription) {
          throw new Error(errorDescription);
        }

        if (accessToken) {
          console.log("Setting session with access token...");
          const { error: sessionError } = await supabase.auth.setSession({
            access_token: accessToken,
            refresh_token: refreshToken || "",
          });

          if (sessionError) {
            console.error("Error setting session:", sessionError);
            throw sessionError;
          }
          console.log("Session set successfully!");
        } else if (code) {
          console.log("Exchanging code for session...");
          const { error: exchangeError } = await supabase.auth.exchangeCodeForSession(code);
          if (exchangeError) {
            console.error("Error exchanging code:", exchangeError);
            throw exchangeError;
          }
          console.log("Code exchanged successfully!");
        } else {
          console.log("No tokens or code in callback URL");
        }
      } else if (result.type === "cancel" || result.type === "dismiss") {
        console.log("User cancelled Google sign-in");
        return;
      }
    } catch (error) {
      console.error("Google sign-in error:", error);
      throw error;
    }
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

      // Sign in with Supabase using the Apple ID token
      if (credential.identityToken) {
        const { error } = await supabase.auth.signInWithIdToken({
          provider: "apple",
          token: credential.identityToken,
        });

        if (error) {
          console.error("Apple sign-in Supabase error:", error);
          throw error;
        }
      } else {
        throw new Error("No identity token returned from Apple");
      }
    } catch (error: unknown) {
      if (error && typeof error === "object" && "code" in error) {
        const appleError = error as { code: string };
        if (appleError.code === "ERR_REQUEST_CANCELED") {
          // User canceled - don't throw
          return;
        }
      }
      console.error("Apple sign-in error:", error);
      throw error;
    }
  }, []);

  // Sign in with email (magic link)
  const signInWithEmail = useCallback(async (email: string) => {
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: {
        emailRedirectTo: "sakhi://auth/callback",
      },
    });

    if (error) {
      console.error("Email sign-in error:", error);
      throw error;
    }
  }, []);

  // Sign out
  const signOut = useCallback(async () => {
    const { error } = await supabase.auth.signOut();
    if (error) {
      console.error("Sign out error:", error);
      throw error;
    }
    setUser(null);
    setSession(null);
  }, []);

  // Refresh session
  const refreshSession = useCallback(async () => {
    const { data: { session: newSession }, error } = await supabase.auth.refreshSession();
    if (error) {
      console.error("Session refresh error:", error);
      throw error;
    }
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
