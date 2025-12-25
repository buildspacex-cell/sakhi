import { NextRequest, NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

export async function POST(req: NextRequest) {
  const API_BASE = getApiBase();
  const url = `${API_BASE}/memory/dev/weekly/run`;
  const body = await req.json();
  const res = await fetch(url, {
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
}
