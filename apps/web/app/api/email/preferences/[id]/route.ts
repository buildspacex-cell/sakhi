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
 * DELETE /api/email/preferences/[id]
 *
 * Delete a contact preference.
 */
export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const personId = await getPersonId();
    if (!personId) {
      return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
    }

    const { id } = await params;

    const apiBase = getApiBase();
    const backendResponse = await fetch(
      `${apiBase}/email/preferences/${encodeURIComponent(id)}?person_id=${personId}`,
      {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
      }
    );

    if (!backendResponse.ok) {
      const errData = await backendResponse.json().catch(() => ({}));
      return NextResponse.json(
        { error: errData.detail || "Failed to delete preference" },
        { status: backendResponse.status }
      );
    }

    const data = await backendResponse.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error in DELETE /api/email/preferences/[id]:", error);
    return NextResponse.json({ error: "Internal error" }, { status: 500 });
  }
}
