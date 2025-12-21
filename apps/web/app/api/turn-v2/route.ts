import { NextRequest, NextResponse } from 'next/server';

const API_BASE = process.env.API_BASE_URL ?? 'http://localhost:8000';

export async function POST(req: NextRequest) {
  const body = await req.json();
  const user = new URL(req.url).searchParams.get("user") || "a";
  const r = await fetch(`${API_BASE}/v2/turn?user=${encodeURIComponent(user)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const text = await r.text();
  let data: any;
  try {
    data = text ? JSON.parse(text) : {};
  } catch (err) {
    data = { error: text || r.statusText || 'Internal Server Error' };
  }
  return NextResponse.json(data, { status: r.status });
}
