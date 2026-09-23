import { renderHook, act } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";

import { useDebounced } from "./useDebounced";

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("useDebounced", () => {
  it("returns initial value immediately", () => {
    const { result } = renderHook(() => useDebounced("hello"));
    expect(result.current).toBe("hello");
  });

  it("debounces updates by the given ms", () => {
    const { result, rerender } = renderHook(
      ({ value }) => useDebounced(value, 200),
      { initialProps: { value: "a" } },
    );
    rerender({ value: "b" });
    expect(result.current).toBe("a");
    act(() => {
      vi.advanceTimersByTime(150);
    });
    expect(result.current).toBe("a");
    act(() => {
      vi.advanceTimersByTime(60);
    });
    expect(result.current).toBe("b");
  });

  it("only commits the latest value when bursts of updates arrive", () => {
    const { result, rerender } = renderHook(
      ({ value }) => useDebounced(value, 200),
      { initialProps: { value: "a" } },
    );
    rerender({ value: "b" });
    rerender({ value: "c" });
    rerender({ value: "d" });
    act(() => {
      vi.advanceTimersByTime(250);
    });
    expect(result.current).toBe("d");
  });
});