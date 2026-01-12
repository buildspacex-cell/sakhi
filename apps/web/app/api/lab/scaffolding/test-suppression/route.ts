import { NextRequest, NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const apiBase = getApiBase();

    const res = await fetch(`${apiBase}/lab/scaffolding/test-suppression`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    const data = await res.json();

    if (!res.ok) {
      return NextResponse.json(
        { error: data?.detail || data?.error || "Suppression test failed" },
        { status: res.status }
      );
    }

    return NextResponse.json(data);
  } catch (error: any) {
    return NextResponse.json(
      { error: error?.message || "Failed to test suppression" },
      { status: 500 }
    );
  }
}
