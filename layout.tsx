import type { Metadata } from "next";
import { AppShell } from "@/components/app-shell";
import { RuntimeConfig } from "@/components/runtime-config";
import "./globals.css";

export const metadata: Metadata = {
  title: "Afran Allocation Dashboard",
  description: "سامانه پایش صندوق‌ها و تحلیل تخصیص دارایی افران",
  other: {
    "codex-preview": "development",
  },
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="fa" dir="rtl">
      <body>
        <RuntimeConfig />
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
