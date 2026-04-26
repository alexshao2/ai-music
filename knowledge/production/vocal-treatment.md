---
title: "Vocal Treatment — chain xử lý vocal cho ballad/pop"
tags: ["production", "mixing", "vocal", "compression", "reverb", "delay", "deesser"]
level: "intermediate"
---

# Vocal Treatment — Chain xử lý vocal world-class

Vocal là 60–70% chú ý của người nghe pop/ballad. Mọi lớp khác phải nhường,
và vocal phải được xử lý đến mức "ngồi đúng pocket" — không to quá, không
nhỏ quá, không hiện diện quá ở midrange.

## 1. Tracking (thu)

- **Mic**: condenser large diaphragm (Neumann U87, AKG C414, Aston Spirit). Khoảng cách 15–20 cm.
- **Pop filter**: bắt buộc, cách mic 5 cm.
- **Phòng**: hấp thụ sau singer (foam, blanket). Tránh reflection từ mặt kính hoặc bàn.
- **Take 4–6 lần** rồi comp (chọn lấy phần hay nhất từng line).

## 2. Cleanup (trước khi mix)

1. **De-noise** nếu phòng noisy (RX iZotope hoặc gating nhẹ).
2. **De-breath** — giảm noise breath xuống −18 đến −24 dB, không xoá hết (mất hồn).
3. **Sibilance check** — note các "s/x/ch/sh" sắc.
4. **Pitch correction** — Melodyne hoặc Auto-Tune ở Retune Speed 20–30 (graceful, không robotic).
5. **Comp + crossfade** — không để click giữa các take.

## 3. Mix chain mẫu (signal flow)

```
Vocal raw
  → Subtractive EQ (low-cut 80–100 Hz, notch 250 Hz nếu boomy, notch 4-7 kHz nếu harsh)
  → Compressor 1 (LA-2A style, slow attack, 3-5 dB GR — để giữ dynamics)
  → De-esser (target 6-9 kHz, threshold sao cho 3-4 dB GR ở "s")
  → Compressor 2 (1176 style, fast attack, 2-3 dB GR — rắn pocket)
  → Additive EQ (presence +1.5 dB @ 3 kHz, air shelf +1 dB @ 12 kHz)
  → Saturation light (tape style, 1-2% drive)
  → Send 1: Reverb (plate 1.2s pre-delay 30ms, low-cut 200 Hz, hi-cut 8 kHz, 12-15% wet)
  → Send 2: Delay 1/4 12% wet on hooks only (automation)
  → Output bus
```

## 4. Reverb chọn theo mood

| Mood | Reverb | Decay | Pre-delay |
|--|--|--|--|
| Intimate ballad | Plate ngắn | 1.0–1.4 s | 25–35 ms |
| Cinematic ballad | Hall vừa | 1.8–2.5 s | 40–60 ms |
| Lofi / dreamy | Vintage spring | 2.0 s | 50 ms |
| Pop modern | Plate + chamber blend | 1.5 s | 30 ms |

**Quy tắc vàng**: tất cả vocal layers (lead, BG, harmony) chia sẻ 1 reverb send chung
để "cùng phòng". Đừng để mỗi lớp dùng reverb riêng.

## 5. Delay tactics

- **Slap delay** (80–120 ms, 0 feedback) — cho intimate verse.
- **1/4 delay** với feedback 25%, low-cut 400 Hz — cho hook chorus.
- **1/8 dotted** — hiện đại, "The Edge" / pop polish.
- **Ping-pong** — chỉ ad-libs cuối bài; tránh trên main vocal (gây mệt).
- **Throw delay** — automation 1 chỗ duy nhất ở hook quan trọng nhất, để 50% wet 1 beat rồi tắt.

## 6. BG vocal stacking pattern

V-pop ballad chorus điển hình:

| Layer | Pitch relative to lead |
|--|--|
| Lead vocal | unison |
| BG layer 1 | unison double (panned 30 L) |
| BG layer 2 | unison double (panned 30 R) |
| Harmony 1 | 3rd above (perfect 3rd hoặc minor 3rd theo chord) |
| Harmony 2 | 5th above hoặc octave up (chỉ ở final chorus) |
| Bass voice | octave below (chỉ on key word) |

Volume rules: lead 0 dB, doubles −10 đến −12 dB, harmonies −12 đến −15 dB,
octaves chỉ +0 dB on hits.

## 7. Auto-tune ethics

- **Luôn tune** — ngay cả singer giỏi cũng có drift ±10 cents.
- **Retune speed cao** (T-Pain effect) chỉ khi production yêu cầu (trap, hyperpop).
- **V-pop ballad chuẩn**: retune speed 20–25, không hard-quantize. Để cảm xúc thở.
- **Vibrato**: bảo vệ vibrato của singer — không tune vibrato trừ khi out-of-key.

## 8. Sibilance management

- De-esser dùng **dynamic EQ** band 6–9 kHz hoặc 7–10 kHz (tuỳ singer).
- Nếu de-esser quá tay → vocal "câm" mất sibilance — sai. Để 70% of "s" attack vẫn nghe được.

## 9. Bus processing (vocal bus)

```
All vocal sends → Vocal Bus
  → Glue compressor 0.5–1 dB GR
  → EQ subtle (pump 12 kHz +1 dB, dip 400 Hz nếu mâu thuẫn với piano)
  → Saturation parallel 20% wet (Tape / Tube)
  → Output to master
```

## 10. Tham chiếu kỹ thuật

- **Touliver** (V-pop): vocal forward, plate reverb sạch, delay 1/4 trên hook.
- **DTAP**: vocal stack dày, K-pop influence; chorus có 4-5 layer harmony.
- **Khắc Hưng**: vocal mid-forward, ít reverb, presence cao 3-4 kHz.
- **Jack Antonoff**: dry verse + reverb wash chuyển vào chorus.
- **Finneas O'Connell** (Billie Eilish): close-mic intimate, tape saturation, không reverb.

## 11. Common mistakes

- Reverb quá nhiều → vocal "lùi" sau mix; mất intimacy.
- De-ess quá → vocal lispy.
- Compress quá → vocal "phẳng", thiếu dynamics, mệt nghe.
- Doubles quá nhiều ở verse → mất intimacy; dành doubles cho chorus.
- BG vocal pan center → đánh lẫn lead; nên pan ±20 đến ±60.
