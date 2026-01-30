import { NextRequest, NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

/**
 * Fetch user's Operating System profile from the FastAPI backend.
 */
export async function GET(req: NextRequest) {
  const userParam = req.nextUrl.searchParams.get("user");

  if (!userParam) {
    return NextResponse.json(
      { error: "user parameter is required" },
      { status: 400 }
    );
  }

  const apiBase = getApiBase();

  try {
    const response = await fetch(
      `${apiBase}/profile/operating-system/${encodeURIComponent(userParam)}`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      }
    );

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(
        { error: data.detail || "Failed to fetch Operating System" },
        { status: response.status }
      );
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error("Operating System API error:", error);
    return NextResponse.json(
      { error: "Failed to connect to server" },
      { status: 500 }
    );
  }
}
