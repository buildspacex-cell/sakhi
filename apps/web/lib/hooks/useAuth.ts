"use client";

import { useEffect, useState, useCallback } from "react";
import { createClient } from "@/lib/supabase/client";
import type { User, Session } from "@supabase/supabase-js";

interface AuthUser {
  id: string; // This is the person_id from auth_users table
  supabaseUserId: string;
  email: string;
  fullName: string | null;
  avatarUrl: string | null;
}

interface UseAuthReturn {
  user: AuthUser | null;
  session: Session | null;
  loading: boolean;
  signOut: () => Promise<void>;
}

/**
 * Hook to access authentication state and user info.
 *
 * The user.id returned is the person_id (from auth_users table)
 * which should be used throughout the app for API calls.
 */
export function useAuth(): UseAuthReturn {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  const supabase = createClient();

  // Fetch auth_users record to get person_id
  const fetchAuthUser = useCallback(
    async (supabaseUser: User) => {
      try {
        const { data, error } = await supabase
          .from("auth_users")
          .select("id, email, full_name, avatar_url")
          .eq("supabase_user_id", supabaseUser.id)
          .single();

        if (error) {
          console.error("Error fetching auth_users:", error);
          // Fallback to supabase user info
          return {
            id: supabaseUser.id, // Use supabase ID as fallback
            supabaseUserId: supabaseUser.id,
            email: supabaseUser.email!,
            fullName: supabaseUser.user_metadata?.full_name || null,
            avatarUrl: supabaseUser.user_metadata?.avatar_url || null,
          };
        }

        return {
          id: data.id, // This is the person_id
          supabaseUserId: supabaseUser.id,
          email: data.email,
          fullName: data.full_name,
          avatarUrl: data.avatar_url,
        };
      } catch (err) {
        console.error("Error in fetchAuthUser:", err);
        return null;
      }
    },
    [supabase]
  );

  useEffect(() => {
    // Get initial session
    const getInitialSession = async () => {
      try {
        const {
          data: { session: currentSession },
        } = await supabase.auth.getSession();

        setSession(currentSession);

        if (currentSession?.user) {
          const authUser = await fetchAuthUser(currentSession.user);
          setUser(authUser);
        }
      } catch (err) {
        console.error("Error getting initial session:", err);
      } finally {
        setLoading(false);
      }
    };

    getInitialSession();

    // Listen for auth changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (event, newSession) => {
      setSession(newSession);

      if (newSession?.user) {
        const authUser = await fetchAuthUser(newSession.user);
        setUser(authUser);
      } else {
        setUser(null);
      }

      setLoading(false);
    });

    return () => {
      subscription.unsubscribe();
    };
  }, [supabase, fetchAuthUser]);

  const signOut = useCallback(async () => {
    await supabase.auth.signOut();
    setUser(null);
    setSession(null);
    // Redirect to login
    window.location.href = "/auth/login";
  }, [supabase]);

  return { user, session, loading, signOut };
}
