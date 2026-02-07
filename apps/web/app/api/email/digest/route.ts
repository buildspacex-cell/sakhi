import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { getApiBase } from "@/lib/api-base";

export const dynamic = "force-dynamic";

/**
 * Helper: resolve person_id from Supabase auth.
 */
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
 * GET /api/email/digest
 *
 * Returns the latest email digest (auto-generates if missing).
 */
export async function GET() {
  try {
    const personId = await getPersonId();
    if (!personId) {
      return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
    }

    const apiBase = getApiBase();
    const backendResponse = await fetch(
      `${apiBase}/email/digest?person_id=${personId}`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      }
    );

    if (!backendResponse.ok) {
      return NextResponse.json({ status: "error" }, { status: backendResponse.status });
    }

    const data = await backendResponse.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error in GET /api/email/digest:", error);
    return NextResponse.json({ status: "error" }, { status: 500 });
  }
}

/**
 * POST /api/email/digest
 *
 * Force-generate a new digest.
 */
export async function POST(request: NextRequest) {
  try {
    const personId = await getPersonId();
    if (!personId) {
      return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
    }

    const background =
      request.nextUrl.searchParams.get("background") === "true";

    const apiBase = getApiBase();
    const backendResponse = await fetch(
      `${apiBase}/email/digest/generate?person_id=${personId}&background=${background}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      }
    );

    if (!backendResponse.ok) {
      return NextResponse.json({ status: "error" }, { status: backendResponse.status });
    }

    const data = await backendResponse.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error in POST /api/email/digest:", error);
    return NextResponse.json({ status: "error" }, { status: 500 });
  }
}
