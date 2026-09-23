import { describe, expect, it } from "vitest";

import { safeRedirect } from "./safeRedirect";

describe("safeRedirect", () => {
  it("returns / for null/undefined/empty", () => {
    expect(safeRedirect(null)).toBe("/");
    expect(safeRedirect(undefined)).toBe("/");
    expect(safeRedirect("")).toBe("/");
  });

  it("blocks protocol-relative URLs", () => {
    expect(safeRedirect("//evil.com")).toBe("/");
    expect(safeRedirect("//evil.com/foo")).toBe("/");
  });

  it("blocks backslash injection", () => {
    expect(safeRedirect("/\\evil.com")).toBe("/");
    expect(safeRedirect("/foo\\bar")).toBe("/");
  });

  it("blocks paths the URL parser turns into another origin (tab, newline, encoded forms)", () => {
    expect(safeRedirect("/\t/evil.com")).toBe("/");
    expect(safeRedirect("/\n/evil.com")).toBe("/");
    expect(safeRedirect("/\r\n//evil.com")).toBe("/");
    expect(safeRedirect(decodeURIComponent("/%09/evil.com"))).toBe("/");
    expect(safeRedirect("/%2F/evil.com")).toBe("/%2F/evil.com"); // stays a same-origin path
  });

  it("keeps the query and hash of an internal path", () => {
    expect(safeRedirect("/zones?page=2#top")).toBe("/zones?page=2#top");
  });

  it("blocks anything not starting with /", () => {
    expect(safeRedirect("evil.com")).toBe("/");
    expect(safeRedirect("javascript:alert(1)")).toBe("/");
    expect(safeRedirect("http://evil.com")).toBe("/");
  });

  it("allows valid internal paths", () => {
    expect(safeRedirect("/")).toBe("/");
    expect(safeRedirect("/dashboard")).toBe("/dashboard");
    expect(safeRedirect("/farms/123?x=1")).toBe("/farms/123?x=1");
  });
});