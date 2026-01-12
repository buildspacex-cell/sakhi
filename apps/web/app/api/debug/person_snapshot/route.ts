import { NextRequest, NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

export async function GET(req: NextRequest) {
  const API_BASE = getApiBase();
  const url = new URL(`${API_BASE}/debug/person_snapshot`);
  const personId = req.nextUrl.searchParams.get("person_id");
  const limit = req.nextUrl.searchParams.get("limit");
  if (personId) url.searchParams.set("person_id", personId);
  if (limit) url.searchParams.set("limit", limit);

  const res = await fetch(url.toString(), {
    method: "GET",
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
  });
  const text = await res.text();
  let data: any;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { error: text || res.statusText || "Internal Server Error" };
  }
  return NextResponse.json(data, { status: res.status });
}
