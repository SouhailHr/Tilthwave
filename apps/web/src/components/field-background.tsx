"use client";

import { useEffect, useRef } from "react";

import { mountFieldBackground } from "@/lib/field-background";

/** The animated field behind the sign-in screens: mounted on mount, stopped on unmount. */
export function FieldBackground() {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    return mountFieldBackground(ref.current);
  }, []);
  return <canvas ref={ref} aria-hidden="true" className="fixed inset-0 block size-full" />;
}
