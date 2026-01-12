import { NextRequest, NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const person_id = searchParams.get("person_id");
    const anchor_days = searchParams.get("anchor_days") || "1500";

    if (!person_id) {
      return NextResponse.json(
        { error: "person_id is required" },
        { status: 400 }
      );
    }

    const apiBase = getApiBase();
    const url = new URL("/lab/personal-intelligence", apiBase);
    url.searchParams.set("person_id", person_id);
    url.searchParams.set("anchor_days", anchor_days);

    const res = await fetch(url.toString(), {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    const data = await res.json();

    if (!res.ok) {
      return NextResponse.json(
        { error: data?.detail || data?.error || "Failed to fetch personal intelligence snapshot" },
        { status: res.status }
      );
    }

    return NextResponse.json(data);
  } catch (error: any) {
    return NextResponse.json(
      { error: error?.message || "Failed to fetch personal intelligence snapshot" },
      { status: 500 }
    );
  }
}
