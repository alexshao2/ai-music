---
title: "Tiếng Nhật — Mora-melody mapping cho lyric J-pop / anime / city-pop"
tags: ["lyrics", "japanese", "prosody", "mora", "jpop", "anime"]
level: "advanced"
---

# Tiếng Nhật — Mora & melody mapping

Tiếng Nhật là **mora-timed language** (khác tiếng Việt syllable-timed, khác tiếng Anh stress-timed).
Mỗi mora chiếm thời lượng tương đương — đó là lý do J-pop có thể nhồi 1/16 note đầy đủ một cách
tự nhiên: 16 mora = 16 nốt 1/16 trong 1 bar 4/4.

## 1. Mora là gì

Mora ≠ syllable. Tiếng Nhật có 3 loại mora:

| Loại | Pattern | Ví dụ | Số mora |
|--|--|--|--|
| Vowel only | V | あ (a), い (i) | 1 |
| Consonant + Vowel | CV | か (ka), ね (ne), し (shi) | 1 |
| Long vowel "−" | C V V | おかあさん (o-ka-a-sa-n) | "kaa" = 2 mora |
| Geminate "っ" | CC | きっと (ki-t-to) | "tto" = 2 mora |
| Final "ん" | n | おかあさん | "n" cuối = 1 mora |

**Quan trọng**: âm tiết tiếng Việt thường ≠ mora Nhật. Ví dụ:
- "Tokyo" = 4 mora (to-u-kyo-u) chứ không phải 2 syllable
- "kakeru" = 3 mora (ka-ke-ru) = 3 syllable
- "ittai" = 4 mora (i-t-ta-i) chứ không phải 3

## 2. Mora-melody mapping nguyên tắc

**Quy tắc 1: 1 mora = 1 nốt** (gần như tuyệt đối trong J-pop modern)
- Verse fast 1/16: 16 mora / bar = đếm chính xác
- Chorus medium 1/8: 8 mora / bar
- Ballad 1/4: 4 mora / bar

**Quy tắc 2: long vowel + n cuối (ん) = sustain notes**
- "kaa" (long vowel) = 2 mora = thường 2 nốt cùng pitch hoặc 1 nốt sustain qua 2 mora
- "san" cuối = ん lấy 1 mora riêng (sustained)

**Quy tắc 3: geminate (っ) = "rest" hoặc "soft attack"**
- "kitto" = ki + (silent っ as 1 mora rest) + to
- Composer phải để 1 nốt rest hoặc 1 ghost note ở っ

## 3. Worked example: "Yoru ni kakeru" hook (YOASOBI)

```
夜 に 駆 け る
yo  ru  ni  ka  ke  ru
1   2   3   4   5   6  mora

Pitch: B4 B4 C#5 B4 E5 E5
Beat:  1   1.5 2   2.5 3 3.5 (in 4/4 at 130 BPM, fast 1/8 phrase)
```

✅ **Pass**: 6 mora distributed over 6 nốt (1:1). "ru" cuối is 1 mora = 1 nốt (no truncation).

❌ **BAD example** (hypothetical wrong):
```
夜 に 駆 け る
Pitch: B4 — C#5 B4 E5 (only 5 notes for 6 mora)
```
Lý do sai: thiếu 1 nốt cho "ru" → mora bị cụt.

## 4. Worked example: "Plastic Love" hook (Mariya)

Verse phrase: 突然 の キス や 熱烈 な 愛 の 言葉
```
to-tsu-ze-n no  ki-su  ya  ne-tsu-re-tsu  na  a-i  no  ko-to-ba
 1   2   3  4   5   6  7   8   9  10  11  12  13 14  15  16  17
```
Đếm: 17 mora. Phrase này thường được hát qua 2 bar 4/4 = 8 beat = 16 nốt 1/8 + 1 pickup.

Trong "Plastic Love", Mariya phrase này across 2 bar (105 BPM) với 1/8 note delivery. Chính
xác 17 mora = 16 nốt + 1 pickup = vừa.

✅ **Pass**: melodic phrase mapping mora đúng nhịp.

## 5. Long vowel & "ん" cuối — handle trong melody

```
お かあ さ ん   (okaasan, "mother")
o  ka-a  sa-n
1   2-3  4-5  mora
```

**Mapping option 1** (sustain):
- "ka" lands beat 1
- "a" sustained over beat 1.5–2 (cùng pitch hoặc glide)
- "sa" beat 2.5
- "n" sustained beat 3

**Mapping option 2** (separate notes):
- "ka" beat 1, "a" beat 1.5 (different pitch, melisma)
- "sa" beat 2, "n" beat 2.5 (different pitch)

Cả 2 đều OK; option 1 cho cảm giác "long emotion", option 2 cho cảm giác busy/busy.

## 6. Pitch accent (intonation) mapping

Tiếng Nhật có **pitch accent** (high/low pattern per word). Composer NÊN tôn trọng (không bắt buộc):

| Pattern | Word | Accent |
|--|--|--|
| Heiban (flat) | 桜 (sakura) | LHH (low-high-high) |
| Atamadaka (head-high) | 雨 (ame) | HL (high-low) "rain" |
| Nakadaka (mid-high) | 男 (otoko) | LHL |
| Odaka (tail-high) | 花 (hana) | LH (rising) |

**Rule of thumb**: nếu accent là HL (atamadaka), nốt đầu nên cao hơn nốt sau.
Nếu LH (odaka), nốt cuối nên cao hơn nốt đầu.

Composer J-pop modern thường KHÔNG strict về pitch accent — chấp nhận melody-driven nếu
melody đẹp. Nhưng Lyricist nên check ít nhất hook keyword.

## 7. English code-mix (đặc biệt city-pop / anime / J-pop modern)

J-pop thường chèn 1–2 từ tiếng Anh trong câu Nhật. Quy tắc:
- 1 mora tiếng Nhật ≈ 1 syllable tiếng Anh ngắn
- "love" = 1 syllable = 1 mora ánh xạ
- "plastic" = 2 syllables = 2 mora ánh xạ
- "starlight" = 2 syllables (star-light) = 2 mora

Worked example "Plastic Love" hook insertion:
```
I'm just play-ing  games  I  know that's  plas-tic  love
 1    1   2    3     1    1   1     1     2    3     1
```
13 syllables tiếng Anh ánh xạ ~13 mora rhythmic slot trong J-pop hook.

## 8. Hook construction — số mora khuyến nghị

| Genre | Hook mora count | Ví dụ |
|--|--|--|
| J-pop modern (YOASOBI, Yorushika) | 4–8 mora | "Yoru ni kakeru" (6), "Aidoru" (4) |
| Anime opening | 4–8 mora | "Gurenge" (4), "Zankyō sanka" (8) |
| City-pop | 6–10 mora (with English insert) | "Plastic love" (4 EN ≈ 4 mora) |
| Ballad emotional | 6–12 mora | "Hikari areba" (6) |

**Rule**: hook ≤8 mora, repeat 2–4× per chorus = anchor signature.

## 9. Verse câu length

| Genre | Verse câu mora |
|--|--|
| J-pop modern verse A | 12–18 mora |
| J-pop modern verse B | 8–14 mora |
| City-pop verse | 14–20 mora (slower groove, longer phrase) |
| Anime opening verse | 10–16 mora |
| Ballad emotional | 8–14 mora |

## 10. Cliché / overused phrase tránh

| Cliché | Lý do tránh | Thay thế |
|--|--|--|
| 君がいた / 君がいない (kimi ga ita / inai) | Quá phổ biến | 君のいない街 (kimi no inai machi) |
| 涙が溢れる (namida ga afureru) | Cliché 90s | 頬を伝う雨 (hoho wo tsutau ame) |
| 永遠に (eien ni) "forever" | Hyperbole sáo | この夜だけは (kono yoru dake wa, "just for tonight") |
| 約束した (yakusoku shita) | Drama K-/J- common | 指切り (yubikiri, "pinky promise") concrete |
| 心が痛い (kokoro ga itai) | Direct | 胸がきしむ (mune ga kishimu, "chest creaks") |

## 11. Imagery palette J-pop / city-pop

| Theme | Words |
|--|--|
| Đêm thành phố | 夜空 (yozora), ネオン (neon), 街灯 (gaitō), 高速道路 (kōsokudōro), 駅前 (ekimae) |
| Tình yêu | キス (kiss), 抱きしめる (dakishimeru), 君の手 (kimi no te), 指先 (yubisaki) |
| Mùa | 桜 (sakura), 夏 (natsu), 紅葉 (kōyō), 雪 (yuki), 梅雨 (tsuyu) |
| Phương tiện | 電車 (densha), タクシー (taxi), 自転車 (jitensha), 飛行機 (hikōki) |
| Đồ vật | 写真 (shashin), 手紙 (tegami), カセット (cassette), 傘 (kasa), 鏡 (kagami) |
| Cảm xúc | 切ない (setsunai), 寂しい (sabishii), 嬉しい (ureshii), 懐かしい (natsukashii) |

## 12. Self-check checklist cho Lyricist (J-pop)

1. ☐ Đã đếm mora cho từng câu phrase?
2. ☐ Hook ≤8 mora và lặp lại 2–4× chorus?
3. ☐ Long vowel (—) và ん cuối có sustained notes mapping?
4. ☐ Geminate (っ) có rest/ghost note?
5. ☐ Pitch accent của hook keyword có check (atamadaka/heiban/odaka)?
6. ☐ Tránh cliché "kimi ga ita / namida ga afureru"?
7. ☐ Có concrete imagery (sakura, densha, neon, kasa)?
8. ☐ English code-mix 1–2 từ ở chorus (nếu city-pop / anime modern)?
9. ☐ Verse 12–18 mora; chorus 8–14 mora?
10. ☐ Pronoun consistent (boku/watashi/kimi/anata)?
