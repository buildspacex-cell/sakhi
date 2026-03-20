import { NextResponse, type NextRequest } from "next/server";
import {
  MVP_PRESENTATION_ACCESS_COOKIE,
  isValidMvpPresentationAccessToken,
} from "@/lib/mvpPresentationAccess";
import { updateSession } from "@/lib/supabase/middleware";

export async function middleware(request: NextRequest) {
  if (request.nextUrl.pathname.startsWith("/mvp-release")) {
    if (request.nextUrl.pathname.startsWith("/mvp-release/unlock")) {
      return NextResponse.next();
    }

    const accessCookie = request.cookies.get(MVP_PRESENTATION_ACCESS_COOKIE)?.value;
    if (!isValidMvpPresentationAccessToken(accessCookie)) {
      const unlockUrl = request.nextUrl.clone();
      unlockUrl.pathname = "/mvp-release/unlock";
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
