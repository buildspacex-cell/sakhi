import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

const API_BASE = process.env.SAKHI_API_URL || "http://localhost:8080";

// Default demo user for development
const DEMO_PERSON_ID = "6b5b2fbc-9efb-4ba4-be0a-9ec527e23f90";

export async function GET(request: NextRequest) {
  const cookieStore = await cookies();

  // Try cookie first, then query param, then fall back to demo user in dev
  const personId =
    cookieStore.get("sakhi_person_id")?.value ||
    request.nextUrl.searchParams.get("user") ||
    (process.env.NODE_ENV === "development" ? DEMO_PERSON_ID : null);

  if (!personId) {
    return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
  }

  try {
    const response = await fetch(`${API_BASE}/v1/state/friction/${personId}`, {
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      const error = await response.text();
      return NextResponse.json(
        { error: "Failed to fetch friction state", details: error },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Friction state error:", error);
    return NextResponse.json(
      { error: "Internal error", details: String(error) },
      { status: 500 }
    );
  }
}
