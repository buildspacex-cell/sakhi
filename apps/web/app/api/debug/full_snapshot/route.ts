import { NextRequest, NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

async function fetchJson(url: string, options?: RequestInit) {
  const res = await fetch(url, { cache: "no-store", ...options });
  const text = await res.text();
  let data: any = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { error: text || res.statusText || "Failed to parse response" };
  }
  return { ok: res.ok, status: res.status, data };
}

export async function GET(req: NextRequest) {
  const API_BASE = getApiBase();
  const personId = req.nextUrl.searchParams.get("person_id") || "a";
  const prime = req.nextUrl.searchParams.get("prime") === "true";
  const limit = req.nextUrl.searchParams.get("limit");

  try {
    if (prime) {
      // Trigger weekly debug pipeline to populate latest signals.
      await fetch(`${API_BASE}/memory/${personId}/weekly?debug=true&limit=1`, { cache: "no-store" }).catch(() => {});
    }

    const [snap, planner, rhythmState, rhythmCurve, soul, weekly, monthly] = await Promise.all([
      fetchJson(`${API_BASE}/debug/person_snapshot?person_id=${encodeURIComponent(personId)}${limit ? `&limit=${limit}` : ""}`),
      fetchJson(`${API_BASE}/planner/${personId}/summary`),
      fetchJson(`${API_BASE}/rhythm/${personId}/state`),
      fetchJson(`${API_BASE}/rhythm/${personId}/curve`),
      fetchJson(`${API_BASE}/soul/${personId}/summary`),
      fetchJson(`${API_BASE}/memory/${personId}/weekly`),
      fetchJson(`${API_BASE}/memory/${personId}/monthly`),
    ]);

    // Snapshot is required; others are optional.
    if (!snap.ok) {
      return NextResponse.json({ error: snap.data?.error || `snapshot:${snap.status}` }, { status: snap.status || 502 });
    }

    const warnings = [
      !planner.ok && `planner:${planner.status}`,
      !rhythmState.ok && `rhythm_state:${rhythmState.status}`,
      !rhythmCurve.ok && `rhythm_curve:${rhythmCurve.status}`,
      !soul.ok && `soul:${soul.status}`,
      !weekly.ok && `weekly:${weekly.status}`,
      !monthly.ok && `monthly:${monthly.status}`,
    ].filter(Boolean);

    const payload = {
      ...(snap.data || {}),
      planner_summary: planner.ok ? planner.data : null,
      rhythm_state: rhythmState.ok ? rhythmState.data : null,
      rhythm_curve: rhythmCurve.ok ? rhythmCurve.data : null,
      soul_summary: soul.ok ? soul.data : null,
      memory_weekly: weekly.ok ? weekly.data : null,
      memory_monthly: monthly.ok ? monthly.data : null,
      warnings,
    };

    return NextResponse.json(payload, { status: 200 });
  } catch (err: any) {
    return NextResponse.json({ error: err?.message || "Snapshot fetch failed" }, { status: 500 });
  }
}
