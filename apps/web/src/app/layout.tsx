import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { QueryProvider } from "@/providers/QueryProvider";
import { ObservabilitySink } from "@/providers/ObservabilitySink";

// Every page is rendered per request: the Content-Security-Policy nonce set in middleware.ts
// can only be stamped on Next's inline scripts when the HTML is not prerendered at build time.
export const dynamic = "force-dynamic";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "tilthwave · farm watch",
  description: "Where farms speak. Fields listen.",
  icons: {
    icon: "/brand/tilthwave-mark.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
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
