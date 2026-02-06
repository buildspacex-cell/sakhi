import { NextRequest, NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

export const dynamic = "force-dynamic";

/**
 * GET /api/relationships/[personId]/needing-attention
 * Fetches relationships that need reconnection
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ personId: string }> }
) {
  const { personId } = await params;

  if (!personId) {
    return NextResponse.json({ error: "personId is required" }, { status: 400 });
  }

  const apiBase = getApiBase();
  const searchParams = request.nextUrl.searchParams;
  const limit = searchParams.get("limit") || "5";

  try {
    const response = await fetch(
      `${apiBase}/relationships/${personId}/needing-attention?limit=${limit}`
    );

    if (!response.ok) {
      return NextResponse.json(
        { error: "Failed to fetch relationships" },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error fetching relationships:", error);
    return NextResponse.json(
      { error: "Failed to connect to API" },
      { status: 500 }
    );
  }
}
