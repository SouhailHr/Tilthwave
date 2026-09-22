import { describe, expect, it } from "vitest";
import { formatDateTime, formatRelative, parseApiDate } from "./dates";

describe("parseApiDate", () => {
  it("reads the API's naive timestamps as UTC, not local time", () => {
    // Regression: Date.parse("2026-09-15 16:06:56") is local time, off by the UTC offset.
    const d = parseApiDate("2026-09-15 16:06:56.266864");
    expect(d?.getTime()).toBe(Date.UTC(2026, 8, 15, 16, 6, 56, 266));
  });

  it("accepts the T separator and no fraction", () => {
    expect(parseApiDate("2026-09-15T16:06:56")?.getTime()).toBe(Date.UTC(2026, 8, 15, 16, 6, 56));
  });

  it("leaves an explicit zone alone", () => {
    expect(parseApiDate("2026-09-15T16:06:56+02:00")?.getTime()).toBe(Date.UTC(2026, 8, 15, 14, 6, 56));
  });

  it("returns null for nothing or garbage", () => {
    expect(parseApiDate(undefined)).toBeNull();
    expect(parseApiDate("")).toBeNull();
    expect(parseApiDate("not a date")).toBeNull();
  });
});

describe("formatDateTime", () => {
  it("renders local time to the second", () => {
    const value = "2026-09-15 16:06:56.266864";
    const d = parseApiDate(value)!;
    const pad = (n: number) => String(n).padStart(2, "0");
    const expected =
      `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ` +
      `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
    expect(formatDateTime(value)).toBe(expected);
    expect(formatDateTime(value)).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/);
  });

  it("shows a dash for nothing", () => {
    expect(formatDateTime(undefined)).toBe("—");
    expect(formatDateTime("garbage")).toBe("—");
  });
});

describe("formatRelative", () => {
  const now = Date.UTC(2026, 8, 15, 18, 0, 0);
  it("buckets by minutes, hours, days, in UTC terms", () => {
    expect(formatRelative("2026-09-15 17:59:40", now)).toBe("just now");
    expect(formatRelative("2026-09-15 17:55:00", now)).toBe("5m ago");
    expect(formatRelative("2026-09-15 15:00:00", now)).toBe("3h ago");
    expect(formatRelative("2026-09-13 18:00:00", now)).toBe("2d ago");
  });
  it("falls back to the raw value when unparseable, and a dash for nothing", () => {
    expect(formatRelative("later", now)).toBe("later");
    expect(formatRelative(undefined, now)).toBe("—");
  });
});
