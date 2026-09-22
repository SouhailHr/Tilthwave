import { NextResponse, type NextRequest } from "next/server";

// The API's httpOnly session cookie. httpOnly hides it from JavaScript, not from this server-side
// check, and cookies are not port-scoped, so the one set by localhost:8080 reaches localhost:3000
// (on split subdomains, API_COOKIE_DOMAIN makes it reach both). Presence only: this is a UX gate
// that keeps anonymous visitors from loading the app shell; the API verifies the token itself.
const SESSION_COOKIE = "tw_access";

const PROTECTED_MATCHER = /^\/(?!login|api\/health|_next|brand|favicon\.ico|.*\.(?:svg|png|jpg|jpeg|webp|ico|js|css|map)$)/;

const API_ORIGIN = (() => {
  const raw = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (!raw) return "";
  try {
    return new URL(raw).origin;
  } catch {
    return "";
  }
})();

/**
 * Content-Security-Policy with a per-request nonce.
 *
 * Next.js emits its React Server Components payload as inline <script> tags, so a plain
 * `script-src 'self'` blocks hydration (the login form never mounts). Next reads the nonce
 * from the request's Content-Security-Policy header and stamps it on every script it emits;
 * 'strict-dynamic' then lets those trusted scripts load the chunks they need.
 */
function buildCsp(nonce: string): string {
  const scriptSrc =
    process.env.NODE_ENV === "production"
      ? `'self' 'nonce-${nonce}' 'strict-dynamic'`
      // Fast refresh needs eval; dev keeps the nonce so the code path is the same as prod.
      : `'self' 'nonce-${nonce}' 'strict-dynamic' 'unsafe-eval'`;
  return [
    "default-src 'self'",
    `script-src ${scriptSrc}`,
    // shadcn primitives + tailwind 4 use inline styles via style attributes.
    "style-src 'self' 'unsafe-inline' fonts.googleapis.com",
    "font-src 'self' fonts.gstatic.com data:",
    "img-src 'self' data: blob:",
    `connect-src 'self'${API_ORIGIN ? ` ${API_ORIGIN}` : ""}`,
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "object-src 'none'",
  ].join("; ");
}

function withCsp(request: NextRequest): { response: NextResponse; csp: string } {
  const nonce = btoa(crypto.randomUUID());
  const csp = buildCsp(nonce);
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);
  requestHeaders.set("Content-Security-Policy", csp);
  const response = NextResponse.next({ request: { headers: requestHeaders } });
  response.headers.set("Content-Security-Policy", csp);
  return { response, csp };
}

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const { response, csp } = withCsp(request);

  if (!PROTECTED_MATCHER.test(pathname)) return response;

  if (request.cookies.get(SESSION_COOKIE)?.value) {
    return response;
  }

  const loginUrl = request.nextUrl.clone();
  loginUrl.pathname = "/login";
  loginUrl.search = `?redirect=${encodeURIComponent(pathname + search)}`;
  const redirect = NextResponse.redirect(loginUrl);
  redirect.headers.set("Content-Security-Policy", csp);
  return redirect;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
