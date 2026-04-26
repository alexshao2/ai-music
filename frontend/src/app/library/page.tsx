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
    <div className="space-y-6">
      <header>
        <h2 className="font-display text-3xl text-accent">Thư viện</h2>
        <p className="text-sm text-white/70">
          Các bản nháp đã được hội đồng tạo trong session này. M5 sẽ thêm
          versioning đầy đủ.
        </p>
      </header>

      {error && <p className="text-sm text-red-400">Lỗi: {error}.</p>}

      {drafts.length === 0 && !error && (
        <p className="text-sm text-white/60">
          Chưa có bản nháp nào. Quay lại{" "}
          <a className="underline text-accent" href="/">
            Studio
          </a>{" "}
          để bắt đầu.
        </p>
      )}

      <ul className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {drafts.map((d) => (
          <li
            key={d.id}
            className="rounded-xl border border-white/10 bg-plum/30 p-4"
          >
            <h3 className="font-display text-lg text-gold">{d.title}</h3>
            <p className="text-xs text-white/60 mt-1">
              {d.brief.genre} · {d.brief.mood} · {d.key} · {d.tempo_bpm} BPM
            </p>
            <p className="text-xs text-white/40 mt-2">id: {d.id}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
