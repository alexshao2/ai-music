# AI Music — Hội đồng Âm nhạc Cấp cao

> Một studio sáng tác nhạc được dẫn dắt bởi **hội đồng AI cấp cao**, dựa trên kho tàng kiến thức âm nhạc đồ sộ, tích hợp **SunoAI** để biến ý tưởng thành bài hát hoàn chỉnh.

## Tầm nhìn

`ai-music` không chỉ là một wrapper LLM — nó là một **hội đồng các nhạc sĩ ảo** (Composer, Lyricist, Arranger, Producer, Music Theorist, A&R Critic) cùng nhau tranh luận, đề xuất và tinh chỉnh tác phẩm dựa trên:

1. **Kho kiến thức âm nhạc có cấu trúc** — lý thuyết hoà âm, phối khí, viết lời, lịch sử thể loại, kỹ thuật sản xuất.
2. **Prompt engineering chuyên biệt cho từng vai trò** trong hội đồng.
3. **Studio sáng tác** — không gian tương tác để duyệt qua từng quyết định: hợp âm, giai điệu, cấu trúc, lời, hoà phối.
4. **Suno bridge** — một cú click để xuất prompt cuối cùng sang [Suno AI](https://suno.com) và tạo ra audio hoàn chỉnh.

## Kiến trúc

```
ai-music/
├── backend/        # FastAPI — council orchestration, RAG, Suno bridge
│   └── app/
│       ├── routers/    # /council, /knowledge, /studio, /suno
│       ├── services/   # LLM, retrieval, council debate engine
│       └── data/       # song drafts, sessions
├── frontend/       # Next.js + Tailwind — Studio UI
│   └── src/
│       ├── app/        # routes (studio, library, council)
│       ├── components/ # ChatPanel, ScoreBoard, SunoLauncher
│       └── lib/        # API client
├── knowledge/      # Music knowledge base (markdown, được index thành RAG)
│   ├── theory/         # Lý thuyết âm nhạc
│   ├── harmony/        # Hoà âm, vòng hợp âm
│   ├── songwriting/    # Cấu trúc bài hát, motif
│   ├── genres/         # Đặc trưng từng thể loại
│   ├── arrangement/    # Phối khí, instrumentation
│   ├── lyrics/         # Kỹ thuật viết lời
│   └── production/     # Mixing, mastering, sound design
└── docs/           # Architecture, roadmap, council personas
```

Xem [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) và [`docs/COUNCIL.md`](docs/COUNCIL.md) để biết chi tiết.

## Bắt đầu

### Yêu cầu

- Python 3.11+
- Node.js 20+
- Một LLM API key (OpenAI, Anthropic, hoặc tương thích OpenAI)

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env   # điền OPENAI_API_KEY
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Studio UI: http://localhost:3000

### Self-host (Docker Compose + Cloudflare Tunnel)

Chạy toàn bộ stack trên server của bạn và public ra Internet bằng Cloudflare
Tunnel ở chế độ token, không cần mở port:

```bash
cp .env.example .env
# điền TUNNEL_TOKEN, PUBLIC_API_BASE, LLM_API_KEY, ...
docker compose up -d --build
```

Hướng dẫn đầy đủ (tạo tunnel, map hostname, troubleshooting): [`docs/SELF_HOSTING.md`](docs/SELF_HOSTING.md).

### Suno Bridge

Khi đã hài lòng với prompt do hội đồng tinh chỉnh, click **"Mở trong Suno"** ở Studio. Một tab mới sẽ mở [suno.com/create](https://suno.com/create) với prompt đã được copy vào clipboard, sẵn sàng paste.

## Workflow phát triển

- `main` là nhánh mặc định và là nguồn duy nhất.
- Mỗi feature được phát triển trên nhánh `feat/*` hoặc `fix/*`, mở PR vào `main`.
- Sau khi merge, **nhánh được xoá**.
- Không force-push `main`.

## Roadmap (tóm tắt)

- [x] M0 — Skeleton: monorepo, council stubs, knowledge seed, Suno launcher.
- [ ] M1 — RAG thực sự: embed knowledge base, retrieval-augmented council.
- [ ] M2 — Multi-agent debate: tranh luận có cấu trúc giữa các persona.
- [ ] M3 — Studio canvas: chỉnh sửa từng thành phần (chord chart, lyric sheet, arrangement).
- [ ] M4 — Suno deep integration: scripted launch với prompt prefill.
- [ ] M5 — Library & versioning: lưu bản nháp, so sánh phiên bản.

Xem [`docs/ROADMAP.md`](docs/ROADMAP.md) cho chi tiết.

## Giấy phép

MIT.
