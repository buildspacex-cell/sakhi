import { NextRequest, NextResponse } from "next/server";

type Depth = "light" | "medium" | "deep";
type Verbosity = "brief" | "standard" | "detailed";

const DEFAULT_DEPTH: Depth = "medium";
const DEFAULT_VERBOSITY: Verbosity = "standard";

const validDepth = new Set<Depth>(["light", "medium", "deep"]);
const validVerbosity = new Set<Verbosity>(["brief", "standard", "detailed"]);

export async function GET(req: NextRequest) {
  const cookies = req.cookies;
  const depth = (cookies.get("reflection_depth")?.value as Depth) ?? DEFAULT_DEPTH;
  const verbosity = (cookies.get("response_verbosity")?.value as Verbosity) ?? DEFAULT_VERBOSITY;

  return NextResponse.json(
    {
      reflection_depth: validDepth.has(depth) ? depth : DEFAULT_DEPTH,
      response_verbosity: validVerbosity.has(verbosity) ? verbosity : DEFAULT_VERBOSITY,
    },
    { status: 200 }
  );
}

export async function PATCH(req: NextRequest) {
  const body = await req.json().catch(() => ({}));
  const depth = validDepth.has(body?.reflection_depth) ? (body.reflection_depth as Depth) : DEFAULT_DEPTH;
  const verbosity = validVerbosity.has(body?.response_verbosity)
    ? (body.response_verbosity as Verbosity)
    : DEFAULT_VERBOSITY;

  const res = NextResponse.json(
    {
      reflection_depth: depth,
      response_verbosity: verbosity,
    },
    { status: 200 }
  );

  const maxAge = 60 * 60 * 24 * 30; // 30 days
  res.cookies.set("reflection_depth", depth, { maxAge, httpOnly: false });
  res.cookies.set("response_verbosity", verbosity, { maxAge, httpOnly: false });
  return res;
}
