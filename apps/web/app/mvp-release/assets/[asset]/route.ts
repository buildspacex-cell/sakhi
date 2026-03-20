import { NextResponse } from "next/server";
import { getMvpPresentationAsset } from "@/lib/mvpPresentation";

export const runtime = "nodejs";

export async function GET(
  _request: Request,
  { params }: { params: { asset: string } }
) {
  const asset = await getMvpPresentationAsset(params.asset);

  if (!asset) {
    return new NextResponse("Not found", { status: 404 });
  }

  return new NextResponse(asset.buffer, {
    headers: {
      "content-type": asset.contentType,
      "cache-control": "private, no-store, max-age=0",
    },
  });
}
