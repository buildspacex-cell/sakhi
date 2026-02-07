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
 * POST /api/email/message/[id]/reply
 *
 * Send a reply to an email via Sakhi (Gmail API).
 * This is an explicit user-confirmed action — Sakhi never auto-sends.
 */
export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const personId = await getPersonId();
    if (!personId) {
      return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
    }

    const { id } = await params;
    const body = await request.json();

    const apiBase = getApiBase();
    const backendResponse = await fetch(
      `${apiBase}/email/message/${encodeURIComponent(id)}/reply?person_id=${personId}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }
    );

    if (!backendResponse.ok) {
      const errData = await backendResponse.json().catch(() => ({}));
      return NextResponse.json(
        { error: errData.detail || "Failed to send reply" },
        { status: backendResponse.status }
      );
    }

    const data = await backendResponse.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error in POST /api/email/message/[id]/reply:", error);
    return NextResponse.json({ error: "Internal error" }, { status: 500 });
  }
}
