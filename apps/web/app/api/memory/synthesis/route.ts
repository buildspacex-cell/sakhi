import { NextRequest, NextResponse } from "next/server";

const API_BASE = process.env.API_BASE_URL ?? "http://localhost:8000";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json().catch(() => ({}));
    const personId: string | undefined =
      body.person_id?.trim() ||
      process.env.NEXT_PUBLIC_DEMO_PERSON_ID ||
      process.env.DEMO_USER_ID ||
      process.env.PERSON_ID;

    if (!personId) {
      return NextResponse.json({ error: "person_id is required" }, { status: 400 });
    }

    const url = new URL(`${API_BASE}/memory/${personId}/weekly`);
    url.searchParams.set("debug", "true");
    if (typeof body.system_prompt === "string" && body.system_prompt.trim()) {
      url.searchParams.set("system_prompt", body.system_prompt);
    }
    if (typeof body.user_prompt === "string" && body.user_prompt.trim()) {
      url.searchParams.set("user_prompt", body.user_prompt);
    }

    const r = await fetch(url.toString(), { method: "GET" });
    const text = await r.text();
    let data: any;
    try {
      data = text ? JSON.parse(text) : {};
    } catch {
      data = { error: text || r.statusText || "Internal Server Error" };
    }
    // Server-side debug: log exactly what we return.
    try {
      console.log("WEEKLY_SYNTHESIS_SERVER_RESPONSE", JSON.stringify(data, null, 2));
    } catch {
      // ignore logging errors
    }

    return NextResponse.json(data, { status: r.status });
  } catch (e) {
    console.error("WEEKLY_SYNTHESIS_ERROR", e);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
