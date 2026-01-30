import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

/**
 * POST /api/dev/reset-onboarding
 *
 * Resets onboarding status for the current authenticated user.
 * DEV ONLY - remove or protect in production.
 */
export async function POST(request: NextRequest) {
  // Only allow in development
  if (process.env.NODE_ENV === "production") {
    return NextResponse.json(
      { error: "Not available in production" },
      { status: 403 }
    );
  }

  try {
    const supabase = await createClient();

    // Get the authenticated user
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

    // Use service role to update auth_users
    const serviceSupabase = await createClient({ useServiceRole: true });

    const { data, error } = await serviceSupabase
      .from("auth_users")
      .update({ onboarding_completed_at: null })
      .eq("supabase_user_id", supabaseUser.id)
      .select("id, email, onboarding_completed_at")
      .single();

    if (error) {
      console.error("Error resetting onboarding:", error);
      return NextResponse.json(
        { error: "Failed to reset onboarding" },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      message: "Onboarding reset. Refresh the page to start over.",
      user: {
        person_id: data.id,
        email: data.email,
        onboarding_completed: false,
      },
    });
  } catch (error) {
    console.error("Error in reset-onboarding:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
