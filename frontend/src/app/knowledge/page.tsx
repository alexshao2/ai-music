import { api, type KnowledgeChunk } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function KnowledgePage() {
  let topics: KnowledgeChunk[] = [];
  let error: string | null = null;
  try {
    topics = await api.knowledgeTopics();
  } catch (e) {
    error = e instanceof Error ? e.message : "Không kết nối được backend";
  }

  // Group by top-level folder.
  const groups = new Map<string, KnowledgeChunk[]>();
  for (const t of topics) {
    const folder = t.path.split("/")[0] ?? "khác";
    if (!groups.has(folder)) groups.set(folder, []);
    groups.get(folder)!.push(t);
  }

  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <p className="chip-mono">knowledge · rag corpus</p>
        <h2 className="font-display text-4xl tracking-tight">
          Kho <span className="text-atelier">kiến thức</span>
        </h2>
        <p className="max-w-2xl text-sm text-white/65">
          Markdown corpus được hội đồng truy vấn khi sáng tác. Bạn có thể đóng
          góp thêm bằng cách đặt file <code className="rounded bg-white/[0.06] px-1.5 py-0.5 font-mono text-[12px]">.md</code> mới vào thư mục tương ứng — xem{" "}
          <code className="rounded bg-white/[0.06] px-1.5 py-0.5 font-mono text-[12px]">AGENTS.md</code>.
        </p>
      </header>

      {error && (
        <p className="rounded-md border border-red-500/30 bg-red-500/[0.06] p-3 text-sm text-red-300">
          Không tải được kho kiến thức: {error}.
        </p>
      )}

      {[...groups.entries()].map(([folder, items]) => (
        <section key={folder} className="space-y-3">
          <h3 className="flex items-baseline gap-3 font-display text-xl tracking-tight">
            <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-gold">
              {folder}
            </span>
            <span aria-hidden className="flex-1 border-t border-white/10" />
            <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-white/45">
              {items.length} chunk
            </span>
          </h3>
          <ul className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {items.map((it) => (
              <li
                key={it.path}
                className="rounded-lg border border-white/10 bg-white/[0.03] p-4 transition-colors hover:border-white/25"
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm font-medium text-white">
                    {it.title}
                  </span>
                  {it.level && (
                    <span className="chip-mono">{it.level}</span>
                  )}
                </div>
                {it.tags.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {it.tags.map((t) => (
                      <span key={t} className="chip-mono">
                        {t}
                      </span>
                    ))}
                  </div>
                )}
                <p className="mt-3 line-clamp-3 text-xs leading-relaxed text-white/65">
                  {it.excerpt}
                </p>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
