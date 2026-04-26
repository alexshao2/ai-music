import { api, type Persona } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function CouncilPage() {
  let personas: Persona[] = [];
  let error: string | null = null;
  try {
    personas = await api.personas();
  } catch (e) {
    error = e instanceof Error ? e.message : "Không kết nối được backend";
  }

  return (
    <div className="space-y-6">
      <header>
        <h2 className="font-display text-3xl text-accent">Hội đồng</h2>
        <p className="text-sm text-white/70">
          Sáu vai trò chuyên môn cùng tranh luận để xây dựng tác phẩm. Mỗi
          persona có hệ thống prompt và tag chuyên môn riêng.
        </p>
      </header>

      {error && (
        <p className="text-sm text-red-400">
          Không tải được danh sách hội đồng: {error}. Bạn đã chạy backend chưa?
        </p>
      )}

      <ul className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {personas.map((p) => (
          <li
            key={p.role}
            className="rounded-xl border border-white/10 bg-plum/30 p-4"
          >
            <div className="flex items-center justify-between">
              <h3 className="font-display text-xl text-gold">{p.name}</h3>
              <span className="text-xs uppercase tracking-wide text-white/50">
                {p.role}
              </span>
            </div>
            <div className="mt-2 flex flex-wrap gap-1">
              {p.expertise_tags.map((t) => (
                <span
                  key={t}
                  className="rounded-full border border-accent/40 px-2 py-0.5 text-xs text-accent"
                >
                  {t}
                </span>
              ))}
            </div>
            <p className="mt-3 text-sm text-white/80">{p.system_prompt}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
