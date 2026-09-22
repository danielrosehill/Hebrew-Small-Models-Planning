# Requirements

Requirements for the Hebrew code-switching layer of the *My Weird Prompts* podcast
pipeline. Derived from the voice note of 2026-09-22
(`transcripts/hebrew-small-models-2026-09-22.md`) plus what was verified in the
pipeline and corpora on the same date.

Identifiers are stable. `MUST` / `SHOULD` / `MAY` carry their RFC 2119 sense.
Status values: `agreed` (stated in the note), `derived` (follows from a verified
fact), `open` (needs a decision — listed in `docs/spec.md`).

## Context

*My Weird Prompts* is an AI-generated podcast, produced in Israel, voiced by
Chatterbox TTS. Its scripts contain Hebrew words written in Latin characters. An
English TTS voice reads them as English grapheme strings, which is acceptable for
words the English corpus knows (*Shabbat*, *kosher*) and wrong for words it does not
(*Bituach Leumi*, *makolet*, *challah* — the guttural ח collapsing to an English "ch").

## Functional — detection (stage 1)

| ID | Requirement | Status |
| --- | --- | --- |
| FR-1 | The system MUST identify, within an English script line, the tokens that are Hebrew words written in Latin characters. | agreed |
| FR-2 | Output MUST be token- or span-level, not sentence-level. A sentence-level language label is useless here: the whole point is which *part* of the sentence switches. | derived |
| FR-3 | Detection MUST handle **multi-token** terms as single units — *Bituach Leumi*, *teudat zehut*, *Mas Hachnasa*. 51 of the 139 known terms are multi-token. | derived |
| FR-4 | Detection SHOULD handle terms not seen in training. A pure lexicon lookup cannot; this is the main reason to prefer a model over a dictionary. | derived |
| FR-5 | The detector MUST NOT flag English words, and SHOULD NOT flag place names and proper nouns that the English voice already pronounces acceptably (*Tel Aviv*, *Jerusalem*, *Netanyahu*). | derived |
| FR-6 | Perfect accuracy is NOT required. A useful-but-imperfect classifier is explicitly acceptable. | agreed |
| FR-7 | Errors SHOULD be asymmetric in favour of precision: a missed Hebrew word leaves today's behaviour unchanged, a false positive makes an English word be read in Hebrew, which is worse than the status quo. | derived |

## Functional — script conversion (stage 2)

| ID | Requirement | Status |
| --- | --- | --- |
| FR-8 | Each detected span MUST be rendered into Hebrew script — `Shabbat` → `שבת`, `Bituach Leumi` → `ביטוח לאומי`. | agreed |
| FR-9 | Any model used here MUST be open source **and open weight**. This is the stated gate on stage 2. | agreed |
| FR-10 | Where a term is in the project lexicon, the lexicon form MUST win over any model output. A curated table is more reliable than inference for known terms and removes them from the model's risk surface. | derived |
| FR-11 | Unvocalised output is assumed. Whether Chatterbox `he` needs niqqud to disambiguate is untested and is an open question. | open |

## Functional — synthesis (stage 3)

| ID | Requirement | Status |
| --- | --- | --- |
| FR-12 | The script MUST be segmented so each segment is synthesised with a single `language_id` — `en` for the ambient text, `he` for each Hebrew span. Chatterbox has no inline language tags; this is forced by the API. See `docs/reference/chatterbox-tts.md`. | derived |
| FR-13 | The pipeline MUST move from `ChatterboxTTS` (English) to `ChatterboxMultilingualTTS` for any turn containing a Hebrew span. Hebrew (`he`) is one of its 23 supported languages. | derived |
| FR-14 | Segments MUST be concatenated back into one clip per speaker turn, preserving the existing per-turn contract that `pipeline/audio/assembly.py` consumes. | derived |
| FR-15 | Segment joins SHOULD be padded so they do not read as audible cuts. The amount is to be found by listening, not specified up front. | agreed |
| FR-16 | Voice identity MUST stay consistent across the `en` and `he` segments of one turn. Both use the same speaker conditionals; `cfg_weight=0` is the documented lever against cross-language accent bleed. | derived |
| FR-17 | Language-driven splits MUST compose with the existing 250-character length-driven chunking (`MAX_CHARS_PER_TTS`), not replace it. | derived |

## Integration

| ID | Requirement | Status |
| --- | --- | --- |
| IR-1 | The layer MUST run inside the existing normalisation step — `pipeline/audio/tts_pronunciation.py`, `normalize_text()`, called from `tts_parallel.py:195` and `:545`. | derived |
| IR-2 | It MUST be behind an environment kill switch, matching the precedent set by `TTS_CONTRACTIONS=0`. | derived |
| IR-3 | With the kill switch off, output MUST be byte-identical to today's. | derived |
| IR-4 | It MUST NOT increase per-episode generation cost materially. Detection runs per turn over a 4,300-word script; stage 1 has to be small and fast, which is the case for a token classifier and not for an LLM call per turn. | derived |
| IR-5 | The existing ffmpeg concat (`tts_parallel.py:421-430`) SHOULD be reused rather than a parallel assembly path introduced. | derived |

## Data

| ID | Requirement | Status |
| --- | --- | --- |
| DR-1 | Training data SHOULD be derived from `danielrosehill/English-Hebrew-Mixed-Sentences` (516 records, 139 terms, MIT) before any new data is created. | agreed |
| DR-2 | That dataset's under-labelling MUST be repaired before use: one label per record leaves 84 spans unlabelled across 81 records, and all 42 null-label records do contain Hebrew. ~24% of the corpus would otherwise train false negatives. | derived |
| DR-3 | The MWP transcript corpus (4,295 episodes, 18.5M words) SHOULD be used as the in-domain evaluation set and as the source of realistic negatives. | agreed |
| DR-4 | Colloquial-register positives MUST come from somewhere else — synthetic generation or a lexicon. Measured MWP counts: *makolet* 1, *balagan* 1, *beseder* 0, *kol hakavod* 0. | derived |
| DR-5 | Synthetic data, if generated, SHOULD be LLM-annotated and human-reviewed. ~1,000 annotations reviewed in a basic GUI is considered tractable. | agreed |
| DR-6 | A lexicon of Latin-script Hebrew terms paired with Hebrew script MUST be maintained as a first-class artefact. It serves FR-10, seeds FR-1, and is the fallback if either model stage fails. | derived |
| DR-7 | Any published dataset or model SHOULD be MIT-licensed, matching the existing `English-Hebrew-Mixed-Sentences` and `Whisper-Hebrish` artefacts. | derived |

## Non-goals

| ID | Statement |
| --- | --- |
| NG-1 | Not translation. Hebrew words stay Hebrew words; only their script and pronunciation change. |
| NG-2 | Not Hebrew→English transliteration, which is the direction most published work covers. |
| NG-3 | Not general multilingual TTS. English is the ambient language; Hebrew is a guest. |
| NG-4 | Not a Hebrew ASR or STT improvement. `Whisper-Hebrish` already exists for that and is a *source* here, not a target. |
| NG-5 | Not retrofitting the 4,295-episode back catalogue. Forward-looking only unless stated otherwise. |

## The acceptance question

The note is explicit that the whole chain may not be worth the gain, and that the
classifier is worth having regardless. So acceptance is staged:

- **Stage 1 is accepted** if it beats a lexicon lookup on held-out MWP turns and is
  reusable outside the podcast.
- **Stage 2 is accepted** if an open-weight model is found, or if a lexicon covers
  the terms that actually occur. It is a search task first.
- **Stage 3 is accepted** only if a listening comparison against the current audio is
  an improvement — measured against the respelling baseline in
  `docs/reference/mwp-pipeline.md`, not against nothing.
