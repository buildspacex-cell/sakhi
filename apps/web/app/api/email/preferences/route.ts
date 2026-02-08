import { NextRequest, NextResponse } from "next/server";
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
 * GET /api/email/preferences
 *
 * Returns contact preferences sorted by priority.
 */
export async function GET() {
  try {
    const personId = await getPersonId();
    if (!personId) {
      return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
    }

    const apiBase = getApiBase();
    const backendResponse = await fetch(
      `${apiBase}/email/preferences?person_id=${personId}`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      }
    );

    if (!backendResponse.ok) {
      return NextResponse.json(
        { preferences: [] },
        { status: backendResponse.status }
      );
    }

    const data = await backendResponse.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error in GET /api/email/preferences:", error);
    return NextResponse.json({ preferences: [] }, { status: 500 });
  }
}

/**
 * PUT /api/email/preferences
 *
 * Create or update a contact preference (upserts on contact_identifier + channel).
 */
export async function PUT(request: NextRequest) {
  try {
    const personId = await getPersonId();
    if (!personId) {
      return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
    }

    const body = await request.json();

    const apiBase = getApiBase();
    const backendResponse = await fetch(
      `${apiBase}/email/preferences?person_id=${personId}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }
    );

    if (!backendResponse.ok) {
      const errData = await backendResponse.json().catch(() => ({}));
      return NextResponse.json(
        { error: errData.detail || "Failed to save preference" },
        { status: backendResponse.status }
      );
    }

    const data = await backendResponse.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error in PUT /api/email/preferences:", error);
    return NextResponse.json({ error: "Internal error" }, { status: 500 });
  }
}
