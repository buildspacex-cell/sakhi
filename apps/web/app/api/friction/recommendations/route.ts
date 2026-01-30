import { NextRequest, NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

export const dynamic = "force-dynamic";

/**
 * GET /api/friction/recommendations
 *
 * Fetches personalized recommendations based on current friction state.
 * Uses LLM-powered generation when available, falls back to rule-based.
 */
export async function GET(request: NextRequest) {
  const user = request.nextUrl.searchParams.get("user");

  if (!user) {
    return NextResponse.json({ error: "user is required" }, { status: 400 });
  }

  const apiBase = getApiBase();

  try {
    const response = await fetch(`${apiBase}/recommendations/now/${user}`);

    if (!response.ok) {
      const errorText = await response.text();
      console.error("Recommendations API error:", errorText);
      return NextResponse.json(
        { error: "Failed to fetch recommendations" },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error fetching recommendations:", error);
    return NextResponse.json(
      { error: "Failed to connect to API" },
      { status: 500 }
    );
  }
}
