import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { getApiBase } from "@/lib/api-base";

export const dynamic = "force-dynamic";

/**
 * GET /api/email/insights
 *
 * Returns the most relevant surfaceable email insight for conversation context.
 */
export async function GET() {
  try {
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

    const { data: authUser, error: dbError } = await supabase
      .from("auth_users")
      .select("id")
      .eq("supabase_user_id", supabaseUser.id)
      .single();

    if (dbError || !authUser) {
      return NextResponse.json(
        { error: "User not found" },
        { status: 404 }
      );
    }

    const apiBase = getApiBase();
    const backendResponse = await fetch(
      `${apiBase}/email/insight?person_id=${authUser.id}`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      }
    );

    if (!backendResponse.ok) {
      return NextResponse.json({ has_insight: false });
    }

    const data = await backendResponse.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error in /api/email/insights:", error);
    return NextResponse.json({ has_insight: false }, { status: 500 });
  }
}
