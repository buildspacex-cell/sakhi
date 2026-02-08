import { NextRequest, NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

export const dynamic = "force-dynamic";

/**
 * GET /api/learning/plan — Get active intervention plans
 * POST /api/learning/plan — Create a new intervention plan
 */
export async function GET(request: NextRequest) {
  const user = request.nextUrl.searchParams.get("user");
  if (!user) {
    return NextResponse.json({ error: "user is required" }, { status: 400 });
  }

  try {
    const response = await fetch(
      `${getApiBase()}/learning/plan/active?person_id=${user}`
    );
    if (!response.ok) {
      return NextResponse.json(
        { error: "Failed to fetch active plans" },
        { status: response.status }
      );
    }
    return NextResponse.json(await response.json());
  } catch (error) {
    console.error("Error fetching active plans:", error);
    return NextResponse.json(
      { error: "Failed to connect to API" },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const response = await fetch(`${getApiBase()}/learning/plan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      const err = await response.text();
      return NextResponse.json(
        { error: err || "Failed to create plan" },
        { status: response.status }
      );
    }
    return NextResponse.json(await response.json());
  } catch (error) {
    console.error("Error creating plan:", error);
    return NextResponse.json(
      { error: "Failed to connect to API" },
      { status: 500 }
    );
  }
}
