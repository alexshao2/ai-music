---
title: "Lỗi phổ biến trong nhạc AI-gen"
tags: ["evaluation", "quality", "defects", "critic", "suno"]
level: "intermediate"
---

# Lỗi phổ biến trong nhạc AI-gen

Danh sách các lỗi thường gặp khi AI tạo nhạc. Critic và A&R evaluator dùng list này để phát hiện bài hát kém chất lượng.

## 1. Lỗi Melody & Hook

- **Hook generic / không nhận diện**: melody flat, không có contour rõ, nghe xong không nhớ gì
- **Peak note sai section**: note cao nhất ở verse_1 thay vì chorus — phá dynamic arc
- **Melody monotone**: range < 5 semitones, thiếu leap và step motion kết hợp
- **Hook recipe không rõ**: không thuộc 1 trong 8 hook construction recipes (repeat-and-vary, call-response, etc)
- **Rhythm hook missing**: chỉ có melodic hook, thiếu rhythmic pattern memorable

## 2. Lỗi Lyrics

- **Cliché overload**: "trái tim tan vỡ", "mưa rơi buồn", "đêm dài cô đơn" — xem cliche-bank-vn.md
- **Imagery generic**: "nỗi đau", "tình yêu" — thiếu chi tiết cụ thể (địa danh, mùi vị, texture)
- **Placeholder lyrics**: câu đầy đủ ngữ pháp nhưng vô nghĩa, không kể câu chuyện
- **Prosody mismatch**: thanh huyền/nặng ở peak note (méo melody trong tiếng Việt)
- **Rhyme gượng**: vần chỉ vì vần, câu bị twist ý nghĩa để vần cho khớp
- **No narrative arc**: verse_1 và verse_2 nói cùng một ý, không có progression

## 3. Lỗi Harmony

- **4-chord syndrome**: I–V–vi–IV lặp toàn bài, mọi section giống nhau
- **No tonal surprise**: bridge dùng cùng chord với verse, thiếu tension
- **Chord notation sai**: dùng roman numeral thay vì chord name cụ thể (Em, không "vi")
- **Key mismatch với mood**: minor key cho bài vui, major key cho bài buồn
- **Voice leading xấu**: parallel fifths, bass nhảy quãng lớn liên tục

## 4. Lỗi Structure

- **Energy flat**: mọi section cùng energy level (5-5-5-5), không có climax
- **Missing strip-down**: không có section nào energy ≤ 4 (bridge strip-down quan trọng)
- **Duration math sai**: bar_count × 240 / tempo ≠ duration_sec (sai ≥ 15%)
- **Final chorus = chorus_1**: copy-paste exact, không modulate / thêm layer / counter-melody
- **No intro/outro**: bài bắt đầu đột ngột, kết thúc cụt

## 5. Lỗi Production / Suno Tags

- **Style string > 200 chars**: Suno cắt bớt → mất thông tin quan trọng
- **Style string < 40 chars**: quá ít → Suno đoán bừa
- **Thiếu tempo/key trong style**: Suno render tempo/key ngẫu nhiên
- **References sai language**: ref V-pop artists cho bài English, hoặc ngược lại
- **FX thiếu values**: "reverb" thay vì "plate reverb 1.4s pre-delay 20ms"
- **Conflicting tags**: "calm peaceful" + "aggressive hard-hitting" cùng lúc
- **Instrument generic**: "piano" thay vì "upright piano felt-damped" hoặc "grand piano bright"

## 6. Lỗi Genre Authenticity

- **Instrument sai genre**: guitar điện distortion trong bolero, đàn tranh trong EDM
- **Tempo ngoài range**: ballade ở 140 BPM, trap ở 70 BPM
- **Drum pattern sai**: straight beat cho reggae (phải one-drop), 4-on-floor cho ballad
- **Vocal style mismatch**: autotune cho bolero, vibrato opera cho trap
- **Thiếu instrument đặc trưng**: reggae không có skank guitar, cải lương không có guitar phím lõm

## 7. Lỗi Suno-specific

- **Lyrics không có section tags**: `[Verse]`, `[Chorus]` — Suno không biết structure
- **Performance markers thiếu**: `(whisper)`, `(belt)`, `(raspy)` giúp Suno interpret tốt hơn
- **Negative tags thiếu**: không exclude styles conflicting → Suno trộn genres
- **Title quá dài / generic**: ảnh hưởng Suno metadata

## Checklist nhanh cho Critic

```
[ ] Hook có catchy không? Hát lại được sau 1 lần nghe?
[ ] Lyrics có cliché từ cliche-bank-vn.md không?
[ ] Imagery cụ thể hay generic?
[ ] Chord progression khác nhau giữa sections?
[ ] Dynamic arc có climax + strip-down?
[ ] Final chorus distinct?
[ ] Style string 60-200 chars, có tempo + key?
[ ] References đúng language/genre?
[ ] Instruments có qualifier cụ thể?
[ ] Tempo trong range genre cookbook?
```
