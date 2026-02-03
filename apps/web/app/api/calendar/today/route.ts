import { NextRequest, NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

export const dynamic = "force-dynamic";

/**
 * GET /api/calendar/today
 * Fetches today's calendar events with relationship context
 */
export async function GET(request: NextRequest) {
  const user = request.nextUrl.searchParams.get("user");

  if (!user) {
    return NextResponse.json({ error: "user is required" }, { status: 400 });
  }

  const apiBase = getApiBase();

  try {
    const response = await fetch(`${apiBase}/calendar/today?person_id=${user}`);

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
