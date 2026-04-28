import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Music — Hội đồng âm nhạc cấp cao",
  description:
    "Studio sáng tác nhạc dẫn dắt bởi hội đồng AI personas, dựa trên kho kiến thức âm nhạc đồ sộ, tích hợp Suno AI.",
};

const NAV_ITEMS = [
  { href: "/", label: "Studio" },
  { href: "/library", label: "Thư viện" },
  { href: "/council", label: "Hội đồng" },
  { href: "/knowledge", label: "Kiến thức" },
];

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi">
      <body className="min-h-screen font-sans antialiased">
        <header className="sticky top-0 z-20 border-b border-white/5 bg-ink/60 backdrop-blur-md">
          {/* Hairline gradient ribbon — signals the studio identity. */}
          <div className="h-px w-full bg-atelier opacity-70" />
          <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
            <div className="flex items-center gap-3">
              <span
                aria-hidden
                className="inline-block h-2 w-2 rounded-full bg-atelier shadow-bloom-soft animate-pulse-glow"
              />
              <div>
                <h1 className="font-mono text-[15px] font-semibold uppercase tracking-[0.18em] text-white">
                  AI<span className="text-atelier">{"//"}</span>MUSIC
                </h1>
                <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-white/45">
                  hội đồng âm nhạc cấp cao · v0.5
                </p>
              </div>
            </div>
            <nav className="flex gap-1 text-sm text-white/75">
              {NAV_ITEMS.map((item) => (
                <a
                  key={item.href}
                  href={item.href}
                  className="rounded-md px-3 py-1.5 transition-colors hover:bg-white/[0.06] hover:text-white"
                >
                  {item.label}
                </a>
              ))}
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-6 py-10">{children}</main>
        <footer className="mx-auto max-w-6xl px-6 py-12 font-mono text-[11px] uppercase tracking-[0.18em] text-white/35">
          <p>
            ai-music · suno ai là dịch vụ độc lập của bên thứ ba —
            <a className="ml-1 underline decoration-dotted hover:text-white/60" href="https://suno.com" target="_blank" rel="noreferrer">
              suno.com
            </a>
          </p>
        </footer>
      </body>
    </html>
  );
}
