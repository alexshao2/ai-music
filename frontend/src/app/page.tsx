"use client";

import { useState } from "react";
import { BriefForm } from "@/components/BriefForm";
import { DraftView } from "@/components/DraftView";
import type { SongDraft } from "@/lib/api";

export default function StudioPage() {
  const [draft, setDraft] = useState<SongDraft | null>(null);

  return (
    <div className="space-y-8">
      <section className="rounded-xl border border-white/10 bg-plum/30 p-6">
        <h2 className="font-display text-2xl text-gold">Studio sáng tác</h2>
        <p className="text-sm text-white/70 mt-1 max-w-2xl">
          Hội đồng cấp cao gồm Music Theorist, Composer, Lyricist, Arranger,
          Producer và A&R Critic sẽ cùng đề xuất một bản nháp dựa trên brief
          của bạn. Khi bạn hài lòng, nhấn <em>Mở Suno</em> để hoàn thiện audio.
        </p>
      </section>

      <BriefForm onDraft={setDraft} />

      {draft && (
        <section className="rounded-xl border border-white/10 bg-white/5 p-5">
          <DraftView draft={draft} />
        </section>
      )}
    </div>
  );
}
