"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  api,
  composeStream,
  composeQualityStream,
  type Brief,
  type BriefOptions,
  type GenreOption,
  type MoodOption,
  type SongDraft,
} from "@/lib/api";
import {
  applyEvent,
  CouncilTimeline,
  type CouncilAttempt,
} from "@/components/CouncilTimeline";

const CUSTOM_VALUE = "__custom__";

function groupBy<T, K extends string>(items: T[], key: (t: T) => K): Map<K, T[]> {
  const out = new Map<K, T[]>();
  for (const item of items) {
    const k = key(item);
    const list = out.get(k);
    if (list) list.push(item);
    else out.set(k, [item]);
  }
  return out;
}

type Props = {
  onDraft: (draft: SongDraft) => void;
};

// Default brief values. `mood` and `genre` match one of the backend's
// picker options (see app/services/options.py) so the select defaults to
// an actual entry instead of "Tự nhập…". If the backend genre titles ever
// change, the form falls back to custom-input gracefully.
const DEFAULTS: Brief = {
  mood: "Hoài niệm, dịu dàng",
  genre: "V-pop Ballad — Sound, Form, Idioms (2018–2025)",
  language: "vi",
  duration_sec: 210,
  references: [],
  notes: "",
};

export function BriefForm({ onDraft }: Props) {
  const [brief, setBrief] = useState<Brief>(DEFAULTS);
  const [refsText, setRefsText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [questions, setQuestions] = useState<string[] | null>(null);
  const [fastMode, setFastMode] = useState(false);
  const [qualityMode, setQualityMode] = useState(false);
  const [targetScore, setTargetScore] = useState(7.5);
  const [maxRevisions, setMaxRevisions] = useState(2);
  const [progress, setProgress] = useState<string | null>(null);
  const [attempts, setAttempts] = useState<CouncilAttempt[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [options, setOptions] = useState<BriefOptions | null>(null);
  const [customMood, setCustomMood] = useState(false);
  const [customGenre, setCustomGenre] = useState(false);
  const startedAtRef = useRef<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!streaming) return;
    const t = setInterval(() => {
      if (startedAtRef.current != null) {
        setElapsed((Date.now() - startedAtRef.current) / 1000);
      }
    }, 500);
    return () => clearInterval(t);
  }, [streaming]);

  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  // Load picker options from the backend on mount. If the request fails we
  // silently keep the form in free-text mode (the label inputs still work).
  useEffect(() => {
    let cancelled = false;
    api
      .briefOptions()
      .then((opts) => {
        if (cancelled) return;
        setOptions(opts);
        setCustomMood(!opts.moods.some((m) => m.label === brief.mood));
        setCustomGenre(!opts.genres.some((g) => g.label === brief.genre));
      })
      .catch(() => {
        // Leave options=null; the form falls back to free-text inputs.
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const moodGroups = useMemo(() => {
    if (!options) return null;
    return Array.from(
      groupBy<MoodOption, string>(options.moods, (m) => m.group).entries(),
    );
  }, [options]);

  const genreGroups = useMemo(() => {
    if (!options) return null;
    // Preserve the backend's sort order — groupBy is insertion-ordered.
    return Array.from(
      groupBy<GenreOption, string>(options.genres, (g) => g.group_label).entries(),
    );
  }, [options]);

  function update<K extends keyof Brief>(k: K, v: Brief[K]) {
    setBrief((b) => ({ ...b, [k]: v }));
  }

  async function askCouncil() {
    setBusy(true);
    setError(null);
    try {
      const payload: Brief = {
        ...brief,
        references: refsText
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      };
      const r = await api.briefIntake(payload);
      setQuestions(r.clarifying_questions);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Lỗi không xác định");
    } finally {
      setBusy(false);
    }
  }

  async function compose() {
    setBusy(true);
    setStreaming(true);
    setError(null);
    setAttempts([]);
    setElapsed(0);
    startedAtRef.current = Date.now();
    setProgress(
      qualityMode
        ? `Chế độ tự sửa — tối đa ${maxRevisions + 1} vòng hội đồng cho đến khi score ≥ ${targetScore.toFixed(1)}. Mỗi vòng ~5–7 phút trên LLM chậm.`
        : fastMode
        ? "Chế độ nhanh — ~3-4 phút. Theo dõi từng vị nói trực tiếp bên dưới."
        : "Chế độ đầy đủ — ~5-7 phút (gồm tinh chỉnh sau Critic). Bạn sẽ thấy từng vị phát biểu real-time."
    );
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    try {
      const payload: Brief = {
        ...brief,
        references: refsText
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      };
      let receivedDraft: SongDraft | null = null;
      let streamError: string | null = null;
      const handleEvent = (ev: Parameters<Parameters<typeof composeQualityStream>[2]>[0]) => {
        if (ev.type === "draft") {
          receivedDraft = ev.draft;
          return;
        }
        if (ev.type === "error") {
          streamError = ev.message;
          return;
        }
        setAttempts((prev) => applyEvent(prev, ev));
      };
      if (qualityMode) {
        await composeQualityStream(
          payload,
          {
            fast: fastMode,
            targetScore,
            maxRevisions,
            signal: ctrl.signal,
          },
          handleEvent,
        );
      } else {
        await composeStream(
          payload,
          { fast: fastMode, signal: ctrl.signal },
          handleEvent,
        );
      }
      if (receivedDraft) {
        onDraft(receivedDraft);
      } else if (streamError) {
        setError(streamError);
      } else {
        setError("Stream kết thúc nhưng không có draft.");
      }
    } catch (e) {
      if (!(e instanceof DOMException && e.name === "AbortError")) {
        setError(e instanceof Error ? e.message : "Lỗi không xác định");
      }
    } finally {
      setBusy(false);
      setStreaming(false);
      setProgress(null);
      startedAtRef.current = null;
      abortRef.current = null;
    }
  }

  function cancelCompose() {
    abortRef.current?.abort();
  }

  return (
    <div className="rounded-xl border border-white/10 bg-white/5 p-5 space-y-4">
      <div>
        <h2 className="font-display text-2xl text-accent">Brief sáng tác</h2>
        <p className="text-sm text-white/60">
          Mô tả ý tưởng — hội đồng sẽ đặt câu hỏi và đề xuất bản nháp đầu tiên.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Field label="Mood / Tâm trạng">
          {moodGroups ? (
            <div className="space-y-2">
              <select
                value={customMood ? CUSTOM_VALUE : brief.mood}
                onChange={(e) => {
                  const v = e.target.value;
                  if (v === CUSTOM_VALUE) {
                    setCustomMood(true);
                    update("mood", "");
                  } else {
                    setCustomMood(false);
                    update("mood", v);
                  }
                }}
                className="input"
              >
                {moodGroups.map(([group, moods]) => (
                  <optgroup key={group} label={group}>
                    {moods.map((m) => (
                      <option key={m.slug} value={m.label}>
                        {m.label}
                      </option>
                    ))}
                  </optgroup>
                ))}
                <option value={CUSTOM_VALUE}>Tự nhập mood khác…</option>
              </select>
              {customMood && (
                <input
                  value={brief.mood}
                  onChange={(e) => update("mood", e.target.value)}
                  className="input"
                  placeholder="ví dụ: hoài niệm phai nhạt, bồi hồi ấm áp"
                  autoFocus
                />
              )}
            </div>
          ) : (
            <input
              value={brief.mood}
              onChange={(e) => update("mood", e.target.value)}
              className="input"
            />
          )}
        </Field>
        <Field label="Thể loại / Genre">
          {genreGroups ? (
            <div className="space-y-2">
              <select
                value={customGenre ? CUSTOM_VALUE : brief.genre}
                onChange={(e) => {
                  const v = e.target.value;
                  if (v === CUSTOM_VALUE) {
                    setCustomGenre(true);
                    update("genre", "");
                  } else {
                    setCustomGenre(false);
                    update("genre", v);
                  }
                }}
                className="input"
              >
                {genreGroups.map(([group, genres]) => (
                  <optgroup key={group} label={group}>
                    {genres.map((g) => (
                      <option key={g.slug} value={g.label}>
                        {g.label}
                      </option>
                    ))}
                  </optgroup>
                ))}
                <option value={CUSTOM_VALUE}>Tự nhập thể loại khác…</option>
              </select>
              {customGenre && (
                <input
                  value={brief.genre}
                  onChange={(e) => update("genre", e.target.value)}
                  className="input"
                  placeholder="ví dụ: V-pop ballad, indie folk, synthwave"
                  autoFocus
                />
              )}
            </div>
          ) : (
            <input
              value={brief.genre}
              onChange={(e) => update("genre", e.target.value)}
              className="input"
            />
          )}
        </Field>
        <Field label="Ngôn ngữ lời">
          <select
            value={brief.language}
            onChange={(e) => update("language", e.target.value)}
            className="input"
          >
            {(options?.languages ?? [
              { code: "vi", label: "Tiếng Việt" },
              { code: "en", label: "English" },
              { code: "ja", label: "日本語" },
              { code: "ko", label: "한국어" },
            ]).map((l) => (
              <option key={l.code} value={l.code}>
                {l.label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Thời lượng (giây)">
          <input
            type="number"
            min={30}
            max={600}
            value={brief.duration_sec}
            onChange={(e) =>
              update("duration_sec", Number(e.target.value || 180))
            }
            className="input"
          />
        </Field>
        <Field label="Bài tham chiếu (phân cách dấu phẩy)">
          <input
            value={refsText}
            onChange={(e) => setRefsText(e.target.value)}
            className="input"
            placeholder="Ví dụ: 'Hà Anh Tuấn — Tháng Tư là lời nói dối của em', ..."
          />
        </Field>
        <Field label="Ghi chú">
          <input
            value={brief.notes ?? ""}
            onChange={(e) => update("notes", e.target.value)}
            className="input"
          />
        </Field>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <button
          onClick={askCouncil}
          disabled={busy}
          className="rounded-md border border-accent/50 bg-accent/10 px-4 py-2 text-sm hover:bg-accent/20 disabled:opacity-50"
        >
          {busy ? "Đang hỏi…" : "Hỏi hội đồng"}
        </button>
        <button
          onClick={compose}
          disabled={busy}
          className="rounded-md bg-accent text-ink px-4 py-2 text-sm font-medium disabled:opacity-50 hover:opacity-90"
        >
          {busy ? "Đang sáng tác…" : "Sáng tác bản nháp"}
        </button>
        {streaming && (
          <button
            onClick={cancelCompose}
            className="rounded-md border border-red-400/50 text-red-300 px-3 py-2 text-xs hover:bg-red-500/10"
          >
            Huỷ
          </button>
        )}
        <label className="flex items-center gap-2 text-xs text-white/70 select-none">
          <input
            type="checkbox"
            checked={fastMode}
            onChange={(e) => setFastMode(e.target.checked)}
            disabled={qualityMode}
            className="accent-accent"
          />
          Chế độ nhanh (bỏ qua tinh chỉnh sau Critic)
        </label>
        <label className="flex items-center gap-2 text-xs text-white/70 select-none">
          <input
            type="checkbox"
            checked={qualityMode}
            onChange={(e) => {
              setQualityMode(e.target.checked);
              if (e.target.checked) setFastMode(false);
            }}
            className="accent-accent"
          />
          Tự sửa đến khi đạt điểm
        </label>
        {qualityMode && (
          <div className="flex items-center gap-2 text-xs text-white/70">
            <label className="flex items-center gap-1">
              Điểm mục tiêu
              <input
                type="number"
                min={0}
                max={10}
                step={0.5}
                value={targetScore}
                onChange={(e) =>
                  setTargetScore(Math.min(10, Math.max(0, Number(e.target.value || 0))))
                }
                className="w-16 rounded bg-white/5 border border-white/10 px-1.5 py-0.5"
              />
            </label>
            <label className="flex items-center gap-1">
              Số vòng sửa tối đa
              <input
                type="number"
                min={0}
                max={5}
                value={maxRevisions}
                onChange={(e) =>
                  setMaxRevisions(Math.min(5, Math.max(0, Number(e.target.value || 0))))
                }
                className="w-12 rounded bg-white/5 border border-white/10 px-1.5 py-0.5"
              />
            </label>
          </div>
        )}
        {error && <span className="text-sm text-red-400">{error}</span>}
      </div>

      {progress && (
        <p className="text-xs text-white/60 italic">{progress}</p>
      )}

      {(streaming || attempts.length > 0) && (
        <CouncilTimeline attempts={attempts} elapsedSec={elapsed} />
      )}

      {questions && questions.length > 0 && (
        <div className="rounded-lg border border-accent/30 bg-plum/40 p-3">
          <p className="text-sm text-accent mb-2">
            Hội đồng cần làm rõ:
          </p>
          <ul className="list-disc pl-5 text-sm text-white/85 space-y-1">
            {questions.map((q, i) => (
              <li key={i}>{q}</li>
            ))}
          </ul>
        </div>
      )}

      <style jsx>{`
        .input {
          width: 100%;
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 6px;
          padding: 8px 10px;
          color: #f5f1ea;
          font-size: 14px;
        }
        .input:focus {
          outline: 2px solid #c79bff;
        }
      `}</style>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="block text-xs uppercase tracking-wide text-white/60 mb-1">
        {label}
      </span>
      {children}
    </label>
  );
}
