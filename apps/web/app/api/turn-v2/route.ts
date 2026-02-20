import { NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

export async function POST(req: Request) {
  console.log("TURN-V2 ROUTE HIT");
  const body = await req.json();
  const url = new URL(req.url);
  const user = url.searchParams.get("user") || "a";
  const debug = url.searchParams.get("debug") || "0";
  const apiBase = getApiBase();
  const r = await fetch(`${apiBase}/v2/turn?user=${encodeURIComponent(user)}&debug=${debug}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const text = await r.text();
  let data: any;
  try {
    data = text ? JSON.parse(text) : {};
  } catch (err) {
    data = { error: text || r.statusText || "Internal Server Error" };
  }
  return NextResponse.json(data, { status: r.status });
}
