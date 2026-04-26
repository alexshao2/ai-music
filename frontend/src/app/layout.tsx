import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Music — Hội đồng âm nhạc cấp cao",
  description:
    "Studio sáng tác nhạc dẫn dắt bởi hội đồng AI personas, dựa trên kho kiến thức âm nhạc đồ sộ, tích hợp Suno AI.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi">
      <body className="min-h-screen font-sans antialiased">
        <header className="border-b border-white/10 bg-ink/70 backdrop-blur sticky top-0 z-10">
          <div className="mx-auto max-w-6xl px-6 py-4 flex items-center justify-between">
            <div>
              <h1 className="font-display text-xl text-gold tracking-wide">
                AI Music
              </h1>
              <p className="text-xs text-white/60">Hội đồng âm nhạc cấp cao</p>
            </div>
            <nav className="flex gap-5 text-sm text-white/80">
              <a href="/" className="hover:text-accent">Studio</a>
              <a href="/library" className="hover:text-accent">Thư viện</a>
              <a href="/council" className="hover:text-accent">Hội đồng</a>
              <a href="/knowledge" className="hover:text-accent">Kiến thức</a>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
        <footer className="mx-auto max-w-6xl px-6 py-10 text-xs text-white/40">
          <p>
            Một dự án ai-music · Suno AI là dịch vụ độc lập của bên thứ ba —
            xem <a className="underline" href="https://suno.com" target="_blank" rel="noreferrer">suno.com</a>.
          </p>
        </footer>
      </body>
    </html>
  );
}
