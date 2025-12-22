import { NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

const API_KEY =
  process.env.NEXT_PUBLIC_API_KEY || process.env.EXPO_PUBLIC_API_KEY || "";

export async function POST(request: Request) {
  const API_BASE = getApiBase();
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
