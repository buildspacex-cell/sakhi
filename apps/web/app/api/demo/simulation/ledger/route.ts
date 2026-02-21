import { NextRequest, NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

export const dynamic = "force-dynamic";

const DEMO_USER_ID = "6b5b2fbc-9efb-4ba4-be0a-9ec527e23f90";

export async function GET(request: NextRequest) {
  try {
    const apiBase = getApiBase();
    const personId = request.nextUrl.searchParams.get("person_id") || DEMO_USER_ID;
    const limit = request.nextUrl.searchParams.get("limit") || "50";
    const res = await fetch(
      `${apiBase}/demo/simulation/ledger/${personId}?limit=${limit}`,
      { method: "GET" }
    );
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    console.error("Error in /api/demo/simulation/ledger:", error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unknown error" },
      { status: 500 }
    );
  }
}
