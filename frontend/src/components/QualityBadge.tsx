import type { QualityEvaluation } from "@/lib/api";

const VERDICT_STYLES = {
  RELEASE: "bg-emerald-500/20 text-emerald-400 border-emerald-500/40",
  REVISE: "bg-amber-500/20 text-amber-400 border-amber-500/40",
  REJECT: "bg-red-500/20 text-red-400 border-red-500/40",
} as const;

const VERDICT_LABELS = {
  RELEASE: "Xuất bản",
  REVISE: "Cần sửa",
  REJECT: "Từ chối",
} as const;

export function QualityBadge({
  evaluation,
}: {
  evaluation: QualityEvaluation;
}) {
  const v = evaluation.verdict;
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide ${VERDICT_STYLES[v]}`}
    >
      <span className="text-base leading-none">
        {v === "RELEASE" ? "\u25CF" : v === "REVISE" ? "\u25B2" : "\u25A0"}
      </span>
      {VERDICT_LABELS[v]}
      <span className="ml-1 font-mono text-[10px] opacity-80">
        {evaluation.scores.overall.toFixed(1)}
      </span>
    </span>
  );
}
