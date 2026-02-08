import { NextRequest, NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

export const dynamic = "force-dynamic";

/**
 * POST /api/learning/plan/[planId]/complete — Mark plan as completed
 */
export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ planId: string }> }
) {
  const { planId } = await params;

  try {
    const response = await fetch(
      `${getApiBase()}/learning/plan/${planId}/complete`,
      { method: "POST" }
    );
    if (!response.ok) {
      return NextResponse.json(
        { error: "Failed to complete plan" },
        { status: response.status }
      );
    }
    return NextResponse.json(await response.json());
  } catch (error) {
    console.error("Error completing plan:", error);
    return NextResponse.json(
      { error: "Failed to connect to API" },
      { status: 500 }
    );
  }
}
