"use client";

import { useState } from "react";
import { BriefForm } from "@/components/BriefForm";
import { DraftView } from "@/components/DraftView";
import type { SongDraft } from "@/lib/api";

const PERSONA_BADGES = [
  "Theorist",
  "Composer",
  "Lyricist",
  "Arranger",
  "Producer",
  "Critic",
];

/** Decorative SVG: hand-drawn waveform-grid that hints at composition. */
function HeroWaveformGrid() {
  // 28 bars, each with a deterministic-ish pseudo-random height so the
  // SSR and client output match without requiring useMemo state.
  const bars = Array.from({ length: 28 }, (_, i) => {
    const seed = Math.sin(i * 1.273) * 0.5 + 0.5;
    const h = 18 + Math.round(seed * 64);
    return { i, h };
  });
  return (
    <svg
      aria-hidden
      viewBox="0 0 600 120"
      className="h-24 w-full opacity-80"
      preserveAspectRatio="none"
    >
      <defs>
        <linearGradient id="hero-grad" x1="0" x2="1" y1="0" y2="0">
          <stop offset="0%" stopColor="#ff2d6e" />
          <stop offset="50%" stopColor="#c79bff" />
          <stop offset="100%" stopColor="#3ee5ff" />
        </linearGradient>
      </defs>
      {bars.map(({ i, h }) => (
        <rect
          key={i}
          x={i * 22}
          y={(120 - h) / 2}
          width={6}
          height={h}
          rx={2}
          fill="url(#hero-grad)"
          opacity={0.25 + (i % 4) * 0.18}
        />
      ))}
    </svg>
  );
}

export default function StudioPage() {
  const [draft, setDraft] = useState<SongDraft | null>(null);

  return (
    <div className="space-y-10">
      <section className="card card-glow overflow-hidden p-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-3">
            <p className="chip-mono">studio · sáng tác bản nháp</p>
            <h2 className="font-display text-4xl leading-tight tracking-tight md:text-5xl">
              Một <span className="text-atelier">hội đồng AI</span>
              <br />
              thay vì một prompt.
            </h2>
            <p className="max-w-xl text-sm leading-relaxed text-white/70">
              Theorist, Composer, Lyricist, Arranger, Producer và A&amp;R Critic
              cùng đề xuất một bản nháp dựa trên brief của bạn. Khi hài lòng,
              nhấn <em className="text-white">Mở Suno</em> để hoàn thiện audio.
            </p>
          </div>
          <ul className="flex flex-wrap gap-1.5">
            {PERSONA_BADGES.map((p) => (
              <li key={p} className="chip-mono">{p}</li>
            ))}
          </ul>
        </div>
        <div className="mt-8 -mx-2">
          <HeroWaveformGrid />
        </div>
      </section>

      <BriefForm onDraft={setDraft} />

      {draft && (
        <section className="card p-6">
          <DraftView draft={draft} />
        </section>
      )}
    </div>
  );
}
