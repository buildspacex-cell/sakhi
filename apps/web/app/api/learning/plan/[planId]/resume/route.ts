import { NextRequest, NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

export const dynamic = "force-dynamic";

/**
 * POST /api/learning/plan/[planId]/resume — Resume a paused plan
 */
export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ planId: string }> }
) {
  const { planId } = await params;

  try {
    const response = await fetch(
      `${getApiBase()}/learning/plan/${planId}/resume`,
      { method: "POST" }
    );
    if (!response.ok) {
      return NextResponse.json(
        { error: "Failed to resume plan" },
        { status: response.status }
      );
    }
    return NextResponse.json(await response.json());
  } catch (error) {
    console.error("Error resuming plan:", error);
    return NextResponse.json(
      { error: "Failed to connect to API" },
      { status: 500 }
    );
  }
}
