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
  const color =
    score >= 7.5
      ? "bg-emerald-500"
      : score >= 5
        ? "bg-amber-500"
        : "bg-red-500";

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-white/70">
          {label}{" "}
          <span className="text-white/40">({weight}%)</span>
        </span>
        <span className="font-mono text-white/90">{score.toFixed(1)}</span>
      </div>
      <div className="h-2 w-full rounded-full bg-white/10">
        <div
          className={`h-full rounded-full transition-all duration-500 ${color}`}
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
    <div className="rounded-xl border border-white/10 bg-white/5 p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-display text-lg text-gold">
          Đánh giá chất lượng
        </h3>
        <div className="flex items-center gap-3">
          {evaluation && <QualityBadge evaluation={evaluation} />}
          <button
            onClick={runEvaluation}
            disabled={loading}
            className="rounded-md border border-gold/60 text-gold px-3 py-1.5 text-sm font-medium disabled:opacity-50 hover:bg-gold/10"
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

          <div className="rounded-lg border border-white/10 bg-white/5 p-3 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs uppercase tracking-wide text-white/60">
                Overall Score
              </span>
              <span className="font-mono text-lg font-bold text-gold">
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
