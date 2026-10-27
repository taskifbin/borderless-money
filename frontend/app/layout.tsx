import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Xpay — Send more home",
  description: "See the exact amount that arrives in Bangladesh before you send.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en"><body className="antialiased">{children}</body></html>
  );
}
