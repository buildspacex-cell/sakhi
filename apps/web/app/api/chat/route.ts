import { NextResponse } from "next/server";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? process.env.API_BASE_URL;
const API_KEY =
  process.env.NEXT_PUBLIC_API_KEY || process.env.EXPO_PUBLIC_API_KEY || "";

if (!API_BASE) {
  throw new Error("Missing NEXT_PUBLIC_API_BASE_URL");
}

export async function POST(request: Request) {
  const body = await request.json();
  const payload = body?.messages
    ? body
    : {
        messages: [
          { role: "user", content: body?.text ?? "", metadata: {} },
        ],
        conversation_id: body?.conversation_id,
      };

  const response = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
    },
    body: JSON.stringify(payload),
  });

  const data = await response.json();
  return NextResponse.json(data, { status: response.status });
}
