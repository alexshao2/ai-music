---
title: "Suno Style Cookbook — Cách viết Style tag tối ưu cho Suno"
tags: ["production", "suno", "style-tag", "prompt-engineering"]
level: "intermediate"
---

# Suno Style Cookbook

Suno có 1 ô **Styles** tối đa 200 ký tự. Đây là vùng quyết định **toàn bộ sound** của bài. Producer cần
viết Style tag sắc bén để Suno generate đúng vibe.

## Format đề xuất

Sweet spot: **140–180 ký tự** (đừng dùng full 200 — Suno xử lý ngắn tốt hơn).

Format cấu trúc:

```
<genre>, <subgenre>, <tempo>, <key/mood>, <core instruments>, <vocal characteristic>, <production palette>, <reference vibe>
```

Ví dụ tốt (160 ký tự):
```
vietnamese ballad, slow 78 bpm, e minor, fingerpicked acoustic guitar, intimate breathy female vocal, plate verb, warm tape saturation, ha anh tuan-style
```

## Quy tắc DO

1. **Genre đầu tiên** — Suno match genre với training data.
2. **Tempo cụ thể** ("78 bpm" tốt hơn "slow"). Suno hiểu BPM number.
3. **Key/mood pairing** — "e minor" + "melancholic" gấp đôi tín hiệu.
4. **Instruments cụ thể** — "fingerpicked acoustic guitar" tốt hơn "guitar". "rhodes electric piano" tốt hơn "keyboard".
5. **Vocal characteristic** — "intimate breathy female", "powerful belt male", "young pop tone".
6. **Production palette** — "plate verb", "tape saturation", "808 sub bass".
7. **Reference artist hoặc style** — "ha anh tuan-style", "vu.-style", "dtap production".

## Quy tắc DON'T

1. ❌ **Generic adjectives**: "good", "nice", "beautiful", "great" → Suno ignore.
2. ❌ **Conflicting instruments**: "acoustic guitar + 808 sub" trừ khi thực sự ý đồ hybrid.
3. ❌ **Quá nhiều genre**: "pop, rock, jazz, soul" → Suno confused, output trung bình.
4. ❌ **Toàn từ tiếng Việt**: Suno hiểu English style tags tốt hơn — viết English mặc dù song là tiếng Việt.
5. ❌ **Chỉ 1 từ**: "ballad" → Suno không có đủ tín hiệu, output generic.
6. ❌ **Câu dài**: "I want a sad melancholic song with..." → Suno không phải prose parser.

## Vocabulary bank theo category

### Genre / Subgenre
- vietnamese ballad / vpop ballad / k-pop influenced vpop
- vietnamese r&b / neo-soul / alt-r&b
- indie folk / indie pop / dream pop
- vietnamese dance pop / tropical pop / electro-pop
- folk fusion / folk rap / ethnic-pop
- city pop / lo-fi hiphop / chillhop

### Tempo descriptors
- slow ballad (60–80 bpm)
- mid-tempo (80–100 bpm)
- uptempo (100–120 bpm)
- dance tempo (120–130 bpm)

### Key + mood pairings
- e minor + melancholic
- a minor + nostalgic
- f major + warm bittersweet
- d major + uplifting
- c minor + dark intimate
- g major + youthful innocent
- bb major + jazz warm

### Instruments — string family
- fingerpicked acoustic guitar (nylon / steel)
- strummed acoustic guitar
- 12-string acoustic
- clean electric guitar (telecaster / strat)
- crunch electric guitar (les paul)
- piano felt grand
- piano bright grand
- piano upright
- rhodes electric piano (warm)
- wurlitzer electric piano
- hammond b3 organ
- mandolin / banjo
- upright bass / electric bass / synth bass / 808 sub

### Instruments — Vietnamese
- dan tranh (vietnamese zither)
- dan bau (monochord)
- sao truc (vietnamese flute)
- dan nhi (two-string fiddle)

### Instruments — strings/woodwinds
- string quartet / string section / synth strings / cinematic strings
- violin solo / cello solo / viola
- saxophone (alto / tenor / soprano)
- flute / oboe / clarinet

### Drums
- brushed drums (jazz/folk)
- modern pop kit
- trap kit (808 + snappy snare)
- house kit (4-on-the-floor)
- live tracked drums / programmed drums
- linndrum / lm-1 (80s pop)

### Vocal characteristics
- intimate breathy / close-mic
- powerful belt
- whisper-sing / talk-singing
- soulful melismatic
- raw indie
- young pop tone
- mature ballad voice
- harmony stack 3-part / 4-part
- ad-libs at end

### Production palette
- plate verb / hall verb / spring verb
- tape saturation / tube warmth / vinyl noise
- sidechain compression / pumping bass
- gated reverb (80s snare)
- vintage analog warmth
- modern radio-pop polish
- lofi grit / lofi tape hiss

### Reference styles
- ha anh tuan-style
- vu.-style indie
- son tung-style modern vpop
- dtap production
- touliver production
- khac hung writing
- amee-style young pop
- toc tien-style ballad
- finneas/billie eilish-style intimate
- jacob collier-style harmony

## Worked examples theo brief

### Brief: "V-pop ballad slow, hoài niệm, vocal nữ"

```
vietnamese ballad, slow 78 bpm, a minor, felt grand piano, fingerpicked acoustic
guitar, lush string section, intimate breathy female vocal, plate verb, warm tape
saturation, ha anh tuan-style production
```

### Brief: "Indie V-pop, intimate, vocal nam"

```
indie vietnamese folk, slow 70 bpm, d minor, fingerpicked nylon guitar, brushed drums,
upright bass, wurlitzer touches, raw close-mic male vocal, lofi tape warmth, vu.-style
intimate production
```

### Brief: "Uptempo dance pop, vui tươi"

```
vietnamese dance pop, uptempo 116 bpm, d major, plucked synth lead, 808 sub bass with
glide, sidechained four-on-floor kick, vocal stack chorus, modern radio polish, dtap
hook style production
```

### Brief: "Folk fusion với đàn tranh"

```
vietnamese folk fusion, mid-tempo 92 bpm, d major pentatonic, dan tranh pluck melody,
modern pop drum kit with vietnamese percussion, dan bau solo bridge, ornamental melismatic
female vocal, dtap-style fusion production
```

### Brief: "R&B chill cho cuối tuần"

```
vietnamese r&b, mid-tempo 84 bpm, c minor, rhodes piano, 808 sub bass with glide, snap
clap, jazzy 9th and 11th chords, intimate close-mic vocal with tasteful melisma, neo-soul
production, soobin/tlinh-style
```

## Negative tags (nếu Suno hỗ trợ)

Một số phiên bản Suno cho phép `[no autotune]`, `[no trap drums]`. Dùng khi:
- Bài indie-folk → `[no autotune]` (không pitch-correct nặng)
- Bài ballad mộc → `[no edm drops]`
- Bài R&B intimate → `[no big chorus]`

## Length validation

```python
def validate_style(style: str) -> bool:
    return 100 < len(style) < 200  # sweet spot 140-180
```

## Common errors khi viết Style tag

1. **Quá ngắn** ("vietnamese ballad") → Suno generic.
2. **Quá dài** (>200) → Suno cắt cụt random.
3. **Conflicting instruments** ("acoustic guitar + heavy 808") → Suno pick 1 random.
4. **Genre mơ hồ** ("various") → Suno default to mainstream pop.
5. **Vocal description thiếu** → Suno chọn random vocal style.
6. **Reference artist sai** ("Beyoncé-style" cho V-pop ballad) → Suno mismatch.
