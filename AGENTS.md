# AGENTS.md

Hướng dẫn cho AI agents (Devin, Copilot, Cursor, ...) làm việc trong repo này.

## Quy ước nhánh

- `main` là nhánh mặc định và là nguồn duy nhất.
- Mỗi task tạo một nhánh mới: `feat/<slug>`, `fix/<slug>`, `chore/<slug>`, `docs/<slug>`.
- Mở PR vào `main`. Sau khi merge, **xoá nhánh** (cả remote và local).
- Không bao giờ force-push `main`.

## Quy ước commit

- Conventional Commits: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`.
- Tin nhắn commit và PR có thể viết bằng tiếng Việt hoặc tiếng Anh.

## Cấu trúc dự án

- `backend/` — FastAPI service. Mỗi router là một domain (`council`, `knowledge`, `studio`, `suno`).
- `frontend/` — Next.js App Router. Components nhỏ, có type. Tránh state global khi không cần.
- `knowledge/` — markdown thuần, mỗi file là một chủ đề độc lập. Frontmatter YAML mô tả `title`, `tags`, `level`.
- `docs/` — tài liệu kiến trúc, không phải code.

## Code style

- Python: type hints bắt buộc, dùng `pydantic` cho schema, `ruff` cho lint, `pytest` cho test.
- TS/React: strict mode, không `any`, ưu tiên server components khi không cần interactivity.
- Markdown kiến thức: đơn vị nhỏ (1 chủ đề / 1 file), ví dụ cụ thể, dẫn nguồn khi có.

## Khi thêm kiến thức mới

1. Đặt vào thư mục con phù hợp dưới `knowledge/`.
2. Có frontmatter:
   ```yaml
   ---
   title: "Vòng hoà âm I–V–vi–IV"
   tags: ["harmony", "pop", "progression"]
   level: "beginner"
   ---
   ```
3. Index sẽ tự rebuild khi backend khởi động (M1 sẽ dùng embedding thực sự).

## Khi thêm persona mới vào hội đồng

Sửa `backend/app/services/council.py` — thêm vào `COUNCIL_PERSONAS`. Mỗi persona cần `name`, `role`, `system_prompt`, `expertise_tags`.

## Bí mật

- Không bao giờ commit `.env`. Dùng `.env.example` làm template.
- LLM key được đọc từ env: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`.
