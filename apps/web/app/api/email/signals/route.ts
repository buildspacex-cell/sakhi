import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { getApiBase } from "@/lib/api-base";

export const dynamic = "force-dynamic";

/**
 * GET /api/email/signals
 *
 * Returns extracted email signals (subscriptions, avoidance, boundary, cognitive load).
 */
export async function GET(request: NextRequest) {
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
    const refresh = request.nextUrl.searchParams.get("refresh") === "true";
    const backendResponse = await fetch(
      `${apiBase}/email/signals?person_id=${authUser.id}${refresh ? "&refresh=true" : ""}`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      }
    );

    if (!backendResponse.ok) {
      return NextResponse.json({
        status: "error",
        subscriptions: [],
        avoidance: [],
        boundary: null,
        cognitive_load: null,
      });
    }

    const data = await backendResponse.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error in /api/email/signals:", error);
    return NextResponse.json(
      {
        status: "error",
        subscriptions: [],
        avoidance: [],
        boundary: null,
        cognitive_load: null,
      },
      { status: 500 }
    );
  }
}
