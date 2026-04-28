"use client";

import { useState } from "react";
import type { QualityEvaluation, SongDraft } from "@/lib/api";
import { EvaluationPanel } from "./EvaluationPanel";
import { QualityBadge } from "./QualityBadge";
import { SunoLauncher } from "./SunoLauncher";

export function DraftView({ draft }: { draft: SongDraft }) {
  const [evaluation, setEvaluation] = useState<QualityEvaluation | null>(
    draft.evaluation ?? null,
  );

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-2">
          <p className="chip-mono">draft · đã có bản nháp</p>
          <h2 className="font-display text-3xl tracking-tight">
            <span className="text-atelier">{draft.title}</span>
          </h2>
          <div className="flex flex-wrap gap-1.5">
            <span className="chip-mono">{draft.brief.genre}</span>
            <span className="chip-mono">{draft.brief.mood}</span>
            <span className="chip-mono">{draft.key}</span>
            <span className="chip-mono">{draft.tempo_bpm} BPM</span>
            <span className="chip-mono">{draft.brief.duration_sec}s</span>
          </div>
        </div>
        {evaluation && <QualityBadge evaluation={evaluation} />}
      </header>

      <EvaluationPanel draft={draft} onEvaluationChange={setEvaluation} />

      {evaluation?.verdict === "RELEASE" ? (
        <SunoLauncher draft={draft} />
      ) : (
        <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">
          <p className="text-sm text-amber-400">
            {evaluation
              ? `Bài chưa đạt chuẩn xuất bản (${evaluation.verdict}). Chạy đánh giá A&R hoặc sử dụng Compose Quality để auto-revise.`
              : "Chưa đánh giá chất lượng. Bấm \"Chạy đánh giá A&R\" bên trên."}
          </p>
          <details className="mt-2">
            <summary className="cursor-pointer text-xs text-white/50 hover:text-white/70">
              Vẫn muốn gửi sang Suno?
            </summary>
            <div className="mt-2">
              <SunoLauncher draft={draft} />
            </div>
          </details>
        </div>
      )}

      <section>
        <SectionTitle index="02">Cấu trúc</SectionTitle>
        <ol className="space-y-2">
          {draft.structure.map((s, i) => (
            <li
              key={i}
              className="rounded-lg border border-white/10 bg-white/[0.03] p-3"
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-white">
                  {s.section.replace("_", " ")}
                </span>
                <span className="chip-mono">{s.bars} ô nhịp</span>
              </div>
              {s.chords.length > 0 && (
                <p className="mt-2 font-mono text-[13px] text-white/80">
                  {s.chords.join("  —  ")}
                </p>
              )}
              {s.notes && (
                <p className="mt-1 text-xs italic text-white/60">{s.notes}</p>
              )}
            </li>
          ))}
        </ol>
      </section>

      <section>
        <SectionTitle index="03">Lời nháp</SectionTitle>
        <div className="space-y-3">
          {Object.entries(draft.lyrics).map(([section, text]) => (
            <div
              key={section}
              className="relative rounded-lg border border-white/10 bg-ink/40 p-4 pl-12"
            >
              <span className="absolute left-3 top-3 font-mono text-[10px] uppercase tracking-[0.18em] text-white/45">
                [{section}]
              </span>
              <pre className="whitespace-pre-wrap font-mono text-[13px] leading-relaxed text-white/85">
                {text}
              </pre>
            </div>
          ))}
        </div>
      </section>

      <section>
        <SectionTitle index="04">Hội đồng phát biểu</SectionTitle>
        <ul className="space-y-3">
          {draft.council_log.map((turn, i) => (
            <li
              key={i}
              className="rounded-lg border border-white/10 bg-white/[0.03] p-4"
            >
              <div className="flex items-center gap-2 text-sm font-medium text-white">
                <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-white/45">
                  {String(i + 1).padStart(2, "0")}
                </span>
                {turn.persona}
                <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-white/40">
                  {turn.role}
                </span>
              </div>
              <p className="mt-1.5 text-sm text-white/85">{turn.message}</p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function SectionTitle({
  index,
  children,
}: {
  index: string;
  children: React.ReactNode;
}) {
  return (
    <h3 className="mb-3 flex items-baseline gap-3 font-display text-xl tracking-tight">
      <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-gold">
        {index}
      </span>
      <span className="text-white">{children}</span>
      <span aria-hidden className="flex-1 border-t border-white/10" />
    </h3>
  );
}
