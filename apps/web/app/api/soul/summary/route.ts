import { NextRequest, NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

export const dynamic = "force-dynamic";

/**
 * GET /api/soul/summary
 *
 * Fetches the user's soul summary from the backend.
 * Returns soul_light, soul_shadow, soul_friction, and coherence.
 */
export async function GET(request: NextRequest) {
  const user = request.nextUrl.searchParams.get("user");

  if (!user) {
    return NextResponse.json({ error: "user is required" }, { status: 400 });
  }

  const apiBase = getApiBase();

  try {
    const response = await fetch(`${apiBase}/soul/summary/${user}`);

    if (!response.ok) {
      const errorText = await response.text();
      console.error("Soul summary API error:", errorText);
      return NextResponse.json(
        { error: "Failed to fetch soul summary" },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error fetching soul summary:", error);
    return NextResponse.json(
      { error: "Failed to connect to API" },
      { status: 500 }
    );
  }
}
