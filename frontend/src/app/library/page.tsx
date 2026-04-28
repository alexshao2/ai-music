import { api, type SongDraft } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function LibraryPage() {
  let drafts: SongDraft[] = [];
  let error: string | null = null;
  try {
    drafts = await api.drafts();
  } catch (e) {
    error = e instanceof Error ? e.message : "Không kết nối được backend";
  }

  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <p className="chip-mono">library · session drafts</p>
        <h2 className="font-display text-4xl tracking-tight">
          Thư <span className="text-atelier">viện</span>
        </h2>
        <p className="max-w-xl text-sm text-white/65">
          Các bản nháp đã được hội đồng tạo trong session này. M5 sẽ thêm
          versioning đầy đủ.
        </p>
      </header>

      {error && (
        <p className="rounded-md border border-red-500/30 bg-red-500/[0.06] p-3 text-sm text-red-300">
          Lỗi: {error}.
        </p>
      )}

      {drafts.length === 0 && !error && (
        <p className="text-sm text-white/60">
          Chưa có bản nháp nào. Quay lại{" "}
          <a className="text-atelier underline decoration-dotted" href="/">
            Studio
          </a>{" "}
          để bắt đầu.
        </p>
      )}

      <ul className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {drafts.map((d, i) => (
          <li key={d.id} className="card card-glow p-5">
            <div className="flex items-start justify-between gap-3">
              <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-gold">
                {String(i + 1).padStart(2, "0")}
              </span>
              <span className="chip-mono">{d.tempo_bpm} BPM</span>
            </div>
            <h3 className="mt-3 font-display text-2xl tracking-tight text-white">
              {d.title}
            </h3>
            <div className="mt-3 flex flex-wrap gap-1.5">
              <span className="chip-mono">{d.brief.genre}</span>
              <span className="chip-mono">{d.brief.mood}</span>
              <span className="chip-mono">{d.key}</span>
            </div>
            <p className="mt-4 font-mono text-[10px] uppercase tracking-[0.18em] text-white/35">
              id · {d.id}
            </p>
          </li>
        ))}
      </ul>
    </div>
  );
}
