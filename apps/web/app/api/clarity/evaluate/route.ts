import { NextRequest, NextResponse } from 'next/server';

const API_BASE = process.env.API_BASE_URL ?? 'http://localhost:8000';

export async function POST(req: NextRequest) {
  const body = await req.json();

  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  const auth = req.headers.get('authorization');
  if (auth) {
    headers.Authorization = auth;
  }

  const upstream = await fetch(`${API_BASE}/clarity/evaluate`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  });

  const raw = await upstream.text();
  let data: any;
  try {
    data = raw ? JSON.parse(raw) : {};
  } catch {
    data = { error: raw || upstream.statusText || 'Internal Server Error' };
  }

  return NextResponse.json(data ?? {}, { status: upstream.status });
}
