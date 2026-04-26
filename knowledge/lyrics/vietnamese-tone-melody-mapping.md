---
title: "Vietnamese Tone–Melody Mapping — Worked Examples"
tags: ["lyrics", "prosody", "vietnamese", "vietnamese-tones", "melody", "worked-examples"]
level: "advanced"
---

# Tone–Melody Mapping cho Lyric tiếng Việt — Ví dụ thực tế

File `vietnamese-prosody.md` mô tả lý thuyết. File này cho **ví dụ pass/fail cụ thể** mà
Lyricist + Composer dùng để tự kiểm tra.

## 1. Quy chiếu thanh điệu vs hướng nốt

| Thanh | Đặc tính nốt | Phù hợp với hướng nốt |
|--|--|--|
| Ngang (a) | Phẳng, mid | Bất kỳ; tốt nhất là nốt giữ ngang |
| Huyền (à) | Đi xuống | Nốt thấp, hoặc descending interval |
| Sắc (á) | Đi lên | Nốt cao, hoặc ascending interval |
| Hỏi (ả) | Xuống rồi lên (V) | Nốt giữ hoặc nốt có ornament V-shape |
| Ngã (ã) | Bị gãy bật lên | Nốt cao có grace note bật lên |
| Nặng (ạ) | Bị nén ngắn | Nốt staccato ngắn, có thể bị cắt |

## 2. Worked example A — Hook 4 nốt G4–E4–G4–A4

Composer đã thiết kế hook melodic motif:

```
Note:    G4    E4    G4    A4
Move:    -     ↓3rd  ↑3rd  ↑M2
Length:  ¼    ¼     ¼     ½
```

### Câu lyric thử (4 âm tiết)

| Câu thử | Thanh điệu | Đánh giá |
|--|--|--|
| "anh yêu em mãi" | ngang–ngang–ngang–ngã | ✅ Smooth. "mãi" rơi vào A4 cao + ngã bật → đẹp. |
| "tôi nhớ em nhiều" | ngang–sắc–ngang–huyền | ⚠️ "nhiều" (huyền) ở A4 cao → âm méo, sẽ nghe như "nhiêu". |
| "đêm vẫn còn dài" | ngang–ngã–huyền–huyền | ⚠️ Hai huyền cuối ở A4 → "còn dài" méo thành "còn dai". |
| "yêu lắm bóng hình" | ngang–sắc–sắc–huyền | ❌ "hình" (huyền) ở A4 → méo. Đổi thành "yêu lắm dáng em" (ngang). |
| "em vẫn ở đây" | ngang–ngã–hỏi–ngang | ⚠️ "ở" (hỏi) ở G4↑A4 — nốt phẳng không có V-shape, nghe gượng. |

### Sửa câu thất bại

**Câu sai**: "tôi nhớ em nhiều" → A4 + huyền méo.
**Sửa**: "tôi nhớ em — yêu" hoặc "tôi nhớ riêng em" (đổi cuối thành thanh ngang/sắc).

Hoặc đổi melody: thay nốt cuối A4 thành E4 (xuống) thì "nhiều" (huyền) đẹp.

## 3. Worked example B — Hook 6 nốt với climbing motif

```
Note:    A4    B4    C5    D5    E5    D5
Move:    -     ↑M2   ↑m2   ↑M2   ↑M2   ↓M2
```

(Hook climb đến E5 = peak, rơi 1 nốt cuối)

### Câu lyric thử (6 âm tiết)

| Câu | Thanh | Đánh giá |
|--|--|--|
| "em là điều anh muốn" | ngang–huyền–huyền–ngang–ngang–sắc | ❌ "là điều" (huyền-huyền) ở B4-C5 climbing → conflict mạnh. |
| "anh yêu em mỗi đêm" | ngang–ngang–ngang–ngã–ngã–ngang | ✅ "mỗi đêm" có ngã climbing đẹp; ngang cuối D5 OK. |
| "em hãy ở lại đi" | ngang–ngã–hỏi–nặng–ngang–ngang | ⚠️ "ở" (hỏi) leo lên C5 + "lại" (nặng) ở D5 — nặng không bật được trên D5 dài. |
| "chờ em mãi mãi yêu" | huyền–ngang–ngã–ngã–ngang–ngang | ✅ Mở bằng huyền ở A4 thấp đẹp. "mãi mãi" climb với ngã hoàn hảo. |

### Quy tắc rút ra

1. **Đỉnh hook (E5) NÊN là thanh ngang, sắc, hoặc ngã**.
2. **Câu mở đầu thấp NÊN khởi với huyền hoặc ngang** (cảm giác "neo").
3. **Climbing intervals tốt nhất với sắc và ngã** ở đoạn lên.
4. **Tránh "huyền tại nốt cao"** — đây là lỗi méo phổ biến nhất.

## 4. Worked example C — Câu chorus dài 8 âm tiết, 2 phrase

Composer đặt 2 phrase 4-note motif (A4-G4-E4-D4) lặp 2 lần:

```
Phrase 1:  A4   G4   E4   D4   |   A4   G4   E4   D4
Note dir:  -    ↓    ↓    ↓    |    -    ↓    ↓    ↓
```

**Câu thử**: "tháng năm cũ qua mau / em ơi nhớ trong tim"

| Phrase | Câu | Thanh | Đánh giá |
|--|--|--|--|
| 1 | "tháng năm cũ qua mau" | sắc–ngang–ngã–ngang–ngang | ⚠️ "tháng" (sắc) ở A4 cao OK; nhưng "cũ" (ngã) ở E4 thấp → ngã bật lên không đủ space, méo. |
| 2 | "em ơi nhớ trong tim" | ngang–ngang–sắc–ngang–ngang | ✅ Smooth descending. "nhớ" (sắc) ở E4 hơi thấp nhưng chấp nhận được. |

**Sửa phrase 1**: "tháng năm trôi mau" (4 âm thay vì 5; bỏ "cũ" có ngã không hợp E4).

## 5. Worked example D — Bridge có falsetto bridge với note cao F#5

Composer thiết kế bridge climax với F#5 dài 1 nhịp.

```
Note:   B4   D5   F#5  E5   D5
                  (long, falsetto)
```

### Câu lyric thử (5 âm tiết)

| Câu | Thanh | Đánh giá |
|--|--|--|
| "em chờ ngày bên nhau" | ngang–huyền–huyền–ngang–ngang | ⚠️ "ngày" (huyền) ở F#5 → méo cực mạnh, falsetto huyền không bay được. |
| "anh tin sẽ tìm em" | ngang–ngang–ngã–huyền–ngang | ⚠️ "tìm" (huyền) ở F#5 → vẫn méo. |
| "em vẫn ở bên anh" | ngang–ngã–hỏi–ngang–ngang | ⚠️ "ở" (hỏi) ở F#5 → hỏi cần V-shape, falsetto thẳng không có V → méo nhẹ. |
| "anh không bao giờ quên" | ngang–ngang–ngang–huyền–ngang | ⚠️ "giờ" ở F#5 huyền → vẫn méo. |
| "ta sẽ không xa nhau" | ngang–ngã–ngang–ngang–ngang | ✅ "không" (ngang) ở F#5 đẹp, falsetto ngân được. |
| "em luôn là tia nắng" | ngang–ngang–huyền–ngang–sắc | ⚠️ "là" (huyền) ở F#5 méo. |
| "yêu mãi đời này thôi" | ngang–ngã–huyền–sắc–ngang | ⚠️ "đời" (huyền) ở F#5 méo. |

**Quy tắc rút ra**: âm tiết đặt vào **nốt cao falsetto** PHẢI là **thanh ngang hoặc sắc**. Tránh huyền/nặng/hỏi/ngã ở falsetto note.

**Sửa**: chọn câu kết bridge có thanh ngang ở vị trí F#5: "ta sẽ không xa nhau", "anh sẽ luôn yêu em" (yêu = ngang ở F#5).

## 6. Quy trình verify dành cho Lyricist

Sau khi viết 1 phrase, Lyricist tự check:

1. **Xác định nốt cao nhất** trong phrase (peak note).
2. **Chiếu âm tiết rơi vào peak note** — thanh điệu phải là **ngang, sắc, hoặc ngã**.
3. **Câu mở đầu phrase**: nốt thường thấp → âm tiết nên là **huyền hoặc ngang**.
4. **Đếm số âm tiết = số nốt**. Không thừa, không thiếu.
5. **Đọc to** với melody, kiểm có "vướng" chỗ nào không.
6. **Cluster 2 thanh giống nhau liên tiếp** — OK với ngang/sắc; **TRÁNH** 2 huyền liên tiếp ở đoạn climb.

## 7. Tham chiếu — câu lyric thực tế của V-pop hit

### Hà Anh Tuấn — "Tháng Tư Là Lời Nói Dối Của Em"

```
"Em đi để lại bao nhớ thương / Cho riêng anh"
Note dir (chorus, simplified):  E4 G4 G4 G4 A4 G4 F4 E4 / D4 C4 C4
Tones:                       ngang sắc nặng huyền ngang sắc ngang ngang / ngang ngang ngang
```

- "đi" (ngang) → G4 mid, OK.
- "để" (nặng) → G4 — chấp nhận được vì nốt giữ ngắn 1/4.
- "thương" (ngang) → E4 — đẹp.
- Phân tích cho thấy hook chủ yếu thanh ngang/sắc — tránh huyền ở peak.

### Vũ. — "Bước Qua Nhau"

```
"Bước qua nhau / Tựa khoảnh khắc thoáng qua trong đêm dài"
Tones (verse):  sắc–ngang–ngang / nặng–ngã–sắc–sắc–ngang–ngang–ngang–ngang–huyền
```

- Phrase mở: "Bước qua nhau" — sắc-ngang-ngang, ascending motif đẹp.
- Câu dài kết thúc với "đêm dài" (ngang-huyền) ở 2 nốt thấp giảm dần — huyền ở nốt thấp đẹp.

## 8. Quy tắc nóng (1 câu)

> **Đỉnh peak phải là ngang/sắc/ngã. Đáy thấp phải là huyền/ngang. Hỏi cần ornament. Ngã cần space cao. Nặng phải ngắn.**
