import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

// Backend API base URL
const API_BASE = process.env.SAKHI_API_URL || "http://127.0.0.1:8080";

/**
 * POST /api/dev/reset-user-data
 *
 * Resets ALL data for a given person_id across all tables.
 * DEV ONLY - this is destructive!
 *
 * Body: { person_id: string }
 */
export async function POST(request: NextRequest) {
  // Only allow in development
  if (process.env.NODE_ENV === "production") {
    return NextResponse.json(
      { error: "Not available in production" },
      { status: 403 }
    );
  }

  try {
    const body = await request.json();
    const { person_id } = body;

    if (!person_id) {
      return NextResponse.json(
        { error: "person_id is required" },
        { status: 400 }
      );
    }

    // Call the backend reset endpoint
    const res = await fetch(`${API_BASE}/dev/reset-user-data`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ person_id }),
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    console.error("Error in reset-user-data:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
