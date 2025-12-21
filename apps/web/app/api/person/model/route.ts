import { NextRequest, NextResponse } from "next/server";

export async function GET(req: NextRequest) {
  const url = new URL(req.url);
  const personId = url.searchParams.get("person_id");

  if (!personId) {
    return NextResponse.json({ error: "person_id required" }, { status: 400 });
  }

  const apiBase = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";
  const upstream = await fetch(
    `${apiBase}/person/model?person_id=${encodeURIComponent(personId)}`
  );
  const payload = await upstream.json();
  return NextResponse.json(payload, { status: upstream.status });
}
