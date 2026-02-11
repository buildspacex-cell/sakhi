import { NextRequest, NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";
import { createClient } from "@/lib/supabase/server";

/**
 * Phase-based onboarding submission endpoint.
 *
 * Receives partial onboarding responses for a specific phase (phase1, phase2a, phase2b)
 * and forwards them to the FastAPI backend for progressive OS computation.
 *
 * Returns the computed Operating System result after each phase.
 */

type OnboardingSubmitBody = {
  phase: "phase1" | "phase2a" | "phase2b";
  responses: Record<string, string | string[]>;
  completed_at: string;
};

export async function POST(req: NextRequest) {
  const body = (await req.json()) as OnboardingSubmitBody;

  if (!body.phase || !body.responses) {
    return NextResponse.json(
      { error: "phase and responses are required" },
      { status: 400 }
    );
  }

  // Get authenticated user from Supabase cookies
  const supabase = await createClient();
  const {
    data: { user: supabaseUser },
    error: authError,
  } = await supabase.auth.getUser();

  if (authError || !supabaseUser) {
    return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
  }

  // Look up person_id from auth_users
  const { data: authUser, error: authUserError } = await supabase
    .from("auth_users")
    .select("id")
    .eq("supabase_user_id", supabaseUser.id)
    .single();

  if (authUserError || !authUser) {
    // Fallback: try matching by id directly
    const { data: authUserById } = await supabase
      .from("auth_users")
      .select("id")
      .eq("id", supabaseUser.id)
      .single();

    if (!authUserById) {
      return NextResponse.json({ error: "User not found" }, { status: 403 });
    }

    return await forwardToBackend(authUserById.id, body, supabase);
  }

  return await forwardToBackend(authUser.id, body, supabase);
}

async function forwardToBackend(
  personId: string,
  body: OnboardingSubmitBody,
  supabase: Awaited<ReturnType<typeof createClient>>
) {
  const apiBase = getApiBase();

  try {
    const response = await fetch(`${apiBase}/onboarding/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        person_id: personId,
        source: "web",
        phase: body.phase,
        responses: body.responses,
        completed_at: body.completed_at,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(
        { error: data.detail || "Onboarding submission failed" },
        { status: response.status }
      );
    }

    // On final phase or if user completes, mark onboarding_completed_at
    if (body.phase === "phase2b" || (data.phases_remaining && data.phases_remaining.length === 0)) {
      try {
        const updates: Record<string, string> = {
          onboarding_completed_at: body.completed_at,
        };
        const preferredName = body.responses?.preferred_name;
        if (typeof preferredName === "string" && preferredName.trim()) {
          updates.full_name = preferredName.trim();
        }
        await supabase
          .from("auth_users")
          .update(updates)
          .eq("id", personId);
      } catch (dbError) {
        console.error("Error updating onboarding status:", dbError);
      }
    }

    // Also update preferred_name on phase1 if provided
    if (body.phase === "phase1" && body.responses?.preferred_name) {
      try {
        const name = body.responses.preferred_name;
        if (typeof name === "string" && name.trim()) {
          await supabase
            .from("auth_users")
            .update({ full_name: name.trim() })
            .eq("id", personId);
        }
      } catch (dbError) {
        console.error("Error updating preferred name:", dbError);
      }
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error("Onboarding submit API error:", error);
    return NextResponse.json(
      { error: "Failed to submit onboarding" },
      { status: 500 }
    );
  }
}
