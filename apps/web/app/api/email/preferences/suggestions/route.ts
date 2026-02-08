import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { getApiBase } from "@/lib/api-base";

export const dynamic = "force-dynamic";

async function getPersonId() {
  const supabase = await createClient();
  const {
    data: { user: supabaseUser },
    error: authError,
  } = await supabase.auth.getUser();

  if (authError || !supabaseUser) return null;

  const { data: authUser, error: dbError } = await supabase
    .from("auth_users")
    .select("id")
    .eq("supabase_user_id", supabaseUser.id)
    .single();

  if (dbError || !authUser) return null;
  return authUser.id as string;
}

/**
 * GET /api/email/preferences/suggestions
 *
 * Returns Sakhi's suggestions for contact priorities based on dismiss patterns.
 */
export async function GET() {
  try {
    const personId = await getPersonId();
    if (!personId) {
      return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
    }

    const apiBase = getApiBase();
    const backendResponse = await fetch(
      `${apiBase}/email/preferences/suggestions?person_id=${personId}`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      }
    );

    if (!backendResponse.ok) {
      return NextResponse.json(
        { suggestions: [] },
        { status: backendResponse.status }
      );
    }

    const data = await backendResponse.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error in GET /api/email/preferences/suggestions:", error);
    return NextResponse.json({ suggestions: [] }, { status: 500 });
  }
}
