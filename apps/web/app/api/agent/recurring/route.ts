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
    const includeInactive =
      request.nextUrl.searchParams.get("include_inactive") === "true";
    const query = new URLSearchParams({
      person_id: personId,
      include_inactive: includeInactive ? "true" : "false",
    });
    const response = await fetch(
      `${getApiBase()}/api/v1/agent/recurring?${query.toString()}`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      }
    );
    const text = await response.text();
    return NextResponse.json(parseJsonSafe(text), { status: response.status });
  } catch (error) {
    console.error("[api/agent/recurring] list proxy error:", error);
    return NextResponse.json(
      { error: "Failed to list recurring schedules" },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const personId = typeof body?.person_id === "string" ? body.person_id : "";
    const task = typeof body?.task === "string" ? body.task : "";
    if (!personId || !task.trim()) {
      return NextResponse.json(
        { error: "person_id and task are required" },
        { status: 400 }
      );
    }

    const response = await fetch(
      `${getApiBase()}/api/v1/agent/recurring?person_id=${encodeURIComponent(personId)}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          task: task.trim(),
          goal_hint: body?.goal_hint,
          cadence: body?.cadence ?? "monthly",
          cadence_interval: body?.cadence_interval ?? 1,
          run_timezone: body?.run_timezone ?? "UTC",
          day_of_month: body?.day_of_month ?? 1,
          run_hour: body?.run_hour ?? 9,
          run_minute: body?.run_minute ?? 0,
          metadata: body?.metadata ?? {},
        }),
      }
    );

    const text = await response.text();
    return NextResponse.json(parseJsonSafe(text), { status: response.status });
  } catch (error) {
    console.error("[api/agent/recurring] create proxy error:", error);
    return NextResponse.json(
      { error: "Failed to create recurring schedule" },
      { status: 500 }
    );
  }
}
