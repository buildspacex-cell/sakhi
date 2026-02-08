import { NextRequest, NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

export const dynamic = "force-dynamic";

/**
 * POST /api/learning/plan/[planId]/pause — Pause a plan
 */
export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ planId: string }> }
) {
  const { planId } = await params;

  try {
    const response = await fetch(
      `${getApiBase()}/learning/plan/${planId}/pause`,
      { method: "POST" }
    );
    if (!response.ok) {
      return NextResponse.json(
        { error: "Failed to pause plan" },
        { status: response.status }
      );
    }
    return NextResponse.json(await response.json());
  } catch (error) {
    console.error("Error pausing plan:", error);
    return NextResponse.json(
      { error: "Failed to connect to API" },
      { status: 500 }
    );
  }
}
