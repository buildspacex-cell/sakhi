import { NextRequest, NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";
import { createClient } from "@/lib/supabase/server";

/**
 * Onboarding completion endpoint.
 *
 * Receives the full onboarding questionnaire responses and forwards them
 * to the FastAPI backend for:
 * 1. Computing the user's Operating System (Prakruti)
 * 2. Storing life context, decision patterns, and preferences
 * 3. Initializing the personal model
 *
 * Also marks the user's onboarding as completed in auth_users.
 */

type OnboardingBody = {
  user_id?: string;
  responses: Record<string, string | string[]>;
  completed_at: string;
};

export async function POST(req: NextRequest) {
  const body = (await req.json()) as OnboardingBody;

  // Get user from query param or body
  const userParam = req.nextUrl.searchParams.get("user");
  const userId = body.user_id || userParam;

  if (!userId) {
    return NextResponse.json(
      { error: "user_id is required" },
      { status: 400 }
    );
  }

  // Require authenticated user and ensure the provided userId belongs to them
  const supabase = await createClient();
  const {
    data: { user: supabaseUser },
    error: authError,
  } = await supabase.auth.getUser();

  if (authError || !supabaseUser) {
    return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
  }

  // Verify the person_id maps to the current Supabase user
  const { data: authUser, error: authUserError } = await supabase
    .from("auth_users")
    .select("id")
    .eq("id", userId)
    .single();

  if (authUserError || !authUser) {
    const status = authUserError?.code === "PGRST116" ? 403 : 500;
    return NextResponse.json(
      { error: "Invalid user" },
      { status }
    );
  }

  const apiBase = getApiBase();

  try {
    // Forward to FastAPI onboarding endpoint
    const response = await fetch(`${apiBase}/onboarding/complete`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        person_id: userId,
        responses: body.responses,
        completed_at: body.completed_at,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(
        { error: data.detail || "Onboarding failed" },
        { status: response.status }
      );
    }

    // Mark onboarding as completed in auth_users table
    try {
      const updates: Record<string, string> = { onboarding_completed_at: body.completed_at };
      const preferredName = body.responses?.preferred_name;
      if (typeof preferredName === "string" && preferredName.trim()) {
        updates.full_name = preferredName.trim();
      }
      await supabase
        .from("auth_users")
        .update(updates)
        .eq("id", userId);
    } catch (dbError) {
      // Log but don't fail the request if this update fails
      console.error("Error updating onboarding status:", dbError);
    }

    return NextResponse.json({
      ok: true,
      user_id: userId,
      operating_system: data.operating_system,
      primary: data.primary,
      secondary: data.secondary,
      dosha_baseline: data.dosha_baseline,
      life_context: data.life_context,
      decision_profile: data.decision_profile,
      stored: data.stored,
    });
  } catch (error) {
    console.error("Onboarding API error:", error);
    return NextResponse.json(
      { error: "Failed to complete onboarding" },
      { status: 500 }
    );
  }
}
