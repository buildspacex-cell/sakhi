import { NextRequest, NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

export const dynamic = "force-dynamic";

function parseJsonSafe(raw: string) {
  if (!raw) return {};
  try {
    return JSON.parse(raw);
  } catch {
    return { error: raw };
  }
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ scheduleId: string }> }
) {
  const { scheduleId } = await params;
  try {
    const body = await request.json();
    const personId = typeof body?.person_id === "string" ? body.person_id : "";
    if (!personId) {
      return NextResponse.json(
        { error: "person_id is required" },
        { status: 400 }
      );
    }

    const response = await fetch(
      `${getApiBase()}/api/v1/agent/recurring/${encodeURIComponent(scheduleId)}/approve?person_id=${encodeURIComponent(personId)}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      }
    );
    const text = await response.text();
    return NextResponse.json(parseJsonSafe(text), { status: response.status });
  } catch (error) {
    console.error("[api/agent/recurring/:scheduleId/approve] proxy error:", error);
    return NextResponse.json(
      { error: "Failed to approve recurring schedule" },
      { status: 500 }
    );
  }
}
