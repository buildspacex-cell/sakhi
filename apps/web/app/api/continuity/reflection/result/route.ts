import { NextRequest, NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  try {
    const apiBase = getApiBase();
    const url = new URL(request.url);
    const target = new URL(`${apiBase}/continuity/reflection/result`);
    url.searchParams.forEach((value, key) => {
      target.searchParams.set(key, value);
    });
    const res = await fetch(target.toString(), { method: "GET", cache: "no-store" });
    const data = await res.json();
    return NextResponse.json(data, {
      status: res.status,
      headers: { "Cache-Control": "no-store, no-cache, must-revalidate" },
    });
  } catch (error) {
    console.error("Error in /api/continuity/reflection/result:", error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unknown error" },
      { status: 500 },
    );
  }
}
