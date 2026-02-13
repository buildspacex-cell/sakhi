import { NextRequest, NextResponse } from "next/server";
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

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const response = await fetch(`${getApiBase()}/learning/companion/protocol/complete`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const text = await response.text();
    return NextResponse.json(parseJsonSafe(text), { status: response.status });
  } catch (error) {
    console.error("[api/learning/companion/protocol/complete] proxy error:", error);
    return NextResponse.json(
      { error: "Failed to log protocol completion" },
      { status: 500 }
    );
  }
}
