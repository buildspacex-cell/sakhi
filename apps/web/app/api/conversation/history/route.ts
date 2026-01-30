import { NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

export async function GET(req: Request) {
  const url = new URL(req.url);
  const user = url.searchParams.get("user") || "a";
  const limit = url.searchParams.get("limit") || "20";
  const session_slug = url.searchParams.get("session_slug") || "converse";

  const apiBase = getApiBase();
  const apiUrl = `${apiBase}/v2/conversation/history?user=${encodeURIComponent(user)}&limit=${limit}&session_slug=${encodeURIComponent(session_slug)}`;

  try {
    const r = await fetch(apiUrl, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    const text = await r.text();
    let data: any;
    try {
      data = text ? JSON.parse(text) : {};
    } catch (err) {
      data = { error: text || r.statusText || "Internal Server Error", messages: [] };
    }

    return NextResponse.json(data, { status: r.status });
  } catch (err) {
    console.error("[conversation/history] Error:", err);
    return NextResponse.json(
      { error: "Failed to load conversation history", messages: [] },
      { status: 500 }
    );
  }
}
