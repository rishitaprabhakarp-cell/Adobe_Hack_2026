import type { Metadata } from "next";
import { Inter, Instrument_Serif, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";
import AppNav from "@/components/AppNav";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const instrumentSerif = Instrument_Serif({
  weight: "400",
  style: ["normal", "italic"],
  subsets: ["latin"],
  variable: "--font-instrument",
  display: "swap",
});

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains",
  display: "swap",
});

export const metadata: Metadata = {
  title: "GEOReady — AI Discoverability Audit",
  description:
    "See how AI sees your brand. Audit your website across 90 GEO checks and get a prioritised fix roadmap — free, instant.",
  openGraph: {
    title: "GEOReady — AI Discoverability Audit",
    description: "Is your brand invisible to AI? Find out in 90 seconds.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${instrumentSerif.variable} ${jetbrains.variable}`}
      data-scroll-behavior="smooth"
    >
      <body className={`${inter.className} min-h-screen antialiased`}>
        <AuthProvider>
          <AppNav />
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
