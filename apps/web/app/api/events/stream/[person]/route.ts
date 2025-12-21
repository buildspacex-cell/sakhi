const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? process.env.API_BASE_URL;
if (!API_BASE) {
  throw new Error("Missing NEXT_PUBLIC_API_BASE_URL");
}
const API_KEY =
  process.env.NEXT_PUBLIC_API_KEY || process.env.EXPO_PUBLIC_API_KEY || "";

export async function GET(
  _request: Request,
  { params }: { params: { person: string } },
) {
  const res = await fetch(`${API_BASE}/events/stream/${params.person}`, {
    headers: { "X-API-Key": API_KEY },
    cache: "no-store",
  });

  return new Response(res.body, {
    status: res.status,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
    },
  });
}
