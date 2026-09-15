const FALLBACK = "/";

export function safeRedirect(raw: string | null | undefined): string {
  if (!raw) return FALLBACK;
  if (!raw.startsWith("/")) return FALLBACK;
  if (raw.startsWith("//") || raw.startsWith("/\\")) return FALLBACK;
  if (raw.includes("\\")) return FALLBACK;
  return raw;
}