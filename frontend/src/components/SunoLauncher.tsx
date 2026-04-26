"use client";

import { useState } from "react";
import { api, type SongDraft } from "@/lib/api";

type Props = { draft: SongDraft };

type CopyKey = "title" | "style" | "lyrics" | "all";

type Bundle = {
  title: string;
  style: string;
  lyrics: string;
  open_url: string;
  negative_tags: string[];
  producer_brief: string;
};

export function SunoLauncher({ draft }: Props) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [bundle, setBundle] = useState<Bundle | null>(null);
  const [copied, setCopied] = useState<CopyKey | null>(null);

  async function load() {
    if (bundle) return bundle;
    setBusy(true);
    setError(null);
    try {
      const data = await api.sunoLaunch(draft.id);
      const b: Bundle = {
        title: data.title,
        style: data.style,
        lyrics: data.lyrics,
        open_url: data.open_url,
        negative_tags: data.negative_tags ?? [],
        producer_brief: data.producer_brief ?? "",
      };
      setBundle(b);
      return b;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Lỗi không xác định");
      return null;
    } finally {
      setBusy(false);
    }
  }

  async function copy(key: CopyKey) {
    const b = await load();
    if (!b) return;
    const text =
      key === "title"
        ? b.title
        : key === "style"
          ? b.style
          : key === "lyrics"
            ? b.lyrics
            : `Title: ${b.title}\n\nStyle:\n${b.style}\n\nLyrics:\n${b.lyrics}`;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(key);
      setTimeout(() => setCopied((c) => (c === key ? null : c)), 1800);
    } catch {
      setError("Trình duyệt chặn clipboard. Hãy copy thủ công từ ô bên dưới.");
    }
  }

  async function open() {
    const b = await load();
    if (b) window.open(b.open_url, "_blank", "noopener,noreferrer");
  }

  return (
    <div className="rounded-xl border border-gold/40 bg-gold/5 p-4 space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h3 className="font-display text-gold text-lg">Gửi sang Suno (paste tay)</h3>
          <p className="text-sm text-white/70">
            Bài hát đã đủ thông tin để bạn paste vào Suno Custom mode. Copy 3 ô dưới rồi
            mở Suno bằng nút bên phải.
          </p>
        </div>
        <button
          onClick={open}
          disabled={busy}
          className="shrink-0 rounded-md border border-gold/60 text-gold px-3 py-2 text-sm font-medium disabled:opacity-50 hover:bg-gold/10"
        >
          {busy ? "Đang chuẩn bị…" : "Mở Suno →"}
        </button>
      </div>

      {error && <p className="text-xs text-red-400">{error}</p>}

      <CopyBlock
        label="Title"
        value={bundle?.title ?? "— bấm Mở Suno để tải"}
        ready={Boolean(bundle)}
        copied={copied === "title"}
        onCopy={() => copy("title")}
      />
      <CopyBlock
        label="Style"
        value={bundle?.style ?? "—"}
        ready={Boolean(bundle)}
        copied={copied === "style"}
        onCopy={() => copy("style")}
        multiline
      />
      <CopyBlock
        label="Lyrics"
        value={bundle?.lyrics ?? "—"}
        ready={Boolean(bundle)}
        copied={copied === "lyrics"}
        onCopy={() => copy("lyrics")}
        multiline
        rows={10}
      />
      <button
        onClick={() => copy("all")}
        disabled={busy}
        className="w-full rounded-md bg-gold text-ink px-3 py-2 text-sm font-medium disabled:opacity-50 hover:opacity-90"
      >
        {copied === "all" ? "Đã copy toàn bộ prompt" : "Copy tất cả (Title + Style + Lyrics)"}
      </button>

      {bundle && bundle.negative_tags.length > 0 && (
        <div className="rounded-lg border border-white/10 bg-white/5 p-3 space-y-1">
          <span className="text-xs uppercase tracking-wide text-white/60">
            Suno — Exclude (paste vào field Exclude Styles)
          </span>
          <p className="text-sm text-white/80 font-mono">
            {bundle.negative_tags.join(", ")}
          </p>
        </div>
      )}

      {bundle && bundle.producer_brief && (
        <div className="rounded-lg border border-white/10 bg-white/5 p-3 space-y-1">
          <span className="text-xs uppercase tracking-wide text-white/60">
            Producer brief (cho engineer / arranger thật)
          </span>
          <p className="text-sm text-white/80 whitespace-pre-wrap leading-relaxed">
            {bundle.producer_brief}
          </p>
        </div>
      )}
    </div>
  );
}

function CopyBlock({
  label,
  value,
  ready,
  copied,
  onCopy,
  multiline = false,
  rows = 3,
}: {
  label: string;
  value: string;
  ready: boolean;
  copied: boolean;
  onCopy: () => void;
  multiline?: boolean;
  rows?: number;
}) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/5 p-3 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs uppercase tracking-wide text-white/60">{label}</span>
        <button
          onClick={onCopy}
          className="text-xs text-accent hover:underline disabled:opacity-50"
          disabled={!ready}
        >
          {copied ? "Đã copy" : "Copy"}
        </button>
      </div>
      {multiline ? (
        <textarea
          readOnly
          value={value}
          rows={rows}
          className="w-full bg-ink/60 text-white/90 text-sm rounded p-2 font-mono"
        />
      ) : (
        <input
          readOnly
          value={value}
          className="w-full bg-ink/60 text-white/90 text-sm rounded px-2 py-1"
        />
      )}
    </div>
  );
}
