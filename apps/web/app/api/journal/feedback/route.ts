import { NextRequest, NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

type FeedbackBody = {
  journal_id?: string;
  emotional_shift?: "lighter" | "calmer" | "same" | "stirred_up";
  shift_explained_text?: string | null;
  return_intent?: "yes" | "maybe" | "no";
};

export async function POST(req: NextRequest) {
  const body = (await req.json()) as FeedbackBody;
  const journal_id = body.journal_id?.trim();
  const emotional_shift = body.emotional_shift;
  const return_intent = body.return_intent;
  const shift_explained_text = (body.shift_explained_text || "").trim() || null;

  if (!journal_id || !emotional_shift || !return_intent) {
    return NextResponse.json({ error: "journal_id, emotional_shift, and return_intent are required" }, { status: 400 });
  }

  const apiBase = getApiBase();
  const apiUrl = new URL(`${apiBase}/experience/journal`);
  const userParam = req.nextUrl.searchParams.get("user");
  if (userParam) {
    apiUrl.searchParams.set("user", userParam);
  }

  const created_at = new Date().toISOString();
  const feedbackPayload = {
    journal_id,
    emotional_shift,
    shift_explained_text,
    return_intent,
    created_at,
  };

  const feedbackEntryId = `journal_feedback:${journal_id}:${Date.now()}`;

  const upstream = await fetch(apiUrl.toString(), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text: JSON.stringify(feedbackPayload),
      layer: "journal_feedback",
      entry_id: feedbackEntryId,
    }),
  });

  const raw = await upstream.text();
  let data: any;
  try {
    data = raw ? JSON.parse(raw) : {};
  } catch {
    data = { error: raw || upstream.statusText || "Internal Server Error" };
  }

  if (!upstream.ok) {
    return NextResponse.json(data ?? { error: "Upstream error" }, { status: upstream.status });
  }

  return NextResponse.json({ ok: true, journal_id, feedback_entry_id: feedbackEntryId, upstream: data });
}
