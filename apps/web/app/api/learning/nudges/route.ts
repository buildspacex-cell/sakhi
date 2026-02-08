import { NextRequest, NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

export const dynamic = "force-dynamic";

/**
 * GET /api/learning/nudges — Get today's nudges
 */
export async function GET(request: NextRequest) {
  const user = request.nextUrl.searchParams.get("user");
  if (!user) {
    return NextResponse.json({ error: "user is required" }, { status: 400 });
  }

  try {
    const response = await fetch(
      `${getApiBase()}/learning/nudges?person_id=${user}`
    );
    if (!response.ok) {
      return NextResponse.json(
        { error: "Failed to fetch nudges" },
        { status: response.status }
      );
    }
    return NextResponse.json(await response.json());
  } catch (error) {
    console.error("Error fetching nudges:", error);
    return NextResponse.json(
      { error: "Failed to connect to API" },
      { status: 500 }
    );
  }
}
