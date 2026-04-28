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
    <div className="card card-glow space-y-4 p-5">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="chip-mono">suno · export bundle</p>
          <h3 className="mt-2 font-display text-2xl tracking-tight text-white">
            Gửi sang <span className="text-atelier">Suno</span>
          </h3>
          <p className="mt-1 text-sm text-white/65">
            Copy 3 ô bên dưới (Title / Style / Lyrics) rồi mở Suno Custom mode.
          </p>
        </div>
        <button onClick={open} disabled={busy} className="btn-bloom shrink-0">
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
        className="btn-bloom w-full"
      >
        {copied === "all" ? "Đã copy toàn bộ prompt" : "Copy tất cả (Title + Style + Lyrics)"}
      </button>

      {bundle && bundle.negative_tags.length > 0 && (
        <div className="rounded-lg border border-white/10 bg-ink/40 p-3 space-y-1.5">
          <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-white/55">
            Suno — Exclude (paste vào field Exclude Styles)
          </span>
          <p className="font-mono text-sm text-white/80">
            {bundle.negative_tags.join(", ")}
          </p>
        </div>
      )}

      {bundle && bundle.producer_brief && (
        <div className="rounded-lg border border-white/10 bg-ink/40 p-3 space-y-1.5">
          <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-white/55">
            Producer brief (cho engineer / arranger thật)
          </span>
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-white/80">
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
    <div className="rounded-lg border border-white/10 bg-ink/40 p-3 space-y-2">
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-white/55">
          {label}
        </span>
        <button
          onClick={onCopy}
          className="font-mono text-[11px] uppercase tracking-[0.18em] text-atelier hover:underline disabled:opacity-50"
          disabled={!ready}
        >
          {copied ? "· đã copy" : "· copy"}
        </button>
      </div>
      {multiline ? (
        <textarea
          readOnly
          value={value}
          rows={rows}
          className="w-full rounded bg-ink/70 p-2 font-mono text-sm text-white/90"
        />
      ) : (
        <input
          readOnly
          value={value}
          className="w-full rounded bg-ink/70 px-2 py-1.5 font-mono text-sm text-white/90"
        />
      )}
    </div>
  );
}
