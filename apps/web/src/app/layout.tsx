import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AppShell } from "@/components/app-shell";

import "./globals.css";

export const metadata: Metadata = {
  title: "AI Atlas",
  description: "Discover AI tools and build evidence-led stacks.",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="vi" data-theme="dark">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
