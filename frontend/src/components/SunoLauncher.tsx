"use client";

import { useState } from "react";
import { api, type SongDraft } from "@/lib/api";

type Props = { draft: SongDraft };

type AutofillState = {
  status: "idle" | "running" | "done" | "error";
  message?: string;
  url?: string | null;
};

export function SunoLauncher({ draft }: Props) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [auto, setAuto] = useState<AutofillState>({ status: "idle" });

  async function launchManual() {
    setBusy(true);
    setError(null);
    try {
      const data = await api.sunoLaunch(draft.id);
      const text = `Title: ${data.title}\n\nStyle:\n${data.style}\n\nLyrics:\n${data.lyrics}`;
      try {
        await navigator.clipboard.writeText(text);
        setCopied(true);
      } catch {
        // clipboard may be unavailable; ignore.
      }
      window.open(data.open_url, "_blank", "noopener,noreferrer");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Lỗi không xác định");
    } finally {
      setBusy(false);
    }
  }

  async function generateAuto() {
    setAuto({ status: "running", message: "Hội đồng đang điều khiển Suno…" });
    try {
      const data = await api.sunoAutofill(draft.id, { wait: true, timeoutSec: 240 });
      setAuto({
        status: "done",
        message: data.note ?? "Đã submit bài hát lên Suno.",
        url: data.suno_url ? `https://suno.com${data.suno_url}` : null,
      });
    } catch (e) {
      setAuto({
        status: "error",
        message: e instanceof Error ? e.message : "Autofill thất bại",
      });
    }
  }

  return (
    <div className="rounded-xl border border-gold/40 bg-gold/5 p-4 space-y-3">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h3 className="font-display text-gold text-lg">Tạo bài hát với Suno</h3>
          <p className="text-sm text-white/70">
            Hội đồng đã chuẩn bị xong prompt. Chọn 1 trong 2 cách bên dưới.
          </p>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <div className="rounded-lg border border-white/10 bg-white/5 p-3 space-y-2">
          <div className="flex items-baseline justify-between">
            <span className="text-sm text-accent">Tự động</span>
            <span className="text-[10px] uppercase tracking-wide text-gold/70">
              khuyên dùng
            </span>
          </div>
          <p className="text-xs text-white/60">
            Backend sẽ điều khiển Suno đã đăng nhập trên trình duyệt và bấm Create
            giúp bạn (cần Chrome chạy với --remote-debugging-port=29229).
          </p>
          <button
            onClick={generateAuto}
            disabled={auto.status === "running"}
            className="w-full rounded-md bg-gold text-ink px-3 py-2 text-sm font-medium disabled:opacity-50 hover:opacity-90"
          >
            {auto.status === "running"
              ? "Đang tạo bài hát…"
              : "Tạo bài hát tự động →"}
          </button>
          {auto.message && (
            <p
              className={`text-xs ${
                auto.status === "error" ? "text-red-400" : "text-white/70"
              }`}
            >
              {auto.message}
            </p>
          )}
          {auto.url && (
            <a
              href={auto.url}
              target="_blank"
              rel="noopener noreferrer"
              className="block text-xs underline text-accent break-all"
            >
              {auto.url}
            </a>
          )}
        </div>

        <div className="rounded-lg border border-white/10 bg-white/5 p-3 space-y-2">
          <div className="flex items-baseline justify-between">
            <span className="text-sm text-accent">Thủ công</span>
            <span className="text-[10px] uppercase tracking-wide text-white/40">
              an toàn
            </span>
          </div>
          <p className="text-xs text-white/60">
            Copy prompt vào clipboard và mở Suno trong tab mới — bạn paste tay
            vào ô Custom.
          </p>
          <button
            onClick={launchManual}
            disabled={busy}
            className="w-full rounded-md border border-gold/60 text-gold px-3 py-2 text-sm font-medium disabled:opacity-50 hover:bg-gold/10"
          >
            {busy ? "Đang chuẩn bị…" : "Mở Suno (paste tay) →"}
          </button>
          {copied && (
            <p className="text-xs text-accent">
              Prompt đã copy. Paste vào trang Custom của Suno.
            </p>
          )}
          {error && <p className="text-xs text-red-400">{error}</p>}
        </div>
      </div>
    </div>
  );
}
