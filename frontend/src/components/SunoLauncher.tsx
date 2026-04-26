"use client";

import { useState } from "react";
import { api, type SongDraft } from "@/lib/api";

type Props = { draft: SongDraft };

export function SunoLauncher({ draft }: Props) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  async function launch() {
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

  return (
    <div className="rounded-xl border border-gold/40 bg-gold/5 p-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h3 className="font-display text-gold text-lg">Mở trong Suno</h3>
          <p className="text-sm text-white/70">
            Tạo bài hát hoàn chỉnh trên Suno AI với prompt do hội đồng đã tinh chỉnh.
            Prompt sẽ được copy vào clipboard, sẵn sàng paste.
          </p>
        </div>
        <button
          onClick={launch}
          disabled={busy}
          className="rounded-md bg-gold text-ink px-4 py-2 text-sm font-medium disabled:opacity-50 hover:opacity-90"
        >
          {busy ? "Đang chuẩn bị…" : "Mở Suno →"}
        </button>
      </div>
      {copied && (
        <p className="mt-2 text-xs text-accent">
          Prompt đã được copy. Paste vào trang Custom của Suno.
        </p>
      )}
      {error && <p className="mt-2 text-xs text-red-400">{error}</p>}
    </div>
  );
}
