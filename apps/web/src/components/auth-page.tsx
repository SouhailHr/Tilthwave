import { ReactNode } from "react";
import Image from "next/image";

import { CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

/** The full-bleed backdrop shared by sign-in, forgot-password and reset-password. */
export function AuthPage({ children }: { children: ReactNode }) {
  return (
    <div className="relative flex flex-1 items-center justify-center overflow-hidden p-6">
      {/* Animated brand SVG kept as a plain img so the embedded SMIL/CSS
          animations actually play and so we don't need next.config's
          dangerouslyAllowSVG escape hatch. */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src="/brand/tilthwave-bg-hero-animated.svg"
        alt=""
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 -z-10 size-full object-cover"
      />
      {children}
    </div>
  );
}

/** Brand lockup plus a title, at the top of every auth card. */
export function AuthCardHeader({ title, description }: { title: string; description: string }) {
  return (
    <CardHeader className="items-center text-center">
      <div className="mb-2 flex flex-col items-center gap-2">
        <Image src="/brand/tilthwave-mark.svg" alt="tilthwave" width={40} height={40} priority />
        <div className="flex items-baseline gap-2">
          <span className="font-heading text-xl font-semibold tracking-tight text-foreground">
            tilthwave
          </span>
          <span className="text-xs text-muted-foreground">· farm watch</span>
        </div>
      </div>
      <CardTitle>{title}</CardTitle>
      <CardDescription>{description}</CardDescription>
    </CardHeader>
  );
}
