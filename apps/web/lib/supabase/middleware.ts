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
  // But skip redirect if already on an auth route to prevent infinite redirect loops
  const isOnAuthRoute = ["/auth/login", "/auth/callback"].some((route) =>
    request.nextUrl.pathname.startsWith(route)
  );

  if (authError?.message?.toLowerCase().includes("refresh token")) {
    // Clear all Supabase auth cookies (they use the pattern sb-<ref>-auth-token*)
    const supabaseCookies = request.cookies
      .getAll()
      .filter((c) => c.name.startsWith("sb-"));
    if (isOnAuthRoute) {
      // Already on login page — just clear cookies and let the page render
      supabaseResponse = NextResponse.next({ request });
      supabaseCookies.forEach((c) => supabaseResponse.cookies.delete(c.name));
      return supabaseResponse;
    }
    const url = request.nextUrl.clone();
    url.pathname = "/auth/login";
    supabaseResponse = NextResponse.redirect(url);
    supabaseCookies.forEach((c) => supabaseResponse.cookies.delete(c.name));
    return supabaseResponse;
  }

  // Define protected routes that require authentication
  // Note: /experience itself is the public welcome screen; only sub-routes are protected
  const protectedRoutes = ["/experience/onboarding", "/experience/converse"];
  const isProtectedRoute = protectedRoutes.some((route) =>
    request.nextUrl.pathname.startsWith(route)
  );

  // If accessing a protected route without auth, redirect to login
  if (isProtectedRoute && !user) {
    const url = request.nextUrl.clone();
    url.pathname = "/auth/login";
    url.searchParams.set("redirect", request.nextUrl.pathname);
    return NextResponse.redirect(url);
  }

  // If already authenticated and trying to access login, honour the redirect param
  if (isOnAuthRoute && user && request.nextUrl.pathname === "/auth/login") {
    const url = request.nextUrl.clone();
    const redirectParam = request.nextUrl.searchParams.get("redirect");
    if (redirectParam && redirectParam.startsWith("/")) {
      url.pathname = redirectParam;
    } else {
      url.pathname = "/experience";
    }
    // Clear leftover search params so ?redirect= doesn't bleed through
    url.search = "";
    return NextResponse.redirect(url);
  }

  return supabaseResponse;
}
