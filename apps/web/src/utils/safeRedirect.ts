const FALLBACK = "/";
// Any origin works: it only has to be one an attacker cannot also name, and the result is
// compared against it. The real origin is not needed, so this also runs during SSR.
const PROBE = "https://tilthwave.invalid";

/**
 * A same-origin path to go to after sign-in, or "/". The value comes from ?redirect=, so it is
 * attacker-controlled. Checking prefixes by hand missed `/\t/evil.com` (the URL parser strips
 * tabs and newlines, leaving `//evil.com`); resolving it the way the browser will and requiring
 * the same origin covers every such trick. Control characters and backslashes are refused
 * outright, since no legitimate in-app path contains them.
 */
export function safeRedirect(raw: string | null | undefined): string {
  if (!raw || !raw.startsWith("/")) return FALLBACK;
  if (/[\u0000-\u001f\u007f\\]/.test(raw)) return FALLBACK;
  let url: URL;
  try {
    url = new URL(raw, PROBE);
  } catch {
    return FALLBACK;
  }
  if (url.origin !== PROBE) return FALLBACK;
  return `${url.pathname}${url.search}${url.hash}`;
}
