---
title: "Vocal Recording — Cookbook (mic / preamp / signal chain / vocal tuning)"
tags: ["production", "vocal", "recording", "microphone", "signal-chain", "tuning"]
level: "advanced"
---

# Vocal Recording Cookbook

Tham chiếu kỹ thuật cho vocal recording + signal chain + post-production tuning. Producer
sẽ quote các giá trị này khi viết FX values và mix_notes.

## 1. Microphone selection by genre

### Female vocal

| Genre | Mic | Reason |
|--|--|--|
| V-pop ballad | Neumann U87 condenser | Warm mid, intimate, smooth top |
| K-pop ballad (IU/Taeyeon) | Neumann U87 / Sony C800G | Crystal-clear top, Korean preference |
| K-pop idol-pop | Sony C800G / Neumann TLM103 | Hot top end, autotuned-friendly |
| K-pop 4th gen | Neumann U87 / TLM103 | Soft breathy capture |
| Reggaeton (Karol G) | Neumann TLM103 / Shure SM7B | Forward presence, club-friendly |
| Latin pop ballad (Shakira) | Neumann U87 / U47 | Warm mid Latin tradition |
| Bachata | Neumann U87 / TLM103 | Romantic warmth |
| Bedroom pop (Clairo) | Shure SM7B / dynamic | Lo-fi intentional, less polished |
| Synthwave (Dua Lipa) | Neumann TLM103 | Modern hot top |
| English pop ballad (Adele) | Neumann U87 | Warm, intimate close-mic |
| Modern J-pop (YOASOBI) | Neumann U87 / TLM103 | Pure clean top |
| Anime opening (LiSA) | Neumann TLM103 | Powerful belt |
| City-pop revival | Vintage Neumann U47 / Telefunken | Vintage warmth |

### Male vocal

| Genre | Mic | Reason |
|--|--|--|
| V-pop male ballad (HAT) | Neumann U87 / TLM103 | Smooth tenor |
| K-pop male ballad (Crush, V) | Neumann U87 / Sony C800G | Korean preference |
| K-pop male idol (BTS) | Sony C800G | Hot top, autotune-friendly |
| Reggaeton (Bad Bunny) | Shure SM7B | Forward intimate, autotuned |
| Bachata (Romeo Santos) | Neumann U87 | Romantic warmth |
| Hip-hop (Kendrick) | Shure SM7B / Telefunken U47 | Forward, raw |
| Indie/Bedroom (Boy Pablo) | Shure SM7B | Intentional grit |

## 2. Preamp & signal chain

### Standard signal chain (modern pop, ballad)

```
Mic → Preamp (Neve 1073, API 512c, UA 610) → 1176 compressor → LA-2A optical compressor →
EQ (Pultec, API 550) → DAW input
```

Preamp adds **color** (Neve = warm British; API = punchy American; UA = vintage tube).

### Hardware compression chain

| Stage | Action | Purpose |
|--|--|--|
| 1176 compressor | Fast attack 5-10ms, fast release 50-100ms, ratio 4:1, GR 4-6 dB | Catches peaks, adds attack |
| LA-2A optical | Slow attack 10ms, slow release 80ms, GR 2-4 dB | Smoothes overall vocal level |
| Total GR before EQ | 6-10 dB combined | Controlled vocal ready for EQ |

### Reggaeton/K-pop idol heavy chain

```
Mic → Preamp → 1176 (heavy 6-8 dB GR) → API 550 EQ →
Antares Auto-Tune (heavy retune speed 0-10 ms) → DAW
```

The **Auto-Tune in chain** = aesthetic choice for genre.

## 3. Vocal tuning (Melodyne / Auto-Tune)

| Style | Tool | Settings |
|--|--|--|
| Natural correction (ballad) | Melodyne | Manual note pull, formant preserve, ~50 cents max |
| Subtle pitch correction | Auto-Tune Pro Classic mode | Retune speed 20-40, key/scale set |
| Moderate (mainstream pop) | Auto-Tune Pro | Retune speed 10-20, formant preserved |
| Heavy (reggaeton, hyper-pop) | Auto-Tune Pro | Retune speed 0-5 (instant snap), no formant correct |
| T-Pain style | Auto-Tune Pro | Retune speed 0, scale C minor blues, throat width adjusted |

## 4. Vocal stack design

### Lead vocal stack (chorus)

| Layer | Pitch | FX |
|--|--|--|
| Lead | 0 (fundamental) | Centered, 1176 + LA-2A, plate verb 1.4s |
| Doubled | 0 (cents −5) | Centered, slightly back in mix, parallel compression |
| 3rd above | +3 semitone (3rd interval) | Wide L60%/R60%, plate verb 0.8s |
| 5th above | +5 semitone (5th) | Wide L80%/R80% |
| Octave below | −12 semitone | Centered, low-pass to keep bottom |
| Ad-lib | Improvised | Wide L100%/R100%, slap delay 1/4 dotted |

### Vocal stack escalation (genre-specific)

| Genre | Verse | Pre | Chorus 1 | Chorus 2 | Final Chorus |
|--|--|--|--|--|--|
| V-pop ballad | Solo | Solo + soft doubled | Lead + 3rd above | Lead + 3rd + doubled | Lead + 3rd + 5th + ad-lib |
| K-pop ballad | Solo (member 1) | Solo (member 2) | Lead + 3rd | Lead + 3rd + doubled | 5-part stack with ad-libs |
| K-pop 4th gen | Solo | Solo + light doubled | Lead + 3rd | Lead + 3rd + doubled | 3-part max + light ad-lib |
| K-pop idol-pop 3rd gen | Solo | Solo + doubled | Lead + 3rd + counter | 4-part stack | 5-part anthemic + tom rolls |
| Reggaeton | Solo + autotune | Solo | Lead + 3rd above | Lead + 3rd + doubled | 3-part + heavy ad-libs |
| Bachata | Solo | Solo | Lead + 3rd | Lead + 3rd + falsetto layer | Lead + 3rd + 5th + falsetto + ad-lib |
| Latin ballad | Solo | Solo doubled | Lead + 3rd | Lead + 3rd + doubled | 4-part + emotional ad-lib |
| English pop ballad | Solo | Solo + soft doubled | Lead + 3rd | Lead + 3rd + doubled | Lead + light layer (no big stack) |
| Synthwave | Solo + chorus FX | Solo + light doubled | Lead + 3rd above wide | Lead + 3rd + doubled wide | 4-part wide + chorus FX heavy |
| Bedroom pop | Solo | Solo + light doubled | Lead + 3rd above (subtle) | Lead + 3rd + doubled | 2-part max (intentional minimal) |

## 5. Vocal effects detailed

### Plate reverb settings per genre

| Genre | Decay | Predelay | EQ on send |
|--|--|--|--|
| V-pop ballad | 1.2-1.5s | 25-35ms | Cut <250 Hz, +1 dB at 6 kHz |
| K-pop ballad | 1.4-1.8s | 30-40ms | Cut <250 Hz, +1 dB at 8 kHz |
| English pop ballad | 1.5-2.0s | 30-50ms | Cut <300 Hz, +1 dB at 7 kHz |
| Bedroom pop | 0.8-1.2s | 10-20ms | Cut <300 Hz |
| Synthwave | 1.0s gated 80s + 0.4s plate | 20ms | Cut <250 Hz |
| Reggaeton | 0.8-1.2s | 15-25ms | Cut <200 Hz, +1 dB at 5 kHz |
| Latin ballad | 1.4-1.8s | 30-40ms | Cut <250 Hz, +1 dB at 7 kHz |
| Bachata | 1.4-1.8s | 25-35ms | Cut <250 Hz, +1 dB at 6 kHz |
| Hip-hop | 0.8-1.2s + slap delay | 15-25ms | Cut <250 Hz |
| Modern J-pop | 1.2-1.5s | 20-30ms | Cut <250 Hz, +1 dB at 8 kHz |

### Slap delay 1/4 dotted

Used in: K-pop ballad, R&B, hip-hop, bachata.
- Time: tempo-synced 1/4 dotted (e.g. at 120 BPM = 750 ms)
- Feedback: 25-35%
- Mix: 15-25%
- High-pass: cut below 500 Hz (avoid muddy delay)

### Chorus effect

Used in: bedroom pop, synthwave, indie.
- Rate: 0.5-1.5 Hz
- Depth: 20-40%
- Mix: 20-30%

### Saturation/Tape

Used universally; subtle 1-3% drive on master, 5-10% on individual tracks for warmth.

## 6. Vocal recording technique

### Mic placement

| Style | Distance | Angle | Pop filter |
|--|--|--|--|
| Intimate close-mic (ballad, bedroom pop) | 6-12 inches | 0° on-axis | Yes, 6 inches in front of mic |
| Standard pop | 12-18 inches | 0° on-axis | Yes |
| Loud belt vocal (Adele, IU, Taeyeon) | 18-24 inches | 0° on-axis | Yes |
| Whisper / ASMR | 4-8 inches | Slightly off-axis (15°) | Yes |

### Headphone monitoring

| Setting | Purpose |
|--|--|
| Click track + light music mix | Stay in tempo, hear pitch references |
| Vocal in headphones at -3 dB below mix | Hear yourself but not over-emphasize |
| Slight reverb on cue mix (1.0s plate) | Helps singer with pitch and confidence |

### Take selection workflow

1. **Multiple takes** — record 5-8 takes per section
2. **Comp**: stitch together best phrases from different takes
3. **Crossfade** at edits (5-10 ms)
4. **Tune after comp** — Melodyne or Auto-Tune on final comp

## 7. Vocal tuning workflow

### Step 1: Pitch correction
- Open Melodyne, scan vocal track
- Identify off-pitch notes (>20 cents off)
- Drag note centers to correct pitch
- Preserve formants (toggle on)

### Step 2: Timing (optional)
- If lyric falls behind beat, time-shift phrase
- Be conservative — too much timing shift sounds robotic

### Step 3: Vibrato adjustment
- For belt vocals, ensure vibrato on long sustains
- For breathy bedroom pop, reduce/eliminate vibrato

### Step 4: Final polish
- Compare to reference track for similar genre
- A/B with naturalistic version (some pitch variation OK)

## 8. Vocal production tools (industry standard)

### Free / Stock (DAW-included)

- Logic Pro: Pitch Correction (basic)
- Ableton: Auto Filter, Glue Compressor
- Pro Tools: Avid Mod Delay III, Pro Tools EQ7

### Paid (industry)

- **Antares Auto-Tune Pro** ($99/year) — pitch correction, T-Pain effect
- **Melodyne** ($249-$849) — best for natural correction, polyphonic note editing
- **iZotope Nectar 4** ($249) — vocal channel strip, AI-assisted mixing
- **Waves Tune** ($29-$299 sales) — alternative to Auto-Tune
- **FabFilter Pro-Q 4** ($179) — best surgical EQ
- **FabFilter Pro-MB** ($199) — multiband compression
- **FabFilter Pro-L 2** ($179) — mastering limiter
- **Soundtoys Bundle** ($499) — Decapitator (saturation), EchoBoy (delay)

## 9. Self-check checklist cho vocal recording / production

1. ☐ Mic chosen for genre (U87 ballad, SM7B intimate/raw, C800G K-pop)?
2. ☐ Preamp warmth chosen (Neve British, API American, UA tube)?
3. ☐ HPF 80-120 Hz applied to vocal?
4. ☐ Compression 6-10 dB GR total (1176 + LA-2A or equivalent)?
5. ☐ Pitch correction done (subtle for ballad, heavy for autotune genres)?
6. ☐ Plate verb decay matches genre table (V-pop 1.2-1.5s, K-pop 1.4-1.8s)?
7. ☐ Vocal stack escalation matches genre table?
8. ☐ Bus compression on vocal sub-bus (4:1, 4-6 dB GR)?
9. ☐ De-essing applied (cut sibilance ~5-7 kHz)?
10. ☐ Final A/B with reference track of same genre?
