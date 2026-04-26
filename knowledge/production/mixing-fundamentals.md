---
title: "Mixing — fundamentals"
tags: ["production", "mixing", "eq", "compression"]
level: "intermediate"
---

# Mixing — fundamentals

## Thứ tự xử lý điển hình trên một channel

1. **Cleanup**: high-pass filter để loại bỏ rumble dưới 80 Hz (trừ kick & bass).
2. **Subtractive EQ**: cắt notch ở vùng "mud" (200–500 Hz) hoặc "harsh" (2–4 kHz).
3. **Compression**: thuần hoá độ động.
4. **Additive EQ / saturation / character**: thêm "mỡ", "không khí".
5. **Effects send**: reverb, delay, modulation.
6. **Volume automation**: cuối cùng, trước master bus.

## Gain staging

Mỗi channel nên peak khoảng **-12 to -6 dBFS** sau cleanup. Master bus chỉ nên có headroom **-6 dB** trước khi vào limiter cuối.

## Phân chia frequency cho 5 elements chính

| Element        | Vai trò       | Khu trú dải tần               |
|----------------|---------------|--------------------------------|
| Kick           | Foundation    | Low (60–100 Hz) + click (3–5k) |
| Bass           | Foundation    | Low (80–200 Hz)               |
| Snare          | Drive         | Body (200 Hz) + crack (3–5 kHz) |
| Vocal          | Focus          | Mid (500 Hz–4 kHz)             |
| Lead element   | Hook          | Mid + air                      |

Pad/strings/synth phụ → cắt vùng vocal, đẩy ra hai bên (pan).

## Sidechain

- **Pump cổ điển**: kick → bass, sub → kick. Cần thiết ở EDM/dance.
- **Vocal ducking**: synth phụ giảm khi vocal hát → mid vocal được bảo toàn.

## Stereo & space

- Mọi thứ dưới 120 Hz nên **mono** (kick, sub, bass).
- Vocal lead **center** + reverb có thể stereo.
- Pan instruments theo nguyên tắc "đứng chỗ trên sân khấu".
- Reverb tail dài ở vocal nhưng cắt LF reverb (dưới 200 Hz) để không đục.

## Reference track

Luôn so sánh với 1 reference track cùng thể loại. Match:

1. Tonal balance (low/mid/high).
2. Loudness perceived.
3. Dynamic range.
4. Stereo width.

Plugin gợi ý: TonalBalance, SPAN, Insight.

## Master bus

- Bus compression nhẹ (1–2 dB GR), ratio 2:1, slow attack.
- EQ broad chỉ ±1.5 dB.
- Limiter cuối: target LUFS theo platform (Spotify -14, Apple -16, YouTube -14).
- Đừng đẩy quá: -7 LUFS đã rất to. Trên đó méo và nén nhạc.
