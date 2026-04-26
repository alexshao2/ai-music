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
    <div className="space-y-6">
      <header>
        <h2 className="font-display text-3xl text-accent">Kho kiến thức</h2>
        <p className="text-sm text-white/70 max-w-2xl">
          Markdown corpus được hội đồng truy vấn khi sáng tác. Bạn có thể đóng
          góp thêm bằng cách đặt file `.md` mới vào thư mục tương ứng — xem
          `AGENTS.md`.
        </p>
      </header>

      {error && (
        <p className="text-sm text-red-400">
          Không tải được kho kiến thức: {error}.
        </p>
      )}

      {[...groups.entries()].map(([folder, items]) => (
        <section key={folder}>
          <h3 className="font-display text-xl text-gold mb-2 uppercase tracking-wide">
            {folder}
          </h3>
          <ul className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {items.map((it) => (
              <li
                key={it.path}
                className="rounded-lg border border-white/10 bg-white/5 p-3"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-accent">
                    {it.title}
                  </span>
                  {it.level && (
                    <span className="text-xs text-white/50">{it.level}</span>
                  )}
                </div>
                {it.tags.length > 0 && (
                  <div className="mt-1 flex flex-wrap gap-1">
                    {it.tags.map((t) => (
                      <span
                        key={t}
                        className="rounded-full bg-accent/10 px-2 py-0.5 text-xs text-accent/90"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                )}
                <p className="mt-2 text-xs text-white/70 line-clamp-3">
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
