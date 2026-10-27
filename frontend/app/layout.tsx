import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "xPay — Send more home",
  description: "See the exact amount that arrives in Bangladesh before you send.",
  icons: { icon: "/favicon.ico" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en"><body className="antialiased">{children}</body></html>
  );
}
