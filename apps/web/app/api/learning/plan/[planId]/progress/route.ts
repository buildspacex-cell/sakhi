import { NextRequest, NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

export const dynamic = "force-dynamic";

/**
 * GET /api/learning/plan/[planId]/progress — Get plan progress
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ planId: string }> }
) {
  const { planId } = await params;

  try {
    const response = await fetch(
      `${getApiBase()}/learning/plan/${planId}/progress`
    );
    if (!response.ok) {
      return NextResponse.json(
        { error: "Failed to fetch plan progress" },
        { status: response.status }
      );
    }
    return NextResponse.json(await response.json());
  } catch (error) {
    console.error("Error fetching plan progress:", error);
    return NextResponse.json(
      { error: "Failed to connect to API" },
      { status: 500 }
    );
  }
}
