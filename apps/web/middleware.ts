import { NextResponse, type NextRequest } from "next/server";
import {
  MVP_PRESENTATION_ACCESS_COOKIE,
  isValidMvpPresentationAccessToken,
} from "@/lib/mvpPresentationAccess";
import { updateSession } from "@/lib/supabase/middleware";

function getProtectedMvpRoot(pathname: string) {
  if (pathname === "/mvp" || pathname.startsWith("/mvp/")) {
    return "/mvp";
  }

  if (pathname === "/mvp-release" || pathname.startsWith("/mvp-release/")) {
    return "/mvp-release";
  }

  if (pathname === "/pitch" || pathname.startsWith("/pitch/")) {
    return "/pitch";
  }

  return null;
}

// ── Public access lock ────────────────────────────────────────────────────────
// Only /company-deck is publicly accessible. All other app routes return 404.
// To re-enable a route, add its prefix to ALLOWED_PREFIXES below.
// DO NOT delete any route files — this is the only change needed to restore access.
//
// Routes currently locked (restore by adding to ALLOWED_PREFIXES):
//   /experience, /auth, /soul, /journal, /demo, /lab, /mvp, /mvp-release,
//   /pitch, /story, /story-scroll, /dashboard, /chat, /session, /system,
//   /debug, /breath, /alignment, /contract, /calibration, /link, /landing, /
//
const ALLOWED_PREFIXES = [
  "/company-deck",
  "/api",
  "/story",
];

function isAllowed(pathname: string): boolean {
  return ALLOWED_PREFIXES.some((prefix) => pathname === prefix || pathname.startsWith(prefix + "/"));
}
// ─────────────────────────────────────────────────────────────────────────────

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Block all routes not in the allow-list
  if (!isAllowed(pathname)) {
    return new NextResponse(null, { status: 404 });
  }

  const protectedRoot = getProtectedMvpRoot(pathname);

  if (protectedRoot) {
    if (pathname === `${protectedRoot}/unlock`) {
      return NextResponse.next();
    }

    const accessCookie = request.cookies.get(MVP_PRESENTATION_ACCESS_COOKIE)?.value;
    if (!isValidMvpPresentationAccessToken(accessCookie)) {
      const unlockUrl = request.nextUrl.clone();
      unlockUrl.pathname = `${protectedRoot}/unlock`;
      unlockUrl.search = "";
      return NextResponse.redirect(unlockUrl);
    }

    return NextResponse.next();
  }

  return await updateSession(request);
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder
     * - api routes (handled separately)
     */
    "/((?!_next/static|_next/image|favicon.ico|api/|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
