import { createServerClient, type CookieOptions } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

/**
 * Create a Supabase client for middleware usage.
 * Handles session refresh and cookie management.
 */
export async function updateSession(request: NextRequest) {
  const supabaseUrl =
    process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL;
  const supabaseAnonKey =
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || process.env.SUPABASE_ANON_KEY;

  // If Supabase env vars are missing, skip auth handling to avoid runtime crashes
  if (!supabaseUrl || !supabaseAnonKey) {
    console.error("Supabase env vars missing in middleware. Skipping auth guard.");
    return NextResponse.next({ request });
  }

  let supabaseResponse = NextResponse.next({
    request,
  });

  const supabase = createServerClient(
    supabaseUrl,
    supabaseAnonKey,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet: { name: string; value: string; options: CookieOptions }[]) {
          cookiesToSet.forEach(({ name, value }) =>
            request.cookies.set(name, value)
          );
          supabaseResponse = NextResponse.next({
            request,
          });
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          );
        },
      },
    }
  );

  // IMPORTANT: Avoid writing any logic between createServerClient and
  // supabase.auth.getUser(). A simple mistake could make it very hard to debug
  // issues with users being randomly logged out.

  const {
    data: { user },
    error: authError,
  } = await supabase.auth.getUser();

  // If refresh token is invalid/used, clear cookies and force re-auth
  if (authError?.message?.toLowerCase().includes("refresh token")) {
    const url = request.nextUrl.clone();
    url.pathname = "/auth/login";
    supabaseResponse = NextResponse.redirect(url);
    ["sb-access-token", "sb-refresh-token"].forEach((name) =>
      supabaseResponse.cookies.delete(name)
    );
    return supabaseResponse;
  }

  // Define protected routes that require authentication
  const protectedRoutes = ["/experience"];
  const isProtectedRoute = protectedRoutes.some((route) =>
    request.nextUrl.pathname.startsWith(route)
  );

  // Define auth routes (login, signup, etc.)
  const authRoutes = ["/auth/login", "/auth/callback"];
  const isAuthRoute = authRoutes.some((route) =>
    request.nextUrl.pathname.startsWith(route)
  );

  // If accessing a protected route without auth, redirect to login
  if (isProtectedRoute && !user) {
    const url = request.nextUrl.clone();
    url.pathname = "/auth/login";
    url.searchParams.set("redirect", request.nextUrl.pathname);
    return NextResponse.redirect(url);
  }

  // If already authenticated and trying to access login, redirect to experience
  if (isAuthRoute && user && request.nextUrl.pathname === "/auth/login") {
    const url = request.nextUrl.clone();
    url.pathname = "/experience";
    return NextResponse.redirect(url);
  }

  return supabaseResponse;
}
