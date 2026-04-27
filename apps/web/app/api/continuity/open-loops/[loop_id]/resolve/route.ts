import { NextRequest, NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

export const dynamic = "force-dynamic";

export async function POST(
  _request: NextRequest,
  { params }: { params: { loop_id: string } },
) {
  try {
    const apiBase = getApiBase();
    const target = `${apiBase}/continuity/open-loops/${params.loop_id}/resolve`;
    const res = await fetch(target, { method: "POST" });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    console.error("Error in /api/continuity/open-loops/[loop_id]/resolve:", error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unknown error" },
      { status: 500 },
    );
  }
}
