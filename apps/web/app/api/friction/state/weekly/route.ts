import { NextRequest, NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

export const dynamic = "force-dynamic";

/**
 * GET /api/friction/state/weekly
 *
 * Fetches the user's weekly state from the Friction Framework API.
 * Returns 7-day activity, trend direction, and insight.
 */
export async function GET(request: NextRequest) {
  const user = request.nextUrl.searchParams.get("user");

  if (!user) {
    return NextResponse.json({ error: "user is required" }, { status: 400 });
  }

  const apiBase = getApiBase();

  try {
    const response = await fetch(`${apiBase}/state/weekly/${user}`);

    if (!response.ok) {
      const errorText = await response.text();
      console.error("Weekly state API error:", errorText);
      return NextResponse.json(
        { error: "Failed to fetch weekly state" },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error fetching weekly state:", error);
    return NextResponse.json(
      { error: "Failed to connect to API" },
      { status: 500 }
    );
  }
}
