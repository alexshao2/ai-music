# Kiến trúc

## Tầng

```
┌──────────────────────────────────────────────────────────┐
│                     Frontend (Next.js)                   │
│  Studio UI · Chat panel · Knowledge browser · Suno btn   │
└───────────────────────────┬──────────────────────────────┘
                            │ HTTP/JSON
┌───────────────────────────▼──────────────────────────────┐
│                     Backend (FastAPI)                    │
│  ┌─────────────┬──────────────┬──────────┬────────────┐  │
│  │  /council   │  /knowledge  │ /studio  │  /suno     │  │
│  └──────┬──────┴───────┬──────┴────┬─────┴──────┬─────┘  │
│         │              │           │            │        │
│  ┌──────▼─────┐ ┌──────▼──────┐ ┌──▼──────┐ ┌───▼─────┐  │
│  │  Council   │ │  Retrieval  │ │ Drafts  │ │  Suno   │  │
│  │  Engine    │ │  (RAG)      │ │  Store  │ │ Bridge  │  │
│  └──────┬─────┘ └──────┬──────┘ └──────────┘ └─────────┘  │
│         │              │                                  │
│  ┌──────▼──────────────▼─────┐                           │
│  │     LLM Provider (OpenAI │ Anthropic │ ...)          │
│  └───────────────────────────┘                           │
└──────────────────────────────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────┐
│              knowledge/  (markdown corpus)               │
│   theory · harmony · songwriting · genres · arrangement  │
│   lyrics · production                                    │
└──────────────────────────────────────────────────────────┘
```

## Luồng "sáng tác một bài hát"

1. **User mô tả ý tưởng** ở Studio (mood, thể loại, tham chiếu, độ dài, ngôn ngữ lời).
2. **Studio gọi `/council/brief`** — hội đồng đọc brief, trả về danh sách câu hỏi làm rõ.
3. **User trả lời**, hoặc bỏ qua → council tự đưa giả định.
4. **`/council/compose`** — mỗi persona đóng góp:
   - *Music Theorist*: tonic, mode, vòng hợp âm gợi ý.
   - *Composer*: motif giai điệu, cấu trúc (intro/verse/chorus/bridge/outro).
   - *Lyricist*: theme, hook, draft lời.
   - *Arranger*: instrumentation, dynamics map.
   - *Producer*: sound palette, reference tracks.
   - *A&R Critic*: phản biện, chỉ ra điểm yếu.
5. **Synthesizer** tổng hợp thành một **Song Draft** (xem schema bên dưới).
6. **User tinh chỉnh** từng phần → gọi lại các endpoint cụ thể.
7. **Khi sẵn sàng**, `/suno/prompt` build prompt Suno tối ưu (style + lyrics) và frontend mở `suno.com/create`.

## Song Draft — schema

```ts
{
  "id": "uuid",
  "title": "string",
  "brief": { "mood": "...", "genre": "...", "language": "vi", "duration_sec": 180 },
  "key": "C major",
  "tempo_bpm": 92,
  "structure": [
    { "section": "intro",  "bars": 4 },
    { "section": "verse",  "bars": 16, "chords": ["C","G","Am","F"] },
    { "section": "chorus", "bars": 16, "chords": ["F","C","G","Am"] },
    ...
  ],
  "lyrics": { "verse_1": "...", "chorus": "...", ... },
  "arrangement": { "instruments": ["acoustic guitar","piano","strings"], "notes": "..." },
  "production": { "palette": "warm, intimate", "reference": "..." },
  "council_log": [
    { "persona": "Theorist", "turn": 1, "message": "..." },
    ...
  ],
  "suno_prompt": { "style": "...", "lyrics": "..." }
}
```

## Lưu trữ

- M0: file JSON dưới `backend/app/data/sessions/`.
- M5: SQLite + migrations, có version cho từng draft.

## Retrieval (knowledge base)

- M0: keyword matching đơn giản (title + tags) — đủ cho prototype.
- M1: chunk các markdown theo heading, embed (text-embedding-3-small hoặc tương đương), lưu vào FAISS/Chroma local.
- Council mỗi turn truy xuất top-K passages liên quan, đính kèm vào system prompt của persona tương ứng.

## Suno bridge

Suno chưa có API công khai cho user thường, nên M0 dùng **launcher pattern**:

1. Backend xuất `style` (≤200 ký tự) và `lyrics` từ draft.
2. Frontend copy cả hai vào clipboard và mở `https://suno.com/create` ở tab mới.
3. User dán vào Suno UI và nhấn Create.

M4 sẽ đánh giá khả năng dùng Playwright để auto-fill khi user đã đăng nhập Suno.
