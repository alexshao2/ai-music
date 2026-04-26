# Suno bridge — chi tiết

Tài liệu này mô tả cách `ai-music` đẩy bản nháp sang [Suno AI](https://suno.com) để tạo audio hoàn chỉnh.

## Hai chế độ

### 1. Quick mode (default — không cần API key)

Suno **chưa có API public cho user free tier**. Nên ở M0–M3 dùng *launcher pattern*:

1. Backend build `style` (≤200 ký tự) + `lyrics` định dạng `[Verse]/[Chorus]/...` từ `SongDraft`.
2. Frontend (`SunoLauncher`) gọi `GET /suno/launch/{draft_id}`, copy nội dung vào clipboard, mở `https://suno.com/create` ở tab mới.
3. User paste vào ô **Custom Mode** của Suno và nhấn Create.

Đây là pattern an toàn, không bị coi là tự động hoá Suno.

### 2. Studio Pro (M4 — Playwright launcher, optional)

Khi user đã đăng nhập Suno trên Chrome của Devin, có thể script Playwright qua CDP `http://localhost:29229` để autofill Custom Mode form. Profile state persist nên không cần đăng nhập lại mỗi lần.

Khi triển khai:

```python
from playwright.async_api import async_playwright

async with async_playwright() as p:
    browser = await p.chromium.connect_over_cdp("http://localhost:29229")
    page = await browser.contexts[0].new_page()
    await page.goto("https://suno.com/create")
    # ... fill style + lyrics + click Create
```

**Lưu ý**: kiểm tra ToS của Suno trước khi triển khai trong production.

## Quy tắc xây prompt tốt cho Suno

### Style (≤200 ký tự)

Suno cắt cụt nếu vượt 200. Format khuyến nghị:

```
<genre>, <subgenre>, <tempo BPM>, <key/mood>, <instruments chính>, <vocal characteristic>, <production palette>
```

Ví dụ:
```
V-pop ballad, slow 78 BPM, A minor, fingerpicked acoustic guitar, intimate breathy female vocal, plate verb, warm tape saturation
```

### Lyrics

Suno hiểu các tag section đặt trong `[]`:

- `[Verse]`, `[Verse 2]`
- `[Pre-Chorus]`
- `[Chorus]`
- `[Bridge]`
- `[Outro]`
- `[Instrumental]` — Suno sẽ chỉ chơi nhạc, không hát
- `[Hook]`

Mỗi section nên có ≤8 dòng. Quá dài Suno sẽ tự cắt hoặc bỏ qua.

### Mẹo nâng cao

1. **Vocal direction**: ghi `(soft, breathy)` hoặc `(belted, powerful)` ở đầu câu để định hướng.
2. **Ad-lib**: dùng dấu ngoặc `(oh, oh)` cho ad-lib BG.
3. **Code-switching**: Suno hỗ trợ tiếng Việt nhưng phát âm tốt hơn nếu có 1–2 từ tiếng Anh ở chorus.
4. **Tránh số quá dài**: `2024` đôi khi đọc thành "two thousand twenty-four", giải pháp: ghi `twenty twenty-four`.

## Endpoint

| Method | Path                     | Mô tả                                       |
|--------|--------------------------|----------------------------------------------|
| GET    | `/suno/prompt/{draft_id}`| Build và lưu prompt vào draft.              |
| GET    | `/suno/launch/{draft_id}`| Trả URL + payload cho frontend launcher.    |

## Roadmap

- [x] M0: launcher pattern + clipboard.
- [ ] M4: Playwright autofill khi user opt-in.
- [ ] M5: lưu Suno track URL ngược về draft (user paste lại).
- [ ] M6: download audio và đính kèm vào library.
