# Hebrew-Small-Models-Planning

Planning repository for a small-model layer that fixes Hebrew pronunciation in the
**My Weird Prompts** podcast's text-to-speech output.

MWP is an AI-generated podcast produced in Israel and voiced by Chatterbox TTS. Its
scripts contain Hebrew words written in Latin characters. An English TTS voice reads
*Shabbat* and *kosher* acceptably because the English corpus knows them, and reads
*Bituach Leumi*, *makolet* and *challah* as English grapheme strings, which is wrong
— the guttural ח in *challah* collapses to an English "ch".

The proposal is to detect those words, render them in Hebrew script, and synthesise
them as Hebrew-tagged segments inside an otherwise English line.

**Status 2026-09-22: planning only. Nothing is built.** The scope actually committed
to is stage 1 (the detector), and only if prior art does not already provide it.

## Read in this order

| Document | What it is |
| --- | --- |
| [`plan.md`](plan.md) | The idea as recorded, with open questions |
| [`docs/spec.md`](docs/spec.md) | The technical specification — pipeline stages, decisions, what is deferred |
| [`docs/requirements.md`](docs/requirements.md) | Numbered requirements (FR / IR / DR / NG) |
| [`docs/prior-art.md`](docs/prior-art.md) | What already exists — surveyed before building |
| [`docs/reference/chatterbox-tts.md`](docs/reference/chatterbox-tts.md) | Chatterbox API, verified from source. **Read this first if you are about to design the audio path** |
| [`docs/reference/training-data.md`](docs/reference/training-data.md) | The two corpora that already exist, and the labelling defect in one of them |
| [`docs/reference/mwp-pipeline.md`](docs/reference/mwp-pipeline.md) | Where this plugs into the podcast pipeline, with file and line references |

## Three findings that shape everything else

1. **Chatterbox has no inline language tags.** `language_id` is a per-call
   parameter, so a code-switched sentence must be split into per-language segments
   and concatenated. Hebrew (`he`) *is* supported — by
   `ChatterboxMultilingualTTS`, which the pipeline does not currently use.
2. **The segmentation already exists.** A 250-character chunker and an ffmpeg concat
   are already in production. The change is to make split points language-driven as
   well as length-driven.
3. **The training data exists but its labels do not survive inspection.**
   `danielrosehill/English-Hebrew-Mixed-Sentences` was labelled by substring search:
   114 of 474 labels point inside an unrelated English word, and in those records the
   real Hebrew term is unlabelled. It needs annotating, not converting.

## Layout

| Path | Contents |
| --- | --- |
| `plan.md` | The plan — goals, constraints, open questions |
| `docs/` | Spec, requirements, prior art |
| `docs/reference/` | Verified reference material on external systems |
| `audio/` | The source voice note this project came from |
| `transcripts/` | Verbatim transcripts of `audio/` |
| `scripts/` | Analysis scripts worth re-running |

## Implementation repos

This repo is planning only. Work that gets built lives in its own repository:

| Repo | Stage | Status |
| --- | --- | --- |
| [**Hebrew-Latin-Token-Classifier**](https://github.com/danielrosehill/Hebrew-Latin-Token-Classifier) | 1 — detection | Corpus preparation; 242-task review queue open |

## Related

- `~/repos/github/mwp-podcast/My-Weird-Prompts` — the consumer pipeline (private)
- [`danielrosehill/English-Hebrew-Mixed-Sentences`](https://huggingface.co/datasets/danielrosehill/English-Hebrew-Mixed-Sentences) — 516 code-switched sentences, MIT
- [`danielrosehill/Whisper-Hebrish`](https://huggingface.co/danielrosehill/Whisper-Hebrish) — the ASR fine-tune built on that dataset
- [`My-Weird-Prompts/transcripts`](https://huggingface.co/datasets/My-Weird-Prompts/transcripts) — the episode corpus, CC-BY-4.0
