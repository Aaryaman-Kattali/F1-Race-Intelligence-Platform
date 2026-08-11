import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "F1 Race Intelligence Platform",
  description:
    "A data engineering + agentic AI platform for Formula 1 race analysis — visualized.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
