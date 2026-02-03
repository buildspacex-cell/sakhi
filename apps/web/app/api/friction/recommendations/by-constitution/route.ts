import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

/**
 * POST /api/friction/recommendations/by-constitution
 *
 * Proxy to Python backend for REAL LLM-powered recommendations.
 * Takes prakruti (constitution) and symptom, returns personalized advice.
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // Validate required fields
    const { vata, pitta, kapha, symptom } = body;
    if (vata === undefined || pitta === undefined || kapha === undefined || !symptom) {
      return NextResponse.json(
        { error: "Missing required fields: vata, pitta, kapha, symptom" },
        { status: 400 }
      );
    }

    // Call Python backend
    const apiUrl = process.env.SAKHI_API_URL || "http://localhost:8080";
    const response = await fetch(`${apiUrl}/recommendations/by-constitution`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        vata: parseFloat(vata),
        pitta: parseFloat(pitta),
        kapha: parseFloat(kapha),
        symptom: String(symptom),
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error("Python API error:", errorText);
      return NextResponse.json(
        { error: "Failed to get recommendations from backend", details: errorText },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Recommendation proxy error:", error);
    return NextResponse.json(
      { error: "Failed to proxy request", details: String(error) },
      { status: 500 }
    );
  }
}
