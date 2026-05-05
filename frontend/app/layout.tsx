import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Research Signal Dashboard",
  description: "Private Reddit-driven stock research signal dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

