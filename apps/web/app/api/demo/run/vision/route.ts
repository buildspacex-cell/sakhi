import { NextRequest, NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

const API_KEY =
  process.env.NEXT_PUBLIC_API_KEY || process.env.EXPO_PUBLIC_API_KEY || "";

function parseJsonSafely(raw: string) {
  if (!raw) return {};
  try {
    return JSON.parse(raw);
  } catch {
    return { error: raw };
  }
}

export async function POST(request: NextRequest) {
  try {
    const apiBase = getApiBase();
    const target = new URL(`${apiBase}/demo/run/vision`);
    const params = request.nextUrl.searchParams;

    const task = params.get("task");
    const mode = params.get("mode");
    const personId = params.get("person_id");

    if (task) target.searchParams.set("task", task);
    if (mode) target.searchParams.set("mode", mode);
    if (personId) target.searchParams.set("person_id", personId);

    const response = await fetch(target.toString(), {
      method: "POST",
      headers: {
        ...(API_KEY ? { "X-API-Key": API_KEY } : {}),
      },
    });

    const text = await response.text();
    return NextResponse.json(parseJsonSafely(text), { status: response.status });
  } catch (error) {
    console.error("[api/demo/run/vision] proxy error:", error);
    return NextResponse.json(
      { error: "Failed to run vision demo" },
      { status: 500 }
    );
  }
}
