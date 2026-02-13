import { NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

export const dynamic = "force-dynamic";

function parseJsonSafe(raw: string) {
  if (!raw) return {};
  try {
    return JSON.parse(raw);
  } catch {
    return { error: raw };
  }
}

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ planId: string }> }
) {
  const { planId } = await params;
  try {
    const response = await fetch(`${getApiBase()}/api/v1/agent/task/${planId}`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    const text = await response.text();
    return NextResponse.json(parseJsonSafe(text), { status: response.status });
  } catch (error) {
    console.error("[api/agent/plans/:planId] proxy error:", error);
    return NextResponse.json(
      { error: "Failed to fetch task plan" },
      { status: 500 }
    );
  }
}
