import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

/**
 * POST /api/auth/update-name
 *
 * Saves the user's preferred name (full_name) to auth_users.
 * Used when a user enters their name during onboarding but skips
 * before the phase1 API call fires.
 */
export async function POST(req: NextRequest) {
  try {
    const { name } = (await req.json()) as { name?: string };

    if (!name || typeof name !== "string" || !name.trim()) {
      return NextResponse.json(
        { error: "name is required" },
        { status: 400 }
      );
    }

    const supabase = await createClient();
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

    const { error: updateError } = await supabase
      .from("auth_users")
      .update({ full_name: name.trim() })
      .eq("supabase_user_id", supabaseUser.id);

    if (updateError) {
      console.error("Error updating name:", updateError);
      return NextResponse.json(
        { error: "Failed to update name" },
        { status: 500 }
      );
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Error in update-name:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
