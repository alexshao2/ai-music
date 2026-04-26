---
title: "Tiếng Hàn — Hangul syllable-block & melody mapping cho lyric K-pop"
tags: ["lyrics", "korean", "prosody", "hangul", "syllable", "kpop"]
level: "advanced"
---

# Tiếng Hàn — Hangul Syllable-Block Prosody

Tiếng Hàn là **syllable-timed language** với cấu trúc Hangul **syllable block** rất đặc biệt:
mỗi block là 1 âm tiết, mỗi block có cấu trúc đầu-giữa-cuối (initial consonant + medial vowel
+ optional final consonant). Khác tiếng Việt syllable-timed (mỗi âm tiết có thanh điệu),
Hangul không có thanh điệu — duration của mỗi âm tiết chủ yếu phụ thuộc vào **vowel weight**
(short vowel ㅏㅓ vs long vowel ㅏㅏ ㅓㅓ vs diphthong ㅘㅙ).

## 1. Hangul syllable structure

Mỗi Hangul block = 1 âm tiết. Cấu trúc:

```
초성 (cho-seong) = initial consonant (ㄱㄴㄷㄹㅁㅂㅅㅈㅊㅋㅌㅍㅎ + ㅇ silent)
중성 (jung-seong) = medial vowel (ㅏㅑㅓㅕㅗㅛㅜㅠㅡㅣ + diphthongs ㅐㅔㅙㅞ ㅘㅝ)
종성 (jong-seong) = final consonant (optional, called "받침" batchim)
```

Ví dụ:
- 사랑 (sa-rang, "love") = 2 syllable blocks. Block 1: ㅅ + ㅏ (no batchim). Block 2: ㄹ + ㅏ + ㅇ (batchim).
- 하늘 (ha-neul, "sky") = 2 syllable blocks. Block 1: ㅎ+ㅏ. Block 2: ㄴ+ㅡ+ㄹ.
- 봄날 (bom-nal, "spring day") = 2 syllable blocks. Block 1: ㅂ+ㅗ+ㅁ batchim. Block 2: ㄴ+ㅏ+ㄹ batchim.

**Quan trọng**: 1 Hangul block = 1 syllable = 1 musical note (gần như tuyệt đối).

## 2. Syllable-melody mapping

**Quy tắc 1: 1 Hangul block = 1 nốt** (như mora Nhật, syllable Anh)

```
사랑해요 = 4 nốt
sa-rang-hae-yo
1   2   3  4   nốt
```

**Quy tắc 2: vowel weight determines note duration**

| Vowel type | Weight | Note duration |
|--|--|--|
| Short vowel (ㅏㅓㅗㅜㅡㅣ) | Light | 1/8 hoặc 1/16 |
| Long vowel (ㅏ:, ㅓ:, ㅗ: marked with macron) | Heavy | 1/4 hoặc 1/2 sustain |
| Diphthong (ㅘㅝㅙㅞ) | Heavy | 1/4 hoặc sustain với glide |
| Batchim final (ㅁㄴㅇㄹ) | Sustained tail | Note sustained → consonant on cutoff |

**Quy tắc 3: batchim final consonant treatment**

Final ㅁㄴㅇㄹ (m, n, ng, l) at end of block — these consonants are **sustained**:
- 봄 (bom) = note sustained on "o" then cut with "m" closure
- 사랑 (sa-rang) = note 2 sustained on "a" then "ng" closure
- 하늘 (ha-neul) = note 2 sustained on "eu" then "l" closure

**Final stops** (ㄱㄷㅂㅅㅈㅊㅋㅌㅍ) — these are **clipped/glottal**:
- 곡 (gok) = note clipped, like staccato
- 잡 (jab) = note clipped

## 3. Worked example: "Spring Day" hook (BTS)

```
보고 싶다  (bogo sipda, "I miss you")
bo-go-sip-da
 1  2  3  4   nốt
```

Pitch contour (B♭ major key):
- 보 (bo) = F4 (1 nốt 1/4) — short vowel ㅗ
- 고 (go) = G4 (1 nốt 1/4) — short vowel ㅗ
- 싶 (sip) = B♭4 sustained (1 nốt 1/2) — short vowel ㅣ + batchim ㅂ stop (clipped on tail)
- 다 (da) = (no note, ㅣ glide ornament cuối)

**Pass**: 4 syllable blocks distributed over 4 notes (1:1) với batchim treated as clip on syllable 3.

## 4. Worked example: "Hype Boy" hook (NewJeans)

```
Hype boy = 2 syllables (English insertion)
```

NewJeans hook is bilingual. Korean vs English insertion:
- "Hype boy" Korean-pronounced = 2 syllables
- Pitch contour: B4 → C#5 (rise)
- Lặp 8× per chorus = NewJeans signature density

**Pass**: 2 syllables maps to 2 notes; varies 50/50 between B4-C#5 vs B4-B4 sustained.

## 5. K-pop English code-mix integration

K-pop chorus typically 30-70% English. Rules:

**Quy tắc 4: English syllable count = Korean syllable count for bilingual hooks**

| K-pop song | Korean phrase | English insert | Total syllables |
|--|--|--|--|
| Dynamite | (English-only chorus) | "Cause I I I'm in the stars tonight" | 8 syl |
| Boy with Luv | 어머나 어머나 (eomeona eomeona, "my my") | "boy with love" | 4+3 = 7 syl |
| Mic Drop | 신경꺼 (sin-gyeong-kkeo, "don't care") | "Mic Drop" | 3+2 = 5 syl |

**Pass**: bilingual line maps syllables 1:1 with notes regardless of language switching.

## 6. Pitch contour & K-pop melodic preference

Korean lyric **does NOT have tone**, so composer is FREE to set any pitch. But cultural preferences:

| Pattern | Common usage |
|--|--|
| Descending phrase | Verse, conversational; ending with sigh |
| Ascending climax | Chorus, hook, emotional peak |
| Plateau (sustained) | Long vowel ㅏ ㅗ; emphasizes meaning |
| Wide leap (octave+) | Belt vocal Taeyeon, IU; dramatic emotional |

**4th gen** (NewJeans, aespa) prefers narrow leaps (3rd, 4th max), narrow vocal range. 3rd gen
(BLACKPINK, BTS) prefers wide leaps (octave+), full belt G5+.

## 7. Hook construction — số syllable khuyến nghị

| Genre | Hook syllable count | Ví dụ |
|--|--|--|
| K-pop 3rd gen idol-pop | 3-6 syllable Korean + English mix | "DDU-DU DDU-DU" (4), "KILL THIS LOVE" (3) |
| K-pop 4th gen girl group | 2-5 syllable | "Hype boy" (2), "I AM" (2), "OMG" (3) |
| K-pop ballad | 4-8 syllable Korean | "보고 싶다" (4), "그날의 우리" (4 + breath) |
| K-R&B | 4-8 syllable Korean + slight English | "지금" (jigeum, "now") (2) |

**Rule**: hook ≤8 syllables (Korean tradition), repeat 4× per chorus minimum (3rd gen) or 8× (4th gen).

## 8. Verse câu length

| Genre | Verse câu syllables (Korean only) |
|--|--|
| K-pop idol-pop verse | 8–12 syllable |
| K-pop 4th gen verse | 6–10 syllable |
| K-pop ballad verse | 10–14 syllable |
| K-R&B verse | 8–14 syllable |

## 9. Rhyme scheme Korean

Korean rhyme thường dùng **vowel + final consonant** pattern. Most common:

| Pattern | Examples |
|--|--|
| -ㅓ ending | 했어 (haesseo) / 없어 (eopseo) / 봤어 (bwasseo) — past tense -ssseo |
| -ㅏㅁ ending (-am) | 사람 (saram) / 마음 (maeum) / 처음 (cheoeum) |
| -ㅡㄹ ending (-eul) | 하늘 (haneul) / 날 (nal) / 별 (byeol) |
| -ㅏㅇ ending (-ang) | 사랑 (sarang) / 마음 (maeum) — broader |
| -요 ending (formal) | 해요 (haeyo) / 봐요 (bwayo) / 가요 (gayo) |

Modern K-pop heavily uses **English rhyme in chorus** (slant rhyme, multi-syllabic) mixed with
Korean tail rhyme in verse.

## 10. Cliché K-pop tránh

| Cliché | Lý do tránh | Thay thế |
|--|--|--|
| 마음이 아파 (maeumi apa, "my heart hurts") | Direct, overused | 가슴이 무겁다 (gaseumi mugeopda, "chest feels heavy") |
| 사랑해 (saranghae, "I love you") thẳng tuột | Default, no nuance | 너밖에 없어 (neobakke eopsseo, "only you") |
| 보고 싶다 (bogo sipda, "I miss you") | Quá phổ biến (BTS đã dùng) | 그리워해 (geuriwohae, deeper longing) |
| 영원히 (yeongwoni, "forever") | Hyperbole sáo | 지금 이 순간 (jigeum i sungan, "this moment now") |
| 너 없이 (neo eopsi, "without you") | Cliché 90s K-ballad | 너의 빈자리 (neoui binjari, "your empty seat") |

## 11. Imagery palette K-pop

| Theme | Korean words |
|--|--|
| Tình yêu | 사랑 (sarang), 키스 (kisseu), 손 (son), 눈빛 (nunbit) |
| Đêm thành phố | 밤 (bam), 별 (byeol), 달 (dal), 거리 (geori), 네온 (neon) |
| Mùa | 봄 (bom), 여름 (yeoreum), 가을 (gaeul), 겨울 (gyeoul), 꽃 (kkot) |
| Phương tiện | 지하철 (jihacheol), 택시 (taxi), 자전거 (jajeongeo), 비행기 (bihaenggi) |
| Đồ vật | 사진 (sajin), 편지 (pyeonji), 카세트 (kaseteu), 우산 (usan), 거울 (geoul) |
| Cảm xúc | 슬프다 (seulpeuda), 외롭다 (oeropda), 행복 (haengbok), 그립다 (geuripda) |

## 12. Self-check checklist cho Lyricist (K-pop)

1. ☐ Đã đếm Hangul block syllables cho từng câu?
2. ☐ Hook ≤8 syllables (Korean) hoặc ≤5 (4th gen) hoặc bilingual với syllable count balanced?
3. ☐ Vowel weight đúng (short = 1/8, long/diphthong = sustained)?
4. ☐ Batchim handling: nasal (ㅁㄴㅇㄹ) sustained, stops (ㄱㄷㅂㅅ) clipped?
5. ☐ English code-mix tỷ lệ phù hợp genre (3rd gen 30-50%, 4th gen 50-70%, ballad ≤15%)?
6. ☐ Tránh cliché direct (사랑해, 마음이 아파, 영원히)?
7. ☐ Có concrete imagery Korean (사진, 편지, 카세트, 별)?
8. ☐ Verse 8-14 syllables; chorus 4-10 syllables?
9. ☐ Pronoun consistent (너/나/우리/그대 — formal level)?
10. ☐ Rhyme scheme Korean tail (-ㅓ, -ㅏㅁ, -ㅏㅇ, -ㅡㄹ, -요) hoặc bilingual rhyme?
