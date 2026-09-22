// The API's timestamps are naive UTC ("2026-09-15 16:06:56.266864", no zone). Date.parse() reads
// a string like that as LOCAL time, which is silently off by the browser's UTC offset. Everything
// that renders a date goes through here so it is parsed as UTC once and shown in local time.
const NAIVE_TIMESTAMP = /^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?$/;

export function parseApiDate(value: string | null | undefined): Date | null {
  if (!value) return null;
  const iso = NAIVE_TIMESTAMP.test(value) ? `${value.replace(" ", "T")}Z` : value;
  const time = Date.parse(iso);
  return Number.isNaN(time) ? null : new Date(time);
}

const pad = (n: number) => String(n).padStart(2, "0");

/** Local time, to the second: "2026-09-15 18:06:56". "—" for nothing or unparseable. */
export function formatDateTime(value: string | null | undefined): string {
  const d = parseApiDate(value);
  if (!d) return "—";
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ` +
    `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  );
}

/** "just now", "5m ago", "3h ago", "2d ago". The raw value if it cannot be parsed. */
export function formatRelative(value: string | null | undefined, now: number = Date.now()): string {
  if (!value) return "—";
  const d = parseApiDate(value);
  if (!d) return value;
  const diffMin = Math.floor((now - d.getTime()) / 60_000);
  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  return `${Math.floor(diffHr / 24)}d ago`;
}
