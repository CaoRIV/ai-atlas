import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AppShell } from "@/components/app-shell";
import { themeBootstrapScript } from "@/lib/theme";

import "./globals.css";

export const metadata: Metadata = {
  title: "AI Atlas",
  description: "Discover AI tools and build evidence-led stacks.",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html data-theme="dark" lang="vi" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeBootstrapScript }} />
      </head>
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
