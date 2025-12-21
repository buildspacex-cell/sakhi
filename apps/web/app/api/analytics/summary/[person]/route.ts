import { NextResponse } from "next/server";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? process.env.API_BASE_URL;

if (!API_BASE) {
  throw new Error("Missing NEXT_PUBLIC_API_BASE_URL");
}
const API_KEY =
  process.env.NEXT_PUBLIC_API_KEY || process.env.EXPO_PUBLIC_API_KEY || "";

export async function GET(
  _request: Request,
  { params }: { params: { person: string } },
) {
  const res = await fetch(`${API_BASE}/analytics/summary/${params.person}`, {
    headers: { "X-API-Key": API_KEY },
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
