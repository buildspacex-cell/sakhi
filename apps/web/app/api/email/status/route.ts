import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { getApiBase } from "@/lib/api-base";

export const dynamic = "force-dynamic";

/**
 * GET /api/email/status
 *
 * Returns the email sync status for the authenticated user.
 */
export async function GET(request: NextRequest) {
  try {
    // Get the authenticated user
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

    // Get the person_id from auth_users
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

    // Forward to the backend API
    const apiBase = getApiBase();
    const backendResponse = await fetch(
      `${apiBase}/email/status?person_id=${authUser.id}`,
      {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
        },
      }
    );

    if (!backendResponse.ok) {
      // If 404 or error, return not connected
      return NextResponse.json({
        connected: false,
        status: "not_connected",
      });
    }

    const data = await backendResponse.json();

    return NextResponse.json(data);
  } catch (error) {
    console.error("Error in /api/email/status:", error);
    return NextResponse.json(
      {
        connected: false,
        status: "error",
        error: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}
