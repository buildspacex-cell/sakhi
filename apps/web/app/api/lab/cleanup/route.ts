import { NextRequest, NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

export async function POST(req: NextRequest) {
  try {
    const API_BASE = getApiBase();
    const body = await req.json();
    const res = await fetch(`${API_BASE}/lab/cleanup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const text = await res.text();
    let data: any;
    try {
      data = text ? JSON.parse(text) : {};
    } catch {
      data = { error: text || res.statusText || "Internal Server Error" };
    }
    return NextResponse.json(data, { status: res.status });
  } catch (err: any) {
    const message = err?.message || "Failed to call /lab/cleanup";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
