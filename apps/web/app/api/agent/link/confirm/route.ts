import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { getApiBase } from "@/lib/api-base";

export const dynamic = "force-dynamic";

/**
 * POST /api/agent/link/confirm
 *
 * Confirms a device link code, connecting a desktop agent to the user's account.
 * Proxies the request to the backend API with the user's authentication.
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
        { error: "Not authenticated", detail: "Please sign in to link a device" },
        { status: 401 }
      );
    }

    // Get the person_id from auth_users
    const { data: authUser, error: dbError } = await supabase
      .from("auth_users")
      .select("id, full_name")
      .eq("supabase_user_id", supabaseUser.id)
      .single();

    if (dbError || !authUser) {
      return NextResponse.json(
        { error: "User not found", detail: "User record not found" },
        { status: 404 }
      );
    }

    // Parse the request body
    const body = await request.json();
    const { code } = body;

    if (!code || typeof code !== "string") {
      return NextResponse.json(
        { error: "Invalid request", detail: "Missing or invalid link code" },
        { status: 400 }
      );
    }

    // Forward to the backend API
    const apiBase = getApiBase();
    if (!apiBase) {
      console.error("Missing API_BASE_URL");
      return NextResponse.json(
        { error: "Configuration error", detail: "API not configured" },
        { status: 500 }
      );
    }

    const backendResponse = await fetch(`${apiBase}/api/v1/agent/link/confirm`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Person-Id": authUser.id,
      },
      body: JSON.stringify({ code }),
    });

    if (!backendResponse.ok) {
      const errorData = await backendResponse.json().catch(() => ({}));
      return NextResponse.json(
        {
          error: "Link failed",
          detail: errorData.detail || `Backend error: ${backendResponse.status}`
        },
        { status: backendResponse.status }
      );
    }

    const data = await backendResponse.json();

    // Return success with user info
    return NextResponse.json({
      success: true,
      agent_id: data.agent_id,
      agent_name: data.agent_name,
      platform: data.platform,
      user_name: authUser.full_name,
    });

  } catch (error) {
    console.error("Error in /api/agent/link/confirm:", error);
    return NextResponse.json(
      {
        error: "Internal server error",
        detail: error instanceof Error ? error.message : "Unknown error"
      },
      { status: 500 }
    );
  }
}
