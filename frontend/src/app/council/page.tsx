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
    <div className="space-y-8">
      <header className="space-y-2">
        <p className="chip-mono">council · 06 personas</p>
        <h2 className="font-display text-4xl tracking-tight">
          Hội <span className="text-atelier">đồng</span>
        </h2>
        <p className="max-w-2xl text-sm text-white/65">
          Sáu vai trò chuyên môn cùng tranh luận để xây dựng tác phẩm. Mỗi
          persona có hệ thống prompt và tag chuyên môn riêng.
        </p>
      </header>

      {error && (
        <p className="rounded-md border border-red-500/30 bg-red-500/[0.06] p-3 text-sm text-red-300">
          Không tải được danh sách hội đồng: {error}. Bạn đã chạy backend chưa?
        </p>
      )}

      <ul className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {personas.map((p, i) => (
          <li key={p.role} className="card card-glow p-5">
            <div className="flex items-baseline justify-between gap-3">
              <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-gold">
                {String(i + 1).padStart(2, "0")}
              </span>
              <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-white/45">
                {p.role}
              </span>
            </div>
            <h3 className="mt-2 font-display text-2xl tracking-tight text-white">
              {p.name}
            </h3>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {p.expertise_tags.map((t) => (
                <span key={t} className="chip-mono">
                  {t}
                </span>
              ))}
            </div>
            <p className="mt-4 text-sm leading-relaxed text-white/75">
              {p.system_prompt}
            </p>
          </li>
        ))}
      </ul>
    </div>
  );
}
