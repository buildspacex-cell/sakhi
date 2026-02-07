import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { getApiBase } from "@/lib/api-base";

export const dynamic = "force-dynamic";

/**
 * POST /api/email/connect/gmail
 *
 * Initiates Gmail OAuth flow. Returns the Google auth URL to redirect to.
 */
export async function POST(request: NextRequest) {
  try {
    // Get the authenticated user
    const supabase = await createClient();
    const {
      data: { user: supabaseUser },
      error: authError,
    } = await supabase.auth.getUser();

    if (authError || !supabaseUser) {
      return NextResponse.json(
        { error: "Not authenticated", detail: "Please sign in to connect Gmail" },
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
        { error: "User not found", detail: "User record not found" },
        { status: 404 }
      );
    }

    // Get the app redirect URI from request body
    const body = await request.json().catch(() => ({}));
    const appRedirectUri = body.app_redirect_uri || `${request.nextUrl.origin}/experience/me`;

    // Forward to the backend API
    const apiBase = getApiBase();
    const backendResponse = await fetch(
      `${apiBase}/email/connect/gmail?person_id=${authUser.id}`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ app_redirect_uri: appRedirectUri }),
      }
    );

    if (!backendResponse.ok) {
      const errorData = await backendResponse.json().catch(() => ({}));
      return NextResponse.json(
        {
          error: "Connection failed",
          detail: errorData.detail || `Backend error: ${backendResponse.status}`,
        },
        { status: backendResponse.status }
      );
    }

    const data = await backendResponse.json();

    return NextResponse.json({
      auth_url: data.auth_url,
      state: data.state,
    });
  } catch (error) {
    console.error("Error in /api/email/connect/gmail:", error);
    return NextResponse.json(
      {
        error: "Internal server error",
        detail: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}
