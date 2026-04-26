# Roadmap

## M0 — Skeleton (đang ở đây)

- [x] Monorepo structure: backend, frontend, knowledge, docs.
- [x] FastAPI app với endpoints stub: `/council`, `/knowledge`, `/studio`, `/suno`.
- [x] Council persona definitions (7 vai trò).
- [x] Knowledge base seed (≥10 chủ đề trải đều theory/harmony/songwriting/genres/lyrics/arrangement/production).
- [x] Frontend Next.js skeleton với Studio page và Suno launcher.
- [x] CI: lint backend (ruff) + lint frontend (eslint) + build frontend.

## M1 — RAG thực sự

- [ ] Chunk markdown theo heading.
- [ ] Embed (text-embedding-3-small hoặc local model).
- [ ] FAISS hoặc Chroma index, persistent under `backend/app/data/index/`.
- [ ] `/knowledge/search?q=...` trả top-K passages có score.
- [ ] Council mỗi turn tự retrieve dựa trên `expertise_tags`.

## M2 — Multi-agent debate

- [ ] Council orchestration: vòng phát biểu có thứ tự, A&R Critic phản biện cuối cùng.
- [ ] Refinement loop: user có thể yêu cầu hội đồng tranh luận lại 1 phần (chord, lyric, arrangement).
- [ ] Stream response (SSE) để UI hiển thị từng persona phát biểu.

## M3 — Studio canvas

- [ ] Chord chart editor (drag-drop ô nhịp, chỉnh hợp âm).
- [ ] Lyric sheet với phần verse/chorus/bridge tách rõ.
- [ ] Arrangement timeline (instruments × sections).
- [ ] "Yêu cầu hội đồng tinh chỉnh phần này" — gửi context có scope.

## M4 — Suno deep integration

- [ ] Build prompt Suno tối ưu từ draft (style ≤200 ký tự, lyrics đúng định dạng `[Verse]/[Chorus]`).
- [ ] One-click "Mở trong Suno": copy clipboard + open tab.
- [ ] (Optional) Playwright launcher: dùng profile đã đăng nhập của user để autofill.

## M5 — Library & versioning

- [ ] SQLite store cho drafts.
- [ ] Mỗi lần council edit → version mới, có diff.
- [ ] Library page: list tất cả bài, filter theo mood/genre.
- [ ] Export: JSON, PDF (chord chart + lyric).

## M6+ — Tương lai

- Voice input cho brief.
- Generative MIDI sketch để preview giai điệu trước khi đẩy sang Suno.
- Plugin để gửi thẳng sang DAW (Ableton, Logic, FL Studio).
- Hội đồng khu vực: Vpop council, K-pop council, EDM council với knowledge base chuyên biệt.
