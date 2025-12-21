import { NextRequest, NextResponse } from "next/server";

export async function GET(req: NextRequest) {
  const url = new URL(req.url);
  const personId = url.searchParams.get("person_id");

  if (!personId) {
    return NextResponse.json({ error: "person_id required" }, { status: 400 });
  }

  const API_BASE =
    process.env.NEXT_PUBLIC_API_BASE_URL ?? process.env.API_BASE_URL;
  if (!API_BASE) {
    throw new Error("Missing NEXT_PUBLIC_API_BASE_URL");
  }

  const upstream = await fetch(
    `${API_BASE}/person/model?person_id=${encodeURIComponent(personId)}`
  );
  const payload = await upstream.json();
  return NextResponse.json(payload, { status: upstream.status });
}
