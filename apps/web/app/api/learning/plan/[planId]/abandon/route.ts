import { NextRequest, NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

export const dynamic = "force-dynamic";

/**
 * POST /api/learning/plan/[planId]/abandon — Abandon a plan
 */
export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ planId: string }> }
) {
  const { planId } = await params;
  const reason = request.nextUrl.searchParams.get("reason");

  try {
    const url = new URL(`${getApiBase()}/learning/plan/${planId}/abandon`);
    if (reason) url.searchParams.set("reason", reason);

    const response = await fetch(url.toString(), { method: "POST" });
    if (!response.ok) {
      return NextResponse.json(
        { error: "Failed to abandon plan" },
        { status: response.status }
      );
    }
    return NextResponse.json(await response.json());
  } catch (error) {
    console.error("Error abandoning plan:", error);
    return NextResponse.json(
      { error: "Failed to connect to API" },
      { status: 500 }
    );
  }
}
