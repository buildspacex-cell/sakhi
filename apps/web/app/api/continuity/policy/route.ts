import { NextRequest, NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  try {
    const apiBase = getApiBase();
    const url = new URL(request.url);
    const personId = url.searchParams.get("person_id");
    const scope = url.searchParams.get("scope");
    const target = new URL(`${apiBase}/continuity/policy`);
    if (personId) target.searchParams.set("person_id", personId);
    if (scope) target.searchParams.set("scope", scope);
    const res = await fetch(target.toString(), { method: "GET" });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    console.error("Error in /api/continuity/policy GET:", error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unknown error" },
      { status: 500 },
    );
  }
}

export async function PUT(request: NextRequest) {
  try {
    const apiBase = getApiBase();
    const body = await request.json();
    const res = await fetch(`${apiBase}/continuity/policy`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    console.error("Error in /api/continuity/policy PUT:", error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unknown error" },
      { status: 500 },
    );
  }
}
