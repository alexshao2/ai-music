# Suno bridge — chi tiết

Tài liệu này mô tả cách `ai-music` đẩy bản nháp sang [Suno AI](https://suno.com) để tạo audio hoàn chỉnh.

## Manual paste workflow

Suno không có API public cho user free tier và có captcha kháng automation, nên ai-music chỉ hỗ trợ luong manual paste:

1. Backend build `title` + `style` (≤200 ký tự) + `lyrics` (định dạng `[Verse]/[Chorus]/...`) từ `SongDraft`.
2. Frontend `SunoLauncher` gọi `GET /suno/launch/{draft_id}` và hiển thị 3 ô copy rời (Title / Style / Lyrics) + 1 nút "Copy tất cả".
3. User bấm ô cần copy, sang tab Suno Custom mode đã mở, paste vào ô tương ứng, bấm Create.

Autofill Playwright đã bị gỡ ở PR feat/m1.5: Suno hiển thị captcha hình ảnh ngay sau Create nên script không thể hoàn thành được, manual là con đường tin cậy.

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
- [ ] M5: lưu Suno track URL ngược về draft (user paste lại).
- [ ] M6: download audio và đính kèm vào library.
