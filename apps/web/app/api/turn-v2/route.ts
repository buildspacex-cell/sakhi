import { NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

export async function POST(req: Request) {
  console.log("TURN-V2 ROUTE HIT");
  const body = await req.json();
  const user = new URL(req.url).searchParams.get("user") || "a";
  const apiBase = getApiBase();
  const r = await fetch(`${apiBase}/v2/turn?user=${encodeURIComponent(user)}`, {
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
