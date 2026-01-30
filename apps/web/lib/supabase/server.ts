import { createServerClient, type CookieOptions } from "@supabase/ssr";
import { cookies } from "next/headers";

type ServerClientOptions = {
  useServiceRole?: boolean;
};

/**
 * Create a Supabase client for server-side usage (Server Components, Route Handlers).
 * This client reads/writes cookies for session management. For privileged
 * operations, pass useServiceRole to bypass RLS (server-only).
 */
export async function createClient(options?: ServerClientOptions) {
  const cookieStore = await cookies();
  const useServiceRole = options?.useServiceRole;
  const supabaseUrl =
    process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL;
  const anonKey =
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || process.env.SUPABASE_ANON_KEY;
  const serviceKey =
    process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_SERVICE_KEY;

  if (!supabaseUrl || (!anonKey && !serviceKey)) {
    throw new Error("Supabase URL and key are required to create a client");
  }

  return createServerClient(
    supabaseUrl,
    useServiceRole ? serviceKey! : anonKey!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet: { name: string; value: string; options: CookieOptions }[]) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options)
            );
          } catch {
            // The `setAll` method was called from a Server Component.
            // This can be ignored if you have middleware refreshing sessions.
          }
        },
      },
    }
  );
}

/**
 * Get the current authenticated user from server context.
 * Returns null if not authenticated.
 */
export async function getUser() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  return user;
}

/**
 * Get the current session from server context.
 * Returns null if not authenticated.
 */
export async function getSession() {
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();
  return session;
}
