import type { Metadata } from "next";
import "./globals.css";
import Header from "@/components/Header";

export const metadata: Metadata = {
  title: "Syone Enterprise GenAI Formation 2026",
  description: "End-to-End Multimodal GenAI Engine: GraphRAG + BM25 vs. Google Open Knowledge Format (OKF)",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen flex flex-col bg-slate-950 text-slate-100 antialiased selection:bg-blue-600 selection:text-white">
        <Header />
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 py-6">{children}</main>
        <footer className="border-t border-slate-800/80 py-4 text-center text-xs text-slate-500">
          Syone Enterprise AI Formation • Designed for High-Performance Local & Cloud AI Engineering
        </footer>
      </body>
    </html>
  );
}
