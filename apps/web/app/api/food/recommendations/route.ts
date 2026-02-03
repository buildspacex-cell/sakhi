import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8080";

export async function GET(request: NextRequest) {
  const cookieStore = await cookies();
  const personId = cookieStore.get("person_id")?.value;

  if (!personId) {
    return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
  }

  // Get meal query param if provided
  const { searchParams } = new URL(request.url);
  const meal = searchParams.get("meal");

  try {
    const url = new URL(`${BACKEND_URL}/recommendations/foods/dosha-aware/${personId}`);
    if (meal) {
      url.searchParams.set("meal", meal);
    }

    const res = await fetch(url.toString(), {
      headers: { "Content-Type": "application/json" },
    });

    if (!res.ok) {
      return NextResponse.json(
        { error: "Failed to fetch food recommendations" },
        { status: res.status }
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Food recommendations error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
