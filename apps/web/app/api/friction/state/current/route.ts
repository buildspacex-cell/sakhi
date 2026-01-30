import { NextRequest, NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

export const dynamic = "force-dynamic";

/**
 * GET /api/friction/state/current
 *
 * Fetches the user's current state from the Friction Framework API.
 * Returns operating mode, friction state, baseline drift, and current dosha.
 */
export async function GET(request: NextRequest) {
  const user = request.nextUrl.searchParams.get("user");

  if (!user) {
    return NextResponse.json({ error: "user is required" }, { status: 400 });
  }

  const apiBase = getApiBase();

  try {
    const response = await fetch(`${apiBase}/state/current/${user}`);

    if (!response.ok) {
      const errorText = await response.text();
      console.error("Friction state API error:", errorText);
      return NextResponse.json(
        { error: "Failed to fetch current state" },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error fetching friction state:", error);
    return NextResponse.json(
      { error: "Failed to connect to API" },
      { status: 500 }
    );
  }
}
