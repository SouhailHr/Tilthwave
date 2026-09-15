"use client";

import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[global:error]", error);
  }, [error]);

  return (
    <html lang="en">
      <body
        style={{
          fontFamily: "system-ui, sans-serif",
          padding: "2rem",
          display: "grid",
          placeItems: "center",
          minHeight: "100vh",
          margin: 0,
        }}
      >
        <div style={{ maxWidth: 480, textAlign: "center", display: "grid", gap: 16 }}>
          <h1 style={{ fontSize: 24, margin: 0 }}>Something went very wrong</h1>
          <p style={{ color: "#666", margin: 0 }}>
            The application failed to render.
            {error.digest ? (
              <>
                <br />
                <code style={{ fontSize: 12 }}>ref: {error.digest}</code>
              </>
            ) : null}
          </p>
          <button
            type="button"
            onClick={reset}
            style={{
              padding: "8px 16px",
              border: "1px solid #ccc",
              borderRadius: 8,
              background: "white",
              cursor: "pointer",
            }}
          >
            Try again
          </button>
        </div>
      </body>
    </html>
  );
}