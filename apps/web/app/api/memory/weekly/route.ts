import { NextRequest, NextResponse } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? process.env.API_BASE_URL;

if (!API_BASE) {
  throw new Error("Missing NEXT_PUBLIC_API_BASE_URL");
}

export async function GET(req: NextRequest) {
  const currentParams = new URL(req.url).searchParams;
  const user = currentParams.get("user") || "a";
  const url = new URL(`${API_BASE}/memory/dev/weekly`);
  const limit = currentParams.get("limit") || "1";
  url.searchParams.set("limit", limit);
  url.searchParams.set("user", user);
  if (currentParams.get("debug") === "true") {
    url.searchParams.set("debug", "true");
  }
  const sysOverride = currentParams.get("system_prompt_override");
  const userOverride = currentParams.get("user_prompt_override");
  if (sysOverride) url.searchParams.set("system_prompt_override", sysOverride);
  if (userOverride) url.searchParams.set("user_prompt_override", userOverride);

  const r = await fetch(url.toString(), { method: "GET" });
  const text = await r.text();
  let data: any;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { error: text || r.statusText || "Internal Server Error" };
  }
  return NextResponse.json(data, { status: r.status });
}
