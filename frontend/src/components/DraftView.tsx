import type { SongDraft } from "@/lib/api";
import { EvaluationPanel } from "./EvaluationPanel";
import { QualityBadge } from "./QualityBadge";
import { SunoLauncher } from "./SunoLauncher";

export function DraftView({ draft }: { draft: SongDraft }) {
  return (
    <div className="space-y-6">
      <header className="flex items-baseline justify-between">
        <div>
          <h2 className="font-display text-3xl text-accent">{draft.title}</h2>
          <p className="text-sm text-white/60">
            {draft.brief.genre} · {draft.brief.mood} · {draft.key} ·{" "}
            {draft.tempo_bpm} BPM · {draft.brief.duration_sec}s
          </p>
        </div>
        {draft.evaluation && <QualityBadge evaluation={draft.evaluation} />}
      </header>

      <EvaluationPanel draft={draft} />

      {draft.evaluation?.verdict === "RELEASE" ? (
        <SunoLauncher draft={draft} />
      ) : (
        <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">
          <p className="text-sm text-amber-400">
            {draft.evaluation
              ? `Bài chưa đạt chuẩn xuất bản (${draft.evaluation.verdict}). Chạy đánh giá A&R hoặc sử dụng Compose Quality để auto-revise.`
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
        <h3 className="font-display text-xl text-gold mb-2">Cấu trúc</h3>
        <ol className="space-y-2">
          {draft.structure.map((s, i) => (
            <li
              key={i}
              className="rounded-lg border border-white/10 bg-white/5 p-3"
            >
              <div className="flex items-center justify-between">
                <span className="uppercase tracking-wide text-sm text-accent">
                  {s.section.replace("_", " ")}
                </span>
                <span className="text-xs text-white/50">{s.bars} ô nhịp</span>
              </div>
              {s.chords.length > 0 && (
                <p className="mt-1 text-sm text-white/80">
                  Hợp âm: {s.chords.join(" — ")}
                </p>
              )}
              {s.notes && (
                <p className="mt-1 text-xs text-white/60 italic">{s.notes}</p>
              )}
            </li>
          ))}
        </ol>
      </section>

      <section>
        <h3 className="font-display text-xl text-gold mb-2">Lời nháp</h3>
        <pre className="whitespace-pre-wrap rounded-lg border border-white/10 bg-white/5 p-3 text-sm text-white/85">
          {Object.entries(draft.lyrics)
            .map(([k, v]) => `[${k}]\n${v}`)
            .join("\n\n")}
        </pre>
      </section>

      <section>
        <h3 className="font-display text-xl text-gold mb-2">Hội đồng phát biểu</h3>
        <ul className="space-y-3">
          {draft.council_log.map((turn, i) => (
            <li
              key={i}
              className="rounded-lg border border-white/10 bg-plum/40 p-3"
            >
              <div className="text-sm font-medium text-accent">
                {turn.persona}{" "}
                <span className="text-white/40 text-xs">({turn.role})</span>
              </div>
              <p className="mt-1 text-sm text-white/85">{turn.message}</p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
