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
 * POST /api/email/actions/dismiss
 *
 * Dismiss an action item from the digest.
 */
export async function POST(request: NextRequest) {
  try {
    const personId = await getPersonId();
    if (!personId) {
      return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
    }

    const body = await request.json();

    const apiBase = getApiBase();
    const backendResponse = await fetch(
      `${apiBase}/email/actions/dismiss?person_id=${personId}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }
    );

    if (!backendResponse.ok) {
      return NextResponse.json(
        { error: "Failed to dismiss" },
        { status: backendResponse.status }
      );
    }

    const data = await backendResponse.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error in POST /api/email/actions/dismiss:", error);
    return NextResponse.json({ error: "Internal error" }, { status: 500 });
  }
}
