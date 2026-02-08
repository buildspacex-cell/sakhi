import { NextRequest, NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

export const dynamic = "force-dynamic";

/**
 * POST /api/learning/plan/checkin — Record a check-in
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const response = await fetch(`${getApiBase()}/learning/plan/checkin`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      const err = await response.text();
      return NextResponse.json(
        { error: err || "Failed to record check-in" },
        { status: response.status }
      );
    }
    return NextResponse.json(await response.json());
  } catch (error) {
    console.error("Error recording check-in:", error);
    return NextResponse.json(
      { error: "Failed to connect to API" },
      { status: 500 }
    );
  }
}
