# Specification — Hebrew code-switching layer for My Weird Prompts TTS

Version 0.1, 2026-09-22. **Planning document. Nothing here is built.**

Source: the voice note at `transcripts/hebrew-small-models-2026-09-22.md`, plus what
was verified in the pipeline, the corpora and the prior-art literature on the same
date. Requirement IDs (`FR-n`, `IR-n`, `DR-n`) refer to `docs/requirements.md`.

## 1. Problem

*My Weird Prompts* is an AI-generated podcast produced in Israel and voiced by
Chatterbox TTS. Its scripts contain Hebrew words written in Latin characters. The
English voice reads them as English grapheme strings.

The failure is graded, not binary:

| Class | Example | Current output |
| --- | --- | --- |
| In the English corpus | *Shabbat*, *kosher* | Acceptable |
| Institutional, not in the English corpus | *Bituach Leumi*, *Mas Hachnasa* | Read as English letter strings |
| Colloquial, not in the English corpus | *makolet*, *balagan*, *beseder* | Same |
| Guttural phonemes | *challah* (ח) | Worst case — "chala", ח collapsed to English "ch" |

Marking those spans with a Hebrew language tag would fix the pronunciation. Nothing
in the pipeline currently identifies them.

## 2. What was established before specifying anything

Five facts, all verified 2026-09-22, that move the design away from the voice note's
first framing.

**2.1 Chatterbox has no inline language tags.** `language_id` is a per-call
parameter on `ChatterboxMultilingualTTS.generate()`, validated against a 23-language
set. The tokenizer is language-conditioned, so one call serves one script. There is
no `<he>…</he>`. Detail: `docs/reference/chatterbox-tts.md`.

*Consequence:* the note's stage 3 ("overwrite the English word and prepend and suffix
it with the Hebrew marker") cannot be implemented as written. Segmentation is forced.

**2.2 Hebrew *is* supported** — `"he": "Hebrew"` in `SUPPORTED_LANGUAGES`. The whole
plan is viable. But the pipeline currently uses the **English-only** `ChatterboxTTS`
class, so this is a model swap, not a flag (FR-13).

**2.3 The segmentation already exists.** `MAX_CHARS_PER_TTS = 250` chunks turns
today, and `tts_parallel.py:421-430` concatenates chunks with ffmpeg. The note treats
per-turn multi-clip generation as a new challenge; it is the existing design. The
change is to make split points language-driven as well as length-driven (FR-17).
Detail: `docs/reference/mwp-pipeline.md`.

**2.4 Nothing off the shelf detects romanized Hebrew.** No `heb_Latn` label exists in
GlotLID v3, `lid.176` or `lid218e`. No token-level code-switching model covers
Hebrew. No Hebrew-English code-switching corpus exists at all. **Stage 1 must be
built** — the note's suspicion, confirmed.

**2.5 One Latin→Hebrew model exists and it is word-level.** TaatikNet
(`malper/taatiknet`, ByT5-small, CC BY-SA 3.0, last touched 2023-06-25, 73 downloads).
Multi-word phrases — which is what *Bituach Leumi* and *teudat zehut* are, and 51 of
139 known terms — are **unsolved by any off-the-shelf component**. Detail:
`docs/prior-art.md`.

## 3. Architecture

```
script turn
   │
   ├─▶ [1] detector ─────────── spans: which tokens are Hebrew-in-Latin
   │                              lexicon lookup ∪ token classifier
   ├─▶ [2] script conversion ─── spans → Hebrew script
   │                              lexicon table → TaatikNet fallback
   ├─▶ [3] segmentation ──────── turn → [(text, language_id)] segments
   │                              deterministic; composes with the 250-char chunker
   └─▶ [4] synthesis ─────────── ChatterboxMultilingualTTS per segment → ffmpeg concat
```

Stage 3 in the voice note was described as a possible third *model*. **It is not a
model.** Given stage 1 spans and stage 2 forms, producing the segment list is
deterministic string work. Recording this so nobody trains something unnecessary.

### 3.1 Detector

Input: one speaker turn of plain text. Output: character spans, each with a
confidence.

Two components, used together:

- **Lexicon lookup** — longest-match over the curated term list (DR-6). Deterministic,
  handles multi-token terms natively, ~100% precision on known terms.
- **Token classifier** — `xlm-roberta-base` fine-tuned for token classification,
  BIO-tagged, three labels (`en` / `he-latn` / `na`), following the EnTaCs recipe.
  Its job is only the words the lexicon does not have (FR-4).

Precision is weighted over recall (FR-7): a miss leaves today's behaviour unchanged,
a false positive makes an English word be read in Hebrew, which is worse than the
status quo.

**Expected performance:** EnTaCs reports macro-F1 0.844 with the romanized class at
**F1 0.638** on a comparable small hand-annotated set. Plan for ~0.64 on the
classifier component, not 0.9. FR-6 accepts that; the lexicon carries the
high-frequency terms where accuracy matters most.

### 3.2 Script conversion

**Lexicon first, model second** — this inverts the voice note's framing, and it is
the main design decision in this document.

The note assumed stage 2 would be a model with a lexicon as a fallback. The prior art
argues the reverse:

- The terms that actually occur are a **closed, small, high-frequency set** — 139 in
  the labelled dataset, roughly 40 with meaningful frequency in 4,295 MWP episodes.
- Every available model is **word-level**, and the hard cases are **multi-word**.
- A curated table is auditable, testable and correct by construction; a 2023
  ByT5-small with 73 downloads is none of those things.

So: lexicon table for known terms (FR-10), TaatikNet for out-of-lexicon words, and
nothing rendered into Hebrew that neither can produce — unknown spans are left as
English, which is the current behaviour and therefore safe.

**TaatikNet integration notes** (from `docs/prior-art.md`, both traps confirmed):
the HF repo is `malper/taatiknet`, **not** `morrisalp/taatiknet`, which 401s; feed it
**one word at a time**, splitting on whitespace yourself; raise `max_length` or output
truncates.

### 3.3 Segmentation

Turn → ordered `[(text, language_id)]`. Constraints:

- Each segment carries exactly one `language_id` (FR-12).
- Segment boundaries fall on span boundaries, then on the existing 250-character
  budget within each resulting run (FR-17).
- Short English runs between two Hebrew spans should be left English rather than
  absorbed — accent bleed is the risk, not clip count.

### 3.4 Synthesis

- `ChatterboxMultilingualTTS.from_pretrained(device=..., t3_model="v3")`.
- Same speaker conditionals across both languages in a turn (FR-16). We are
  deliberately violating Chatterbox's guidance that `language_id` should match the
  reference clip's language, since the reference voices are English. **`cfg_weight=0`
  is the documented lever against cross-language accent bleed** — start there.
- Concatenate to one clip per turn (FR-14), reusing the existing ffmpeg path (IR-5),
  with padding at joins tuned by listening (FR-15).

## 4. Integration

Lives in `pipeline/audio/tts_pronunciation.py`, inside `normalize_text()` (IR-1),
behind an env kill switch on the `TTS_CONTRACTIONS=0` precedent (IR-2), byte-identical
output when off (IR-3).

**A warning already written into that file.** Acronym phonetic spell-out was removed
on 2026-06-09 because spelling out letter names made Chatterbox read "URL" as the
sentence "you are el". Naive respelling has **already failed once in this exact
pipeline**. Any pseudo-phonetic English respelling inherits that risk — which is the
argument for real Hebrew segments over clever spelling.

## 5. Phasing

Deliberately ordered so each phase produces something useful alone and the expensive
phases have to earn themselves.

### Phase 0 — the lexicon (no model)

Build `lexicon.csv`: Latin form(s), Hebrew script, category, source, first-seen.

Seed from: the 139 terms in `English-Hebrew-Mixed-Sentences`; everything the MWP grep
found; then kaikki.org's Hebrew `roman` fields for breadth. Prefer kaikki.org over
TaatikNet's CSV as the bulk source — TaatikNet's is CC BY-SA 3.0 and share-alike
would constrain what can be published (DR-7 prefers MIT).

Output: a reusable artefact, independent of every model decision, that is also the
stage-2 table and the stage-1 seed.

### Phase 1 — the respelling baseline (no model)

Populate `PRONUNCIATION_OVERRIDES` with English respellings for the ~40 terms that
actually occur, generate a few turns, listen.

This is an afternoon's work and it exists to produce **the number the model chain has
to beat**. It is not expected to be the answer — see the 2026-06-09 failure above,
and note it cannot fix guttural ח at all, since English orthography has no ח. Expect
it to help the institutional terms and fail on exactly the cases the note cares about.

**Decision gate:** if the baseline is good enough, stop. That would be the cheapest
possible outcome and it should be checked before anything is trained.

### Phase 2 — the detector

1. Annotate `English-Hebrew-Mixed-Sentences` properly (DR-2). Its labels were
   produced by substring search — 114 of 474 point inside an unrelated English word,
   leaving the real Hebrew term unlabelled — and a further 86 candidate spans and 42
   null-label records need a human. **Under way in
   [Hebrew-Latin-Token-Classifier](https://github.com/danielrosehill/Hebrew-Latin-Token-Classifier)**;
   242 review tasks queued.
2. Mine in-domain examples from the MWP corpus by sampling **around lexicon hits**,
   not at random — 18.5M words that are almost all negatives (DR-3).
3. Generate colloquial-register positives synthetically; the register is near-absent
   from MWP (*makolet* 1 occurrence, *balagan* 1, *beseder* 0) (DR-4, DR-5).
4. Fine-tune `xlm-roberta-base` for token classification, EnTaCs recipe.
5. Evaluate on held-out MWP turns against the lexicon-only baseline.

**Decision gate (FR-6, acceptance):** ship if it beats lexicon lookup on held-out
turns. Publishing it would fill a real, specific gap — no `heb_Latn` classifier
exists anywhere.

### Phase 3 — Hebrew segments end to end

Swap to `ChatterboxMultilingualTTS`, wire stages 2–4, generate one full episode both
ways, listen.

**Decision gate:** only ships if the A/B is an improvement over phase 1's baseline.
The voice note is explicit that the full chain may not justify its cost, and that
judgement stays with the listening test.

## 6. Decisions taken in this document

| # | Decision | Because |
| --- | --- | --- |
| D-1 | Lexicon is primary for stage 2; TaatikNet is fallback | Terms are a closed high-frequency set; every model is word-level and the hard cases are multi-word |
| D-2 | Stage 3 is deterministic code, not a model | Given spans and Hebrew forms, segment construction is string work |
| D-3 | `xlm-roberta-base` token classification for the detector | The EnTaCs recipe is the closest published template with a reported number |
| D-4 | Phase 1 respelling baseline runs before any training | It is cheap and it defines what the model chain has to beat |
| D-5 | Lexicon sourced from kaikki.org, not TaatikNet's CSV | TaatikNet's data is CC BY-SA 3.0; share-alike would constrain publication |
| D-6 | Unknown spans stay English | Failing to the current behaviour is safe; FR-7 weights precision |

## 7. Still open

| # | Question | Blocks |
| --- | --- | --- |
| Q-1 | Does Chatterbox `he` accept unvocalised Hebrew script, and how does it resolve ambiguity without niqqud (`בטוח` vs `בטח`)? | Phase 3. **Test this first — it is one call and it can invalidate the design** |
| Q-2 | How much does voice identity drift between an `en` and a `he` segment from the same conditionals? | Phase 3 |
| Q-3 | How much padding at segment joins before they stop sounding like cuts? | Phase 3, by listening (FR-15) |
| Q-4 | Does a Python transliteration package exist on PyPI? Unverified — pypi.org returned a 403/JS wall on both search and direct fetch | Phase 0, minor |
| Q-5 | Should place names and proper nouns (*Tel Aviv*, *Netanyahu*) be classified as Hebrew? They are already pronounced acceptably (FR-5) | Phase 2 labelling policy |
| Q-6 | Are brand names Hebrew? The dataset's null-label records include *10 Bis*, *Zol Stock* — a category the lexicon does not currently model | Phase 2 labelling policy |

**Q-1 is the cheapest and the most dangerous.** If Chatterbox's `he` voice cannot
render unvocalised modern Hebrew acceptably, phases 2 and 3 have no consumer and the
project reduces to the lexicon plus the baseline. Run it before phase 2.
