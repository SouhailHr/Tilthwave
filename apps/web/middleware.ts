import { NextResponse, type NextRequest } from "next/server";

const SESSION_COOKIE = "tw_logged_in";

const PROTECTED_MATCHER = /^\/(?!login|api\/health|_next|brand|favicon\.ico|.*\.(?:svg|png|jpg|jpeg|webp|ico|js|css|map)$)/;

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;

  if (!PROTECTED_MATCHER.test(pathname)) return NextResponse.next();

  if (request.cookies.get(SESSION_COOKIE)?.value === "1") {
    return NextResponse.next();
  }

  const loginUrl = request.nextUrl.clone();
  loginUrl.pathname = "/login";
  loginUrl.search = `?redirect=${encodeURIComponent(pathname + search)}`;
  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};