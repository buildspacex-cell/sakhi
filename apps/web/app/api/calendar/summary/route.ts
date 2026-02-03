import { NextRequest, NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

export const dynamic = "force-dynamic";

/**
 * GET /api/calendar/summary
 * Fetches week summary with energy predictions
 */
export async function GET(request: NextRequest) {
  const user = request.nextUrl.searchParams.get("user");

  if (!user) {
    return NextResponse.json({ error: "user is required" }, { status: 400 });
  }

  const apiBase = getApiBase();

  try {
    const response = await fetch(`${apiBase}/calendar/summary?person_id=${user}`);

    if (!response.ok) {
      return NextResponse.json(
        { error: "Failed to fetch summary" },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error fetching summary:", error);
    return NextResponse.json(
      { error: "Failed to connect to API" },
      { status: 500 }
    );
  }
}
