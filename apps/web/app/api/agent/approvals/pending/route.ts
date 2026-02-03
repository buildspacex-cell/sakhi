import { NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

export async function GET(req: Request) {
  const user = new URL(req.url).searchParams.get("user") || "";
  const apiBase = getApiBase();

  try {
    const r = await fetch(
      `${apiBase}/api/v1/agent/task/approvals/pending?user=${encodeURIComponent(user)}`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      }
    );

    const text = await r.text();
    let data: unknown;
    try {
      data = text ? JSON.parse(text) : { pending: [], count: 0 };
    } catch {
      data = { pending: [], count: 0, error: text || r.statusText };
    }

    return NextResponse.json(data, { status: r.status });
  } catch (error) {
    console.error("Error fetching pending approvals:", error);
    return NextResponse.json(
      { pending: [], count: 0, error: "Failed to fetch approvals" },
      { status: 500 }
    );
  }
}
