---
title: "Mixing & Mastering Deep-Dive — Streaming-aware values per genre/platform"
tags: ["production", "mixing", "mastering", "lufs", "frequency", "streaming"]
level: "advanced"
---

# Mixing & Mastering — Deep-Dive

Đây là tham chiếu kỹ thuật cụ thể cho mixing + mastering hiện đại, có values số. Producer sẽ
quote các con số này khi viết mix_notes / mastering target / FX values trong council output.

## 1. LUFS — Streaming platform targets (2024)

| Platform | Target LUFS | Penalty if louder | Format |
|--|--|--|--|
| **Spotify** | −14 LUFS integrated | Turn down (no boost if quieter) | normalization on by default |
| **Apple Music** | −16 LUFS integrated (Sound Check) | Turn down | optional Sound Check |
| **YouTube** | −13 to −14 LUFS | Turn down | always-on |
| **Tidal HiFi** | −14 LUFS | Turn down | always-on |
| **Amazon Music** | −14 LUFS | Turn down | always-on |
| **Pandora** | −14 LUFS | Turn down | always-on |
| **TikTok / Instagram Reels** | −9 to −12 LUFS | NO normalization | hot master wins |
| **Club / DJ play** | −5 to −9 LUFS | NO normalization | hot master wins |
| **CD / Vinyl** | −6 to −10 LUFS | No normalization | platform-dependent |

**Rule of thumb 2024**: Master at **−9 to −7 LUFS** for genres targeting club/social media (reggaeton,
K-pop, EDM); **−10 to −12 LUFS** for ballad/indie/acoustic (preserves dynamics on Spotify);
**−14 LUFS** for "audiophile" target (matches Spotify normalization exactly).

## 2. LUFS targets per genre

| Genre | Master LUFS | LRA (loudness range) | True Peak |
|--|--|--|--|
| Pop ballad (V-pop, English) | −9 to −11 | 8–10 dB | ≤ −1 dBTP |
| K-pop ballad | −7 to −9 | 7–9 dB | ≤ −1 dBTP |
| K-pop idol-pop (3rd gen) | −5 to −7 | 4–6 dB (compressed) | ≤ −1 dBTP |
| K-pop 4th gen | −7 to −9 | 6–8 dB | ≤ −1 dBTP |
| Reggaeton | −5 to −7 | 4–6 dB | ≤ −1 dBTP |
| Latin pop ballad | −8 to −10 | 7–9 dB | ≤ −1 dBTP |
| Bachata | −8 to −10 | 7–9 dB | ≤ −1 dBTP |
| English pop ballad | −9 to −11 | 8–10 dB | ≤ −1 dBTP |
| Bedroom pop | −12 to −10 | 9–11 dB (intentional dynamic) | ≤ −1 dBTP |
| Synthwave | −7 to −9 | 5–7 dB | ≤ −1 dBTP |
| Modern J-pop | −6 to −8 | 5–7 dB (loud) | ≤ −1 dBTP |
| Anime opening | −5 to −7 | 4–6 dB (very loud) | ≤ −1 dBTP |
| Japanese city-pop (revival) | −10 to −12 | 9–11 dB (vintage analog) | ≤ −1 dBTP |
| Hip-hop storytelling | −7 to −10 | 6–9 dB | ≤ −1 dBTP |
| V-pop ballad | −9 to −11 | 8–10 dB | ≤ −1 dBTP |
| V-pop dance-pop | −6 to −9 | 5–7 dB | ≤ −1 dBTP |

## 3. Frequency carving — instrument frequency map

Mỗi instrument có "home" và "rival" frequency. Carve rivals to clear home.

### Vocals

| Range | Action |
|--|--|
| 80–120 Hz | High-pass filter (HPF) for non-bass vocals — REMOVE rumble |
| 200–300 Hz | Boost +1–2 dB for warmth (intimate ballad) OR cut −2 dB if muddy |
| 400–600 Hz | Cut −2 to −4 dB if "boxy" sound |
| 1.5–3 kHz | Boost +1–2 dB for presence (this is "the talking" range) |
| 5–7 kHz | Boost +1–2 dB for clarity |
| 10–12 kHz | Boost +1–3 dB "air" — modern pop especially |

### Kick drum

| Range | Action |
|--|--|
| 30–60 Hz | Sub-bass thump (if room/system can handle) |
| 80–120 Hz | "Body" of kick |
| 300–500 Hz | Cut for "boxy" |
| 1.5–3 kHz | Click/attack |
| 5–8 kHz | Optional brightness for modern pop |

### Snare drum

| Range | Action |
|--|--|
| 80–200 Hz | Body — add for fatness |
| 250–350 Hz | "Box" — usually cut |
| 1–3 kHz | Crack/attack |
| 5–8 kHz | Brightness/snap |

### Bass (electric/synth)

| Range | Action |
|--|--|
| 30–80 Hz | Sub fundamental |
| 80–200 Hz | "Body" |
| 200–400 Hz | "Mud zone" — usually cut |
| 700 Hz–1 kHz | "Honk" — boost slightly for definition through small speakers |
| 2–4 kHz | Pluck attack — boost for clarity through phones |

### Acoustic guitar

| Range | Action |
|--|--|
| 100–200 Hz | "Body" |
| 200–500 Hz | "Boxy" — cut |
| 1–3 kHz | Pick attack |
| 6–10 kHz | "Sparkle" |
| 12–16 kHz | "Air" — modern hi-fi |

### Piano

| Range | Action |
|--|--|
| 100–200 Hz | Bass register clear |
| 250–400 Hz | "Mud" — minor cut |
| 1–3 kHz | Mid clarity |
| 5–8 kHz | "Bell" character |
| 10–14 kHz | "Air" |

## 4. Vocal & kick conflict map (200 Hz / 3 kHz / 10 kHz)

When **vocal + kick** play together (chorus), they conflict in 3 zones:

| Zone | Vocal need | Kick need | Resolution |
|--|--|--|--|
| 200 Hz | Warmth | Body | Cut kick 200 Hz by −2 dB; boost vocal 200 Hz by +1 dB |
| 3 kHz | Presence | Click | Boost vocal 3 kHz +2 dB; control kick 3 kHz with EQ wide-cut |
| 10 kHz | "Air" | (n/a) | Vocal owns this zone; kick stays out |

## 5. Bus compression

| Bus | Compression target | Ratio | Attack/Release |
|--|--|--|--|
| Vocal bus | 2–4 dB GR (gain reduction) | 4:1 | 10ms attack, 80ms release |
| Drum bus | 2–3 dB GR | 4:1 | 30ms attack, 100ms release |
| Master bus (glue) | 1–2 dB GR | 2:1 | 30ms attack, 100ms release |
| Parallel compression on drums | 6–10 dB GR | 8:1 | 5ms attack, 30ms release |

## 6. Reverb settings — by genre

| Genre | Plate decay | Predelay | Mix |
|--|--|--|--|
| V-pop ballad | 1.2–1.5s | 25–35 ms | 18–25% |
| K-pop ballad | 1.4–1.8s | 30–40 ms | 20–30% |
| English pop ballad | 1.5–2.0s | 30–50 ms | 20–30% |
| Bedroom pop | 0.8–1.2s | 10–20 ms | 12–18% |
| Synthwave | 1.0s gated + 0.4s plate | 20 ms | 15–25% |
| K-pop idol-pop | 0.8–1.2s plate | 15–25 ms | 12–18% |
| Reggaeton | 0.8–1.2s plate + slap delay | 15–25 ms | 12–18% |
| Latin pop ballad | 1.4–1.8s | 30–40 ms | 20–30% |
| Bachata | 1.4–1.8s | 25–35 ms | 18–25% |
| Modern J-pop | 1.2–1.5s | 20–30 ms | 15–20% |
| Hip-hop storytelling | 0.8–1.2s + slap delay 1/4 | 15–25 ms | 12–18% |
| Japanese city-pop | 1.5–2.0s + tape delay | 30–40 ms | 18–25% |
| Anime opening | 1.0s gated 80s style | 20 ms | 15–20% |

## 7. Master limiter settings

| Setting | Value | Notes |
|--|--|--|
| **True peak ceiling** | −1.0 dBTP | Critical for streaming (avoid clipping after MP3/AAC encode) |
| Lookahead | 5 ms | Smooth transients without distortion |
| Release | Auto / 30–80 ms | Genre-dependent |
| **Final limiter type** | Modern broadband (FabFilter Pro-L 2, Waves L3) | Avoid 90s-style "brickwall" sound |

## 8. Loudness penalty algorithm

When mastering louder than streaming target (e.g. −7 LUFS vs Spotify −14 target):
- Spotify lowers your track by **7 dB** to match its target
- This means your DYNAMIC RANGE is reduced (no benefit from being louder)
- BUT your "punch" in transients is preserved if not over-limited

**Rule**: target the platform's LUFS or +2 dB above (e.g. −12 LUFS for Spotify target −14)
unless genre demands hot master (reggaeton, K-pop idol-pop, club).

## 9. Stereo width

| Element | Width |
|--|--|
| Lead vocal | Mono center |
| Background vocals | Wide L80%/R80% |
| Bass | Mono center (always) |
| Kick | Mono center |
| Snare | Mono center (slight ambience L/R wide for room mics) |
| Hi-hat | Slight L (L20%) — drum kit positioning realism |
| Acoustic guitars (rhythm) | Wide L80%/R80% if double-tracked |
| Piano | Stereo image L40%/R40% (real piano natural width) |
| Pads | Wide L100%/R100% (synth padding) |
| Strings | Hall L80%/R80% (orchestral seat positioning) |
| Reverb returns | Wide L80%/R80% |

## 10. Mastering chain typical (modern 2020s)

```
1. Subtractive EQ (clean low-end below 30 Hz, cut 200-400 Hz mud)
2. Multiband compression (3 band: low/mid/high; 1-2 dB GR each)
3. Saturation/tape (subtle 1-3% drive, modern color)
4. Stereo width control (no widening below 200 Hz; subtle widening 5-15% above 8 kHz)
5. Final EQ (additive — boost air 12 kHz +1 dB, slight low-shelf 100 Hz +0.5 dB if needed)
6. Brickwall limiter (true peak ceiling -1.0 dBTP, GR 2-4 dB final)
7. Dithering (24-bit → 16-bit conversion, TPDF noise shaping for CD/streaming)
```

## 11. Reference tracks for mastering target

When in doubt, A/B compare with these:

| Genre | Reference track | LUFS | Style notes |
|--|--|--|--|
| V-pop ballad | Hà Anh Tuấn — Tháng Tư | −10 LUFS | Plate verb generous, vocal forward |
| K-pop ballad | BTS — Spring Day | −8 LUFS | Vocal stack escalation, modulate |
| K-pop idol-pop | BLACKPINK — How You Like That | −5 LUFS | Hyper-loud, aggressive trap |
| K-pop 4th gen | NewJeans — Hype Boy | −7 LUFS | UK Garage 2-step, vocal stack 3-part |
| English pop ballad | Adele — Someone Like You | −10 LUFS | NO modulation, vocal-led |
| Reggaeton | Bad Bunny — Tití Me Preguntó | −5.5 LUFS | Dembow lock, autotuned |
| Latin pop ballad | Camilo — Vida de Rico | −9 LUFS | Spanish guitar fingerstyle |
| Bachata | Romeo Santos — Propuesta Indecente | −8 LUFS | Requinto + vocal falsetto |
| Bedroom pop | Clairo — Pretty Girl | −12 LUFS | Lo-fi, intentional dynamic |
| Synthwave | The Weeknd — Blinding Lights | −7 LUFS | Gated reverb snare 0.4s |
| Modern J-pop | YOASOBI — Yoru ni Kakeru | −6 LUFS | Hot master, vocal stack |
| Hip-hop storytelling | Kendrick Lamar — Money Trees | −9 LUFS | Sample-based, sparse |

## 12. Self-check checklist cho Producer

1. ☐ Master LUFS đúng platform target (Spotify −14, hoặc genre-specific)?
2. ☐ True peak ceiling −1.0 dBTP (NOT 0 dBTP)?
3. ☐ Vocal HPF 80–120 Hz để clear rumble?
4. ☐ Vocal/kick conflict zones (200 Hz / 3 kHz / 10 kHz) đã carve?
5. ☐ Bus compression 1-2 dB GR master (no crush)?
6. ☐ Reverb decay match genre table (ballad 1.4–1.8s, lo-fi 0.8–1.2s)?
7. ☐ Bass mono center; kick mono center?
8. ☐ LRA preserved (no over-limiting → LRA <4 dB unless genre demands)?
9. ☐ Reference track A/B comparison done với genre matching?
10. ☐ Dithering applied for 16-bit final (TPDF noise shaping)?
