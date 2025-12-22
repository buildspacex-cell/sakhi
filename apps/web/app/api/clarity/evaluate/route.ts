import { NextRequest, NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

export async function POST(req: NextRequest) {
  const API_BASE = getApiBase();
  const body = await req.json();

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const auth = req.headers.get("authorization");
  if (auth) {
    headers.Authorization = auth;
  }

  const upstream = await fetch(`${API_BASE}/clarity/evaluate`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });

  const raw = await upstream.text();
  let data: any;
  try {
    data = raw ? JSON.parse(raw) : {};
  } catch {
    data = { error: raw || upstream.statusText || "Internal Server Error" };
  }

  return NextResponse.json(data ?? {}, { status: upstream.status });
}
