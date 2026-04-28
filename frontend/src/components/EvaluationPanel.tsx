"use client";

import { useState } from "react";
import { api, type QualityEvaluation, type SongDraft } from "@/lib/api";
import { QualityBadge } from "./QualityBadge";

const DIMENSION_LABELS: Record<string, string> = {
  melody_catchiness: "Melody & Hook",
  lyric_quality: "Chất lượng lời",
  harmonic_sophistication: "Hoà âm",
  structural_coherence: "Cấu trúc",
  production_direction: "Production",
  genre_authenticity: "Genre Authenticity",
};

const DIMENSION_WEIGHTS: Record<string, number> = {
  melody_catchiness: 20,
  lyric_quality: 20,
  genre_authenticity: 20,
  structural_coherence: 15,
  production_direction: 15,
  harmonic_sophistication: 10,
};

function ScoreBar({ label, score, weight }: { label: string; score: number; weight: number }) {
  const pct = (score / 10) * 100;
  // Healthy scores ride the atelier gradient; anything <5 turns red.
  const fill =
    score >= 5 ? "bg-atelier" : "bg-red-500";

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-2 text-xs text-white/75">
          {label}
          <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-white/40">
            {weight}%
          </span>
        </span>
        <span className="font-mono text-[12px] text-white/90">
          {score.toFixed(1)}
        </span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/[0.06]">
        <div
          className={`h-full rounded-full transition-all duration-500 ${fill}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export function EvaluationPanel({
  draft,
  onEvaluationChange,
}: {
  draft: SongDraft;
  onEvaluationChange?: (evaluation: QualityEvaluation) => void;
}) {
  const [evaluation, setEvaluation] = useState<QualityEvaluation | null>(
    draft.evaluation ?? null,
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function runEvaluation() {
    setLoading(true);
    setError(null);
    try {
      const result = await api.evaluateDraft(draft.id);
      setEvaluation(result);
      onEvaluationChange?.(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Lỗi không xác định");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card p-5 space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="chip-mono">a&amp;r · quality gate</p>
          <h3 className="mt-2 font-display text-xl tracking-tight text-white">
            Đánh giá <span className="text-atelier">chất lượng</span>
          </h3>
        </div>
        <div className="flex items-center gap-3">
          {evaluation && <QualityBadge evaluation={evaluation} />}
          <button
            onClick={runEvaluation}
            disabled={loading}
            className="btn-ghost"
          >
            {loading
              ? "Đang đánh giá…"
              : evaluation
                ? "Đánh giá lại"
                : "Chạy đánh giá A&R"}
          </button>
        </div>
      </div>

      {error && <p className="text-xs text-red-400">{error}</p>}

      {evaluation && (
        <>
          <div className="grid gap-3">
            {Object.entries(DIMENSION_LABELS).map(([key, label]) => (
              <ScoreBar
                key={key}
                label={label}
                score={
                  evaluation.scores[key as keyof typeof evaluation.scores] ?? 0
                }
                weight={DIMENSION_WEIGHTS[key] ?? 0}
              />
            ))}
          </div>

          <div className="rounded-lg border border-white/10 bg-ink/40 p-3 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-white/55">
                Overall Score
              </span>
              <span className="font-mono text-lg font-bold text-atelier">
                {evaluation.scores.overall.toFixed(1)}/10
              </span>
            </div>
            {evaluation.attempt > 1 && (
              <p className="text-xs text-white/50">
                Attempt #{evaluation.attempt}
                {evaluation.max_attempts_reached && " (max reached)"}
              </p>
            )}
          </div>

          {evaluation.feedback && (
            <div className="rounded-lg border border-white/10 bg-white/5 p-3 space-y-1">
              <span className="text-xs uppercase tracking-wide text-white/60">
                Nhận xét A&R
              </span>
              <p className="text-sm text-white/85 whitespace-pre-wrap leading-relaxed">
                {evaluation.feedback}
              </p>
            </div>
          )}

          {evaluation.verdict !== "RELEASE" && evaluation.revision_notes && (
            <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3 space-y-1">
              <span className="text-xs uppercase tracking-wide text-amber-400">
                Hướng dẫn sửa
              </span>
              <p className="text-sm text-white/85 whitespace-pre-wrap leading-relaxed">
                {evaluation.revision_notes}
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
