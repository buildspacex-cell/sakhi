import { NextRequest, NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

export const dynamic = "force-dynamic";

function parseJsonSafe(raw: string) {
  if (!raw) return {};
  try {
    return JSON.parse(raw);
  } catch {
    return { error: raw };
  }
}

export async function GET(request: NextRequest) {
  const personId = request.nextUrl.searchParams.get("person_id");
  if (!personId) {
    return NextResponse.json(
      { error: "person_id is required" },
      { status: 400 }
    );
  }

  try {
    const response = await fetch(
      `${getApiBase()}/api/v1/agent/tasks/active?person_id=${encodeURIComponent(personId)}`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      }
    );

    const text = await response.text();
    return NextResponse.json(parseJsonSafe(text), { status: response.status });
  } catch (error) {
    console.error("[api/agent/plans] active tasks proxy error:", error);
    return NextResponse.json(
      { error: "Failed to fetch active task plans" },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const personId = typeof body?.person_id === "string" ? body.person_id : "";
    const task = typeof body?.task === "string" ? body.task : "";
    const autoExecute = Boolean(body?.auto_execute);

    if (!personId || !task.trim()) {
      return NextResponse.json(
        { error: "person_id and task are required" },
        { status: 400 }
      );
    }

    const response = await fetch(
      `${getApiBase()}/api/v1/agent/task?person_id=${encodeURIComponent(personId)}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          task: task.trim(),
          auto_execute: autoExecute,
        }),
      }
    );

    const text = await response.text();
    return NextResponse.json(parseJsonSafe(text), { status: response.status });
  } catch (error) {
    console.error("[api/agent/plans] create task plan proxy error:", error);
    return NextResponse.json(
      { error: "Failed to create task plan" },
      { status: 500 }
    );
  }
}
