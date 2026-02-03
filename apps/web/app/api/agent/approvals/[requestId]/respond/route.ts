import { NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

export async function POST(
  req: Request,
  { params }: { params: Promise<{ requestId: string }> }
) {
  const { requestId } = await params;
  const user = new URL(req.url).searchParams.get("user") || "";
  const body = await req.json();
  const apiBase = getApiBase();

  try {
    const r = await fetch(
      `${apiBase}/api/v1/agent/task/approvals/${requestId}/respond?user=${encodeURIComponent(user)}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }
    );

    const text = await r.text();
    let data: unknown;
    try {
      data = text ? JSON.parse(text) : {};
    } catch {
      data = { error: text || r.statusText };
    }

    return NextResponse.json(data, { status: r.status });
  } catch (error) {
    console.error("Error responding to approval:", error);
    return NextResponse.json(
      { success: false, error: "Failed to respond to approval" },
      { status: 500 }
    );
  }
}
