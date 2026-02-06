import { NextRequest, NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

export const dynamic = "force-dynamic";

/**
 * GET /api/calendar/[personId]/events
 * Fetches calendar events for a person
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ personId: string }> }
) {
  const { personId } = await params;

  if (!personId) {
    return NextResponse.json({ error: "personId is required" }, { status: 400 });
  }

  const apiBase = getApiBase();
  const searchParams = request.nextUrl.searchParams;
  const limit = searchParams.get("limit") || "50";
  const start = searchParams.get("start");
  const end = searchParams.get("end");
  const eventType = searchParams.get("event_type");

  try {
    const queryParams = new URLSearchParams({ limit });
    if (start) queryParams.append("start", start);
    if (end) queryParams.append("end", end);
    if (eventType) queryParams.append("event_type", eventType);

    const response = await fetch(
      `${apiBase}/calendar/${personId}/events?${queryParams.toString()}`
    );

    if (!response.ok) {
      return NextResponse.json(
        { error: "Failed to fetch events" },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error fetching events:", error);
    return NextResponse.json(
      { error: "Failed to connect to API" },
      { status: 500 }
    );
  }
}
