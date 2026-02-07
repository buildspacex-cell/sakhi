import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { getApiBase } from "@/lib/api-base";

export const dynamic = "force-dynamic";

/**
 * POST /api/email/disconnect
 *
 * Disconnects the user's email account and deletes all email data.
 */
export async function POST() {
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
      `${apiBase}/email/disconnect?person_id=${authUser.id}`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      }
    );

    if (!backendResponse.ok) {
      const errorData = await backendResponse.json().catch(() => ({}));
      return NextResponse.json(
        {
          error: "Disconnect failed",
          detail: errorData.detail || `Backend error: ${backendResponse.status}`,
        },
        { status: backendResponse.status }
      );
    }

    const data = await backendResponse.json();

    return NextResponse.json({
      success: true,
      status: data.status || "disconnected",
    });
  } catch (error) {
    console.error("Error in /api/email/disconnect:", error);
    return NextResponse.json(
      {
        error: "Internal server error",
        detail: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}
