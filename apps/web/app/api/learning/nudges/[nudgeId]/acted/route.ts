import { NextRequest, NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

export const dynamic = "force-dynamic";

/**
 * POST /api/learning/nudges/[nudgeId]/acted — Mark nudge as acted upon
 */
export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ nudgeId: string }> }
) {
  const { nudgeId } = await params;

  try {
    const response = await fetch(
      `${getApiBase()}/learning/nudges/${nudgeId}/acted`,
      { method: "POST" }
    );
    if (!response.ok) {
      return NextResponse.json(
        { error: "Failed to mark nudge as acted" },
        { status: response.status }
      );
    }
    return NextResponse.json(await response.json());
  } catch (error) {
    console.error("Error marking nudge as acted:", error);
    return NextResponse.json(
      { error: "Failed to connect to API" },
      { status: 500 }
    );
  }
}
