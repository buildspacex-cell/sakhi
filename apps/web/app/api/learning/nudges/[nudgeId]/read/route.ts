import { NextRequest, NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

export const dynamic = "force-dynamic";

/**
 * POST /api/learning/nudges/[nudgeId]/read — Mark nudge as read
 */
export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ nudgeId: string }> }
) {
  const { nudgeId } = await params;

  try {
    const response = await fetch(
      `${getApiBase()}/learning/nudges/${nudgeId}/read`,
      { method: "POST" }
    );
    if (!response.ok) {
      return NextResponse.json(
        { error: "Failed to mark nudge as read" },
        { status: response.status }
      );
    }
    return NextResponse.json(await response.json());
  } catch (error) {
    console.error("Error marking nudge as read:", error);
    return NextResponse.json(
      { error: "Failed to connect to API" },
      { status: 500 }
    );
  }
}
