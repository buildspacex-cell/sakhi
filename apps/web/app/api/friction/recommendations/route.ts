import { NextRequest, NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

export const dynamic = "force-dynamic";

/**
 * GET /api/friction/recommendations
 *
 * Fetches truly personalized recommendations based on:
 * - Ayurvedic knowledge graph
 * - Personal patterns (what's worked for YOU)
 * - Current friction state and drift
 * - Historical effectiveness
 */
export async function GET(request: NextRequest) {
  const user = request.nextUrl.searchParams.get("user");

  if (!user) {
    return NextResponse.json({ error: "user is required" }, { status: 400 });
  }

  const apiBase = getApiBase();

  try {
    // Use personalized recommendations endpoint for richer data
    const response = await fetch(
      `${apiBase}/recommendations/personalized/${user}?max_foods=5&max_practices=5`
    );

    if (!response.ok) {
      // Fall back to basic recommendations if personalized fails
      console.warn("Personalized recommendations unavailable, falling back");
      const fallbackResponse = await fetch(
        `${apiBase}/recommendations/now/${user}`
      );
      if (!fallbackResponse.ok) {
        return NextResponse.json(
          { error: "Failed to fetch recommendations" },
          { status: fallbackResponse.status }
        );
      }
      const fallbackData = await fallbackResponse.json();
      return NextResponse.json(fallbackData);
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
