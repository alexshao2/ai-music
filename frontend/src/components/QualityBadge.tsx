import type { QualityEvaluation } from "@/lib/api";

const VERDICT_LABELS = {
  RELEASE: "Xuất bản",
  REVISE: "Cần sửa",
  REJECT: "Từ chối",
} as const;

const VERDICT_TONE = {
  RELEASE: { ring: "stroke-emerald-400", text: "text-emerald-300", bg: "bg-emerald-500/10 border-emerald-500/30" },
  REVISE: { ring: "stroke-amber-400", text: "text-amber-300", bg: "bg-amber-500/10 border-amber-500/30" },
  REJECT: { ring: "stroke-red-400", text: "text-red-300", bg: "bg-red-500/10 border-red-500/30" },
} as const;

/** Donut gauge: shows overall score 0–10 as a stroke-arc + verdict label. */
export function QualityBadge({
  evaluation,
}: {
  evaluation: QualityEvaluation;
}) {
  const v = evaluation.verdict;
  const score = Math.max(0, Math.min(10, evaluation.scores.overall));
  const radius = 22;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - score / 10);
  const tone = VERDICT_TONE[v];

  return (
    <div
      className={`flex items-center gap-3 rounded-xl border px-3 py-2 ${tone.bg}`}
    >
      <div className="relative h-12 w-12">
        <svg viewBox="0 0 50 50" className="h-12 w-12 -rotate-90">
          <circle
            cx={25}
            cy={25}
            r={radius}
            className="stroke-white/10"
            strokeWidth={4}
            fill="none"
          />
          <circle
            cx={25}
            cy={25}
            r={radius}
            className={tone.ring}
            strokeWidth={4}
            fill="none"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center font-mono text-[12px] font-semibold text-white">
          {score.toFixed(1)}
        </div>
      </div>
      <div className="flex flex-col">
        <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-white/50">
          A&amp;R verdict
        </span>
        <span className={`font-display text-sm ${tone.text}`}>
          {VERDICT_LABELS[v]}
        </span>
      </div>
    </div>
  );
}
