import { NextRequest, NextResponse } from "next/server";
import { createServerClient, type CookieOptions } from "@supabase/ssr";

/**
 * OAuth Callback Handler
 *
 * This route handles the OAuth callback from Google/Supabase:
 * 1. Exchanges the code for a session
 * 2. Creates or updates the auth_users record (which serves as person_id)
 * 3. Redirects to the appropriate page
 */
export async function GET(request: NextRequest) {
  const { searchParams, origin } = request.nextUrl;
  const code = searchParams.get("code");
  const redirect = searchParams.get("redirect") || "/experience/converse";

  const buildPostAuthPath = (personId: string, fullName: string | null | undefined) => {
    const trimmedName = String(fullName || "").trim();
    if (!trimmedName) {
      return `/experience/onboarding?user=${encodeURIComponent(personId)}`;
    }
    if (
      redirect === "/experience"
      || redirect === "/experience/converse"
      || redirect === "/experience/onboarding"
    ) {
      return `/experience/converse?user=${encodeURIComponent(personId)}&name=${encodeURIComponent(trimmedName)}`;
    }
    return redirect;
  };

  if (code) {
    // Create initial response — destination may change after we check onboarding
    let response = NextResponse.redirect(`${origin}${redirect}`);
    let postAuthPath = redirect;

    const supabase = createServerClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      // Use service role to bypass RLS when syncing auth_users on callback
      process.env.SUPABASE_SERVICE_ROLE_KEY!,
      {
        cookies: {
          getAll() {
            return request.cookies.getAll();
          },
          setAll(cookiesToSet: { name: string; value: string; options: CookieOptions }[]) {
            cookiesToSet.forEach(({ name, value, options }) => {
              response.cookies.set(name, value, options);
            });
          },
        },
      }
    );

    // Exchange code for session
    const { data: sessionData, error: sessionError } =
      await supabase.auth.exchangeCodeForSession(code);

    if (sessionError) {
      console.error("Session exchange error:", sessionError);
      return NextResponse.redirect(`${origin}/auth/login?error=auth_failed`);
    }

    const user = sessionData?.user;

    if (user) {
      // Create or update auth_users record
      // This record's ID becomes the person_id used throughout the app
      try {
        const { data: existingUser, error: selectError } = await supabase
          .from("auth_users")
          .select("id, full_name")
          .eq("supabase_user_id", user.id)
          .single();

        if (selectError && selectError.code !== "PGRST116") {
          // PGRST116 = no rows found, which is fine for new users
          console.error("Error checking existing user:", selectError);
        }

        if (existingUser) {
          // Update existing user's last sign in
          const incomingFullName =
            user.user_metadata?.full_name || user.user_metadata?.name;
          const existingFullName =
            typeof existingUser.full_name === "string" && existingUser.full_name.trim()
              ? existingUser.full_name
              : null;
          const nameToStore = existingFullName || incomingFullName || null;

          await supabase
            .from("auth_users")
            .update({
              last_sign_in_at: new Date().toISOString(),
              full_name: nameToStore,
              avatar_url: user.user_metadata?.avatar_url || user.user_metadata?.picture,
            })
            .eq("id", existingUser.id);

          postAuthPath = buildPostAuthPath(existingUser.id, nameToStore);
        } else {
          // Create new auth_users record
          // The ID generated here becomes the person_id
          const { data: insertedUser, error: insertError } = await supabase
            .from("auth_users")
            .insert({
              supabase_user_id: user.id,
              email: user.email!,
              full_name: user.user_metadata?.full_name || user.user_metadata?.name,
              avatar_url: user.user_metadata?.avatar_url || user.user_metadata?.picture,
              last_sign_in_at: new Date().toISOString(),
            })
            .select("id, full_name")
            .single();

          if (insertError) {
            console.error("Error creating auth_users record:", insertError);
          } else if (insertedUser) {
            postAuthPath = buildPostAuthPath(insertedUser.id, insertedUser.full_name);
          }
        }
      } catch (err) {
        console.error("Error in auth callback:", err);
      }
    }

    const finalResponse = NextResponse.redirect(`${origin}${postAuthPath}`);
    response.cookies.getAll().forEach((cookie) => {
      finalResponse.cookies.set(cookie.name, cookie.value);
    });
    return finalResponse;
  }

  // If no code, redirect to login with error
  return NextResponse.redirect(`${origin}/auth/login?error=no_code`);
}
