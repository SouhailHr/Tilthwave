import { ReactNode } from "react";

import { BrandMarkOnDark } from "@/components/brand-mark";
import { FieldBackground } from "@/components/field-background";

/**
 * The sign-in, forgot-password and reset-password screen (brand handoff,
 * login/reference-login.html): the animated field on a canvas, a grain and a vignette over it,
 * and a frosted card. The whole screen is in the dark palette (`dark`), so the shared form
 * components read sage on loam without per-field overrides. Safe-area insets keep the card
 * clear of a notch; the card's entrance animation is off under prefers-reduced-motion.
 */
export function AuthPage({ children }: { children: ReactNode }) {
  return (
    <div className="dark auth-screen">
      <FieldBackground />
      <div className="auth-grain" aria-hidden="true" />
      <div className="auth-vignette" aria-hidden="true" />
      {children}
    </div>
  );
}

/** The frosted card every auth screen sits in. */
export function AuthCard({ children }: { children: ReactNode }) {
  return <main className="auth-card">{children}</main>;
}

/** Brand row (mark, wordmark, slogan), then the screen's title and lead line. */
export function AuthCardHeader({ title, description }: { title: string; description: string }) {
  return (
    <header>
      <div className="auth-brand">
        <BrandMarkOnDark className="size-11 flex-none" />
        <div>
          <div className="auth-brand-name">tilthwave</div>
          <div className="auth-brand-slogan">The field&rsquo;s true voice</div>
        </div>
      </div>
      <h1 className="auth-title">{title}</h1>
      <p className="auth-lead">{description}</p>
    </header>
  );
}
