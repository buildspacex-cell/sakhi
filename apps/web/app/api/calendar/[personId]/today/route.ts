import { NextRequest, NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

export const dynamic = "force-dynamic";

/**
 * GET /api/calendar/[personId]/today
 * Fetches today's calendar events for a person
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

  try {
    const response = await fetch(`${apiBase}/calendar/${personId}/today`);

    if (!response.ok) {
      return NextResponse.json(
        { error: "Failed to fetch today's events" },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error fetching today's events:", error);
    return NextResponse.json(
      { error: "Failed to connect to API" },
      { status: 500 }
    );
  }
}
