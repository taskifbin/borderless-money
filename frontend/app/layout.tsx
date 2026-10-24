import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Borderless Money",
  description:
    "Send money to Bangladesh. See the exact amount that arrives before you send.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-white text-ink antialiased">{children}</body>
    </html>
  );
}
