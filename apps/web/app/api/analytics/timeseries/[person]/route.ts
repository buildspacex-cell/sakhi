import { NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

const API_KEY =
  process.env.NEXT_PUBLIC_API_KEY || process.env.EXPO_PUBLIC_API_KEY || "";

export async function GET(
  _request: Request,
  { params }: { params: { person: string } },
) {
  const API_BASE = getApiBase();
  const res = await fetch(`${API_BASE}/analytics/timeseries/${params.person}`, {
    headers: { "X-API-Key": API_KEY },
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
