import "../styles/globals.css";
import type { ReactNode } from "react";

export const metadata = {
  title: "KWS Control Panel",
  description: "Unified hosting and DNS control panel",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-900 text-slate-100">
        <header className="p-4 border-b border-slate-800 bg-slate-950">
          <div className="max-w-5xl mx-auto flex items-center justify-between">
            <h1 className="text-xl font-semibold">KWS Control Panel</h1>
            <span className="text-sm text-slate-400">cp.karve.fun</span>
          </div>
        </header>
        <main className="max-w-5xl mx-auto p-4">{children}</main>
      </body>
    </html>
  );
}
