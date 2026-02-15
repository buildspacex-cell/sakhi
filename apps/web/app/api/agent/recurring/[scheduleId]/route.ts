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

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ scheduleId: string }> }
) {
  const { scheduleId } = await params;
  const personId = request.nextUrl.searchParams.get("person_id");
  if (!personId) {
    return NextResponse.json(
      { error: "person_id is required" },
      { status: 400 }
    );
  }

  try {
    const response = await fetch(
      `${getApiBase()}/api/v1/agent/recurring/${encodeURIComponent(scheduleId)}?person_id=${encodeURIComponent(personId)}`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      }
    );
    const text = await response.text();
    return NextResponse.json(parseJsonSafe(text), { status: response.status });
  } catch (error) {
    console.error("[api/agent/recurring/:scheduleId] proxy error:", error);
    return NextResponse.json(
      { error: "Failed to fetch recurring schedule" },
      { status: 500 }
    );
  }
}
