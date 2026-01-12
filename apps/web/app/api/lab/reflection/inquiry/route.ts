import { NextRequest, NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

export async function POST(req: NextRequest) {
  try {
    const API_BASE = getApiBase();
    const payload = await req.json();
    const res = await fetch(`${API_BASE}/lab/reflection/inquiry`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const text = await res.text();
    let data: any = {};
    try {
      data = text ? JSON.parse(text) : {};
    } catch {
      data = { error: text || res.statusText || "Internal Server Error" };
    }
    return NextResponse.json(data, { status: res.status });
  } catch (err: any) {
    return NextResponse.json({ error: err?.message || "Failed to run reflection inquiry" }, { status: 500 });
  }
}
