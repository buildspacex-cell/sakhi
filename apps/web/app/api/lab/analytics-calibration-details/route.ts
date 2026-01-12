import { NextRequest, NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

export async function GET(req: NextRequest) {
  try {
    const API_BASE = getApiBase();
    const url = new URL(`${API_BASE}/lab/analytics-calibration-details`);
    req.nextUrl.searchParams.forEach((value, key) => {
      url.searchParams.set(key, value);
    });
    const res = await fetch(url.toString(), { method: "GET" });
    const text = await res.text();
    let data: any = {};
    try {
      data = text ? JSON.parse(text) : {};
    } catch {
      data = { error: text || res.statusText || "Internal Server Error" };
    }
    return NextResponse.json(data, { status: res.status });
  } catch (err: any) {
    return NextResponse.json({ error: err?.message || "Failed to fetch analytics/calibration details" }, { status: 500 });
  }
}
