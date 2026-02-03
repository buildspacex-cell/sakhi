import { NextRequest, NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

const API_KEY =
  process.env.NEXT_PUBLIC_API_KEY || process.env.EXPO_PUBLIC_API_KEY || "";

/**
 * POST /api/missions - Create a new mission
 * Proxies to the backend mission creation endpoint
 */
export async function POST(request: NextRequest) {
  const API_BASE = getApiBase();
  const searchParams = request.nextUrl.searchParams;
  const personId = searchParams.get("person_id");

  if (!personId) {
    return NextResponse.json(
      { error: "person_id query parameter is required" },
      { status: 400 }
    );
  }

  try {
    const body = await request.json();

    const response = await fetch(`${API_BASE}/missions?person_id=${personId}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY,
      },
      body: JSON.stringify(body),
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error("[api/missions] Error creating mission:", error);
    return NextResponse.json(
      { error: "Failed to create mission" },
      { status: 500 }
    );
  }
}

/**
 * GET /api/missions - List missions for a person
 * Proxies to the backend mission list endpoint
 */
export async function GET(request: NextRequest) {
  const API_BASE = getApiBase();
  const searchParams = request.nextUrl.searchParams;
  const personId = searchParams.get("person_id");

  if (!personId) {
    return NextResponse.json(
      { error: "person_id query parameter is required" },
      { status: 400 }
    );
  }

  try {
    const response = await fetch(`${API_BASE}/missions?person_id=${personId}`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY,
      },
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error("[api/missions] Error fetching missions:", error);
    return NextResponse.json(
      { error: "Failed to fetch missions" },
      { status: 500 }
    );
  }
}
