# Contributing

Cảm ơn bạn đã muốn đóng góp cho `ai-music`. Quy ước workflow:

## Branch

- `main` là default branch và là nguồn duy nhất.
- Mọi thay đổi đi qua PR. **Không** push trực tiếp `main`.
- Đặt tên: `feat/<slug>`, `fix/<slug>`, `chore/<slug>`, `docs/<slug>`, `refactor/<slug>`.
- Sau khi PR được merge, **xoá nhánh** (cả remote và local).

## Local workflow

```bash
git checkout main && git pull
git checkout -b feat/your-feature
# ... làm việc ...
git push -u origin feat/your-feature
# Mở PR vào main trên GitHub
```

## Yêu cầu trước khi mở PR

### Backend

```bash
cd backend
ruff check .
pytest -q
```

Cả hai phải pass. Test mới đặt dưới `backend/tests/`.

### Frontend

```bash
cd frontend
npm run lint
npm run typecheck
npm run build
```

Cả ba phải pass.

### Knowledge

Nếu thêm tài liệu mới dưới `knowledge/`:

- Đặt vào thư mục con phù hợp (`theory`, `harmony`, `songwriting`, `lyrics`, `arrangement`, `genres`, `production`, `evaluation`).
- Có frontmatter YAML:
  ```yaml
  ---
  title: "Tên ngắn gọn"
  tags: ["tag1", "tag2"]
  level: "beginner | intermediate | advanced"
  ---
  ```
- Mỗi file 1 chủ đề, ≤2000 từ. Có ví dụ cụ thể.

## Commit message

Conventional Commits:

- `feat: thêm endpoint /studio/refine`
- `fix: vòng hợp âm minor không transpose đúng`
- `docs: bổ sung hướng dẫn Suno bridge`
- `chore: bump next.js to 14.2.35`
- `refactor: tách suno service ra khỏi router`
- `test: cover lyric formatting edge cases`

Tin nhắn có thể tiếng Việt hoặc tiếng Anh.

## PR template

Mọi PR cần có:

1. **Mục tiêu** — làm gì, vì sao.
2. **Thay đổi chính** — bullet list.
3. **Test** — đã test thế nào (CI pass + screenshot nếu UI).
4. **Rollback** — nếu cần revert thì làm gì.

## Code review

- Chấp nhận squash merge mặc định.
- Sau merge: xoá nhánh trên GitHub UI hoặc `git push origin --delete <branch>`.
