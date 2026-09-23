import type { Metadata, Viewport } from "next";
import { Geist_Mono, Manrope } from "next/font/google";

import "./globals.css";
import { ObservabilitySink } from "@/providers/ObservabilitySink";
import { QueryProvider } from "@/providers/QueryProvider";

// Every page is rendered per request: the Content-Security-Policy nonce set in middleware.ts
// can only be stamped on Next's inline scripts when the HTML is not prerendered at build time.
export const dynamic = "force-dynamic";

// The brand face (brand/README.md): Medium for the slogan and body, Bold for headings, ExtraBold
// for the wordmark. Self-hosted by next/font, so no request to Google Fonts at run time.
const manrope = Manrope({
  variable: "--font-manrope",
  subsets: ["latin"],
  weight: ["500", "700", "800"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

// Absolute base for the share-card URLs link previews fetch (WhatsApp, Slack, LinkedIn, X).
const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://tilthwave.hannibyte.com";
const SHARE_IMAGE = {
  url: "/brand/png/tilthwave-og-1200x630.png",
  width: 1200,
  height: 630,
  alt: "tilthwave: the field's true voice",
};

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: "tilthwave",
  description: "The field's true voice",
  applicationName: "tilthwave",
  manifest: "/manifest.json",
  openGraph: {
    type: "website",
    siteName: "tilthwave",
    title: "tilthwave",
    description: "The field's true voice",
    url: "/",
    images: [SHARE_IMAGE],
  },
  twitter: {
    card: "summary_large_image",
    title: "tilthwave",
    description: "The field's true voice",
    images: [SHARE_IMAGE.url],
  },
  // iOS "Add to Home Screen": the name under the icon and a dark status bar over the loam UI.
  appleWebApp: { capable: true, title: "tilthwave", statusBarStyle: "black-translucent" },
  icons: {
    icon: [
      { url: "/brand/png/tilthwave-mark-reverse-64.png", sizes: "64x64", type: "image/png" },
      { url: "/brand/tilthwave-mark-reverse.svg", type: "image/svg+xml" },
    ],
    apple: [{ url: "/brand/png/tilthwave-mark-reverse-180.png", sizes: "180x180", type: "image/png" }],
  },
};

export const viewport: Viewport = {
  themeColor: "#1E2A1C",
  viewportFit: "cover", // the sign-in card respects the notch through safe-area insets
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${manrope.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body
        className="min-h-full flex flex-col font-sans"
        suppressHydrationWarning
      >
        <QueryProvider>
          <ObservabilitySink>{children}</ObservabilitySink>
        </QueryProvider>
      </body>
    </html>
  );
}
