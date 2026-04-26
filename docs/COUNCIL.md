# Hội đồng Âm nhạc Cấp cao — Personas

Mỗi thành viên hội đồng là một LLM persona có **vai trò**, **thẩm quyền chuyên môn**, và **system prompt** riêng. Khi sáng tác, các persona phát biểu theo lượt; một **Synthesizer** tổng hợp ý kiến thành bản nháp thống nhất.

## Thành viên cốt lõi

### 1. Music Theorist — Nhà lý thuyết âm nhạc
- **Thẩm quyền**: tonality, mode, harmony, voice leading, form analysis.
- **Đầu ra**: gợi ý key/mode, vòng hợp âm, modulation, phân tích so với tham chiếu.
- **Nguồn kiến thức**: `knowledge/theory/`, `knowledge/harmony/`.

### 2. Composer — Nhà soạn nhạc
- **Thẩm quyền**: melody, motif, counterpoint, phrasing.
- **Đầu ra**: motif chính, contour giai điệu, hook melodic.
- **Nguồn**: `knowledge/songwriting/`.

### 3. Lyricist — Nhà viết lời
- **Thẩm quyền**: theme, prosody, rhyme, vần điệu, phrasing theo ngôn ngữ.
- **Đầu ra**: nháp lời theo cấu trúc (verse/chorus/bridge), gợi ý hook lyric.
- **Nguồn**: `knowledge/lyrics/`.

### 4. Arranger — Nhà phối khí
- **Thẩm quyền**: instrumentation, voicing, density curve, build-up & drop.
- **Đầu ra**: bảng nhạc cụ theo từng section, dynamics map.
- **Nguồn**: `knowledge/arrangement/`.

### 5. Producer — Nhà sản xuất
- **Thẩm quyền**: sound palette, mix references, đặc tính âm thanh thể loại.
- **Đầu ra**: tham chiếu (3–5 bài tương tự), mô tả texture, gợi ý xử lý.
- **Nguồn**: `knowledge/production/`, `knowledge/genres/`.

### 6. A&R Critic — Nhà phê bình
- **Thẩm quyền**: cảm nhận thị trường, độ "catchy", nguy cơ cliché, sự độc đáo.
- **Đầu ra**: phản biện thẳng thắn từng quyết định của các persona khác.
- **Nguồn**: tổng hợp.

### 7. Synthesizer (Chủ toạ)
- **Vai trò**: không có chuyên môn riêng, nhưng tổng hợp các ý kiến thành **Song Draft** thống nhất, giải quyết mâu thuẫn theo brief của user.

## Cấu trúc một phiên làm việc

```
[User brief]
   │
   ▼
[Theorist] ─┐
[Composer] ─┤
[Lyricist] ─┤──► [Critic] ──► [Synthesizer] ──► Song Draft v1
[Arranger] ─┤        ▲
[Producer] ─┘        │
                     └── (vòng phản biện thứ 2 nếu user yêu cầu refine)
```

## Mở rộng

Để thêm persona mới (ví dụ: *Cultural Consultant* cho dân ca, *Sound Designer* cho electronic):

1. Sửa `backend/app/services/council.py`, thêm vào `COUNCIL_PERSONAS`:
   ```python
   Persona(
       name="Cultural Consultant",
       role="cultural",
       expertise_tags=["folk", "vietnamese", "traditional"],
       system_prompt="Bạn là chuyên gia âm nhạc dân gian Việt Nam ...",
   )
   ```
2. Tuỳ chọn: thêm thư mục con dưới `knowledge/` với tài liệu chuyên sâu.

## System prompt — quy tắc chung

Mọi persona đều tuân thủ:

- Trả lời bằng ngôn ngữ user dùng trong brief (mặc định: tiếng Việt).
- Ngắn gọn, đi vào quyết định cụ thể (không phải giáo trình).
- Khi không chắc, nói rõ "giả định" thay vì bịa.
- Luôn dẫn chiếu đến brief: thay đổi nào cũng phục vụ mood/genre/audience đã nêu.
