"use client";

import { useState } from "react";
import { api, type Brief, type SongDraft } from "@/lib/api";

type Props = {
  onDraft: (draft: SongDraft) => void;
};

const DEFAULTS: Brief = {
  mood: "hoài niệm, dịu dàng",
  genre: "V-pop ballad",
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
    setError(null);
    try {
      const payload: Brief = {
        ...brief,
        references: refsText
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      };
      const draft = await api.compose(payload);
      onDraft(draft);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Lỗi không xác định");
    } finally {
      setBusy(false);
    }
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
        <Field label="Mood">
          <input
            value={brief.mood}
            onChange={(e) => update("mood", e.target.value)}
            className="input"
          />
        </Field>
        <Field label="Thể loại">
          <input
            value={brief.genre}
            onChange={(e) => update("genre", e.target.value)}
            className="input"
          />
        </Field>
        <Field label="Ngôn ngữ lời">
          <select
            value={brief.language}
            onChange={(e) => update("language", e.target.value)}
            className="input"
          >
            <option value="vi">Tiếng Việt</option>
            <option value="en">English</option>
            <option value="ja">日本語</option>
            <option value="ko">한국어</option>
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
        {error && <span className="text-sm text-red-400">{error}</span>}
      </div>

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
