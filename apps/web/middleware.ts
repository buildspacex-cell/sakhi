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

export async function middleware(request: NextRequest) {
  const protectedRoot = getProtectedMvpRoot(request.nextUrl.pathname);

  if (protectedRoot) {
    if (request.nextUrl.pathname === `${protectedRoot}/unlock`) {
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
