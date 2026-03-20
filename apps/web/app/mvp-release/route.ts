import { NextResponse } from "next/server";
import { getMvpPresentationHtml } from "@/lib/mvpPresentation";

export const runtime = "nodejs";

export async function GET() {
  const html = await getMvpPresentationHtml();

  return new NextResponse(html, {
    headers: {
      "content-type": "text/html; charset=utf-8",
      "cache-control": "private, no-store, max-age=0",
    },
  });
}
