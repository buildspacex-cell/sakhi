import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

/**
 * GET /api/auth/me
 *
 * Returns the current authenticated user's info including their person_id.
 * The person_id is from the auth_users table, not the Supabase user ID.
 */
export async function GET(request: NextRequest) {
  try {
    const supabase = await createClient();

    // Get the authenticated Supabase user
    const {
      data: { user: supabaseUser },
      error: authError,
    } = await supabase.auth.getUser();

    if (authError || !supabaseUser) {
      return NextResponse.json(
        { error: "Not authenticated" },
        { status: 401 }
      );
    }

    // Fetch the auth_users record to get the person_id
    const { data: authUser, error: dbError } = await supabase
      .from("auth_users")
      .select("id, email, full_name, avatar_url, onboarding_completed_at")
      .eq("supabase_user_id", supabaseUser.id)
      .single();

    if (dbError) {
      // If no auth_users record exists, create one
      if (dbError.code === "PGRST116") {
        // Use service role for initial creation to bypass RLS during bootstrap
        const serviceSupabase = await createClient({ useServiceRole: true });
        const { data: newUser, error: insertError } = await serviceSupabase
          .from("auth_users")
          .insert({
            supabase_user_id: supabaseUser.id,
            email: supabaseUser.email!,
            full_name:
              supabaseUser.user_metadata?.full_name ||
              supabaseUser.user_metadata?.name,
            avatar_url:
              supabaseUser.user_metadata?.avatar_url ||
              supabaseUser.user_metadata?.picture,
            last_sign_in_at: new Date().toISOString(),
          })
          .select("id, email, full_name, avatar_url, onboarding_completed_at")
          .single();

        if (insertError) {
          console.error("Error creating auth_users record:", insertError);
          return NextResponse.json(
            { error: "Failed to create user record" },
            { status: 500 }
          );
        }

        return NextResponse.json({
          person_id: newUser.id,
          email: newUser.email,
          full_name: newUser.full_name,
          avatar_url: newUser.avatar_url,
          onboarding_completed: !!newUser.onboarding_completed_at,
        });
      }

      console.error("Error fetching auth_users:", dbError);
      return NextResponse.json(
        { error: "Failed to fetch user" },
        { status: 500 }
      );
    }

    return NextResponse.json({
      person_id: authUser.id,
      email: authUser.email,
      full_name: authUser.full_name,
      avatar_url: authUser.avatar_url,
      onboarding_completed: !!authUser.onboarding_completed_at,
    });
  } catch (error) {
    console.error("Error in /api/auth/me:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
