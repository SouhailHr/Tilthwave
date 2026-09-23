import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { mountFieldBackground } from "./field-background";

// jsdom has no canvas: a context that accepts every call is enough to drive the animation loop.
function fakeContext() {
  const gradient = { addColorStop: vi.fn() };
  return new Proxy({} as Record<string, unknown>, {
    get: (target, key) => {
      if (!(key in target)) {
        const isGradient = key === "createLinearGradient" || key === "createRadialGradient";
        target[key as string] = isGradient ? () => gradient : vi.fn(); // one spy per method
      }
      return target[key as string];
    },
    set: (target, key, value) => {
      target[key as string] = value;
      return true;
    },
  });
}

function canvas() {
  const c = document.createElement("canvas");
  const ctx = fakeContext();
  vi.spyOn(c, "getContext").mockReturnValue(ctx as unknown as CanvasRenderingContext2D);
  return { c, ctx };
}

function reducedMotion(matches: boolean) {
  vi.stubGlobal("matchMedia", vi.fn().mockReturnValue({ matches }));
}

let frames: FrameRequestCallback[];
let nextId: number;
beforeEach(() => {
  frames = [];
  nextId = 0;
  vi.stubGlobal(
    "requestAnimationFrame",
    vi.fn((cb: FrameRequestCallback) => {
      frames.push(cb);
      return ++nextId;
    }),
  );
  vi.stubGlobal("cancelAnimationFrame", vi.fn());
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("mountFieldBackground", () => {
  it("keeps requesting frames while mounted and stops on cleanup, listeners included", () => {
    reducedMotion(false);
    const remove = vi.spyOn(window, "removeEventListener");
    const { c } = canvas();
    const stop = mountFieldBackground(c);
    frames.shift()!(performance.now() + 16);
    frames.shift()!(performance.now() + 32);
    expect(requestAnimationFrame).toHaveBeenCalledTimes(3); // the first, then one per drawn frame
    stop();
    expect(cancelAnimationFrame).toHaveBeenCalledWith(3);
    const removed = remove.mock.calls.map(([type]) => type);
    expect(removed).toEqual(expect.arrayContaining(["resize", "pointermove", "deviceorientation"]));
  });

  it("draws one still frame under reduced motion instead of animating or staying blank", () => {
    reducedMotion(true);
    const { c, ctx } = canvas();
    mountFieldBackground(c);
    expect(frames).toHaveLength(1);
    frames.shift()!(performance.now());
    expect(frames).toHaveLength(0); // no further frames
    expect(ctx.fillRect).toHaveBeenCalled(); // the sky was painted
  });

  it("is a no-op without a 2D context", () => {
    reducedMotion(false);
    const c = document.createElement("canvas");
    vi.spyOn(c, "getContext").mockReturnValue(null);
    expect(() => mountFieldBackground(c)()).not.toThrow();
    expect(requestAnimationFrame).not.toHaveBeenCalled();
  });
});
