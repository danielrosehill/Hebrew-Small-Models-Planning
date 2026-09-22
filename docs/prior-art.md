# Prior art

Surveyed 2026-09-22. The voice note asks two questions — *does the classifier
already exist?* and *does an open-weight Latin→Hebrew model exist?* This answers
both.

**Short answers: no, and yes-but-word-level.**

Items are marked CONFIRMED (the page or API was read) or INFERRED (search snippet
only).

---

## Stage 1 — detecting Hebrew words written in Latin script

### Nothing off the shelf does this. Build it.

The relevant label would be something like `heb_Latn` — Hebrew *language*, Latin
*script*. It does not exist in any language-ID resource found.

| System | Hebrew? | Romanized Hebrew? | Token-level? | Evidence |
| --- | --- | --- | --- | --- |
| **GlotLID v3** | `heb_Hebr` only | **No `heb_Latn`** | No — sentence-level fastText | CONFIRMED: read `languages-v3.md`, one `heb_*` label at row 620 |
| **fastText `lid.176`** | `__label__he` | No — trained on Hebrew-script Wikipedia/Tatoeba | No | INFERRED |
| **NLLB `lid218e`** | `heb_Hebr` | No | No | INFERRED. CC-BY-NC 4.0 |
| **`papluca/xlm-roberta-base-language-detection`** | **Hebrew is not among its 20 languages at all** | n/a | No | CONFIRMED: read the model card |
| **CodeSwitch-LID** (`sagorsarker/codeswitch-*-lid-lince`) | No | n/a | **Yes, genuinely token-level** | CONFIRMED via HF API: only `hineng`, `spaeng`, `nepeng` exist |
| **LinCE benchmark** | No | n/a | Yes | INFERRED — covers spa-eng, nep-eng, hin-eng, MSA-EGY |

Note the omission is **specific, not structural**: GlotLID v3 *does* carry romanized
labels for other languages — `arb_Latn`, `hin_Latn`, `ben_Latn`, `kas_Latn`. Hebrew
simply was not done.

**No Hebrew-English code-switching corpus was found either**, token-tagged or
otherwise. This is what makes `danielrosehill/English-Hebrew-Mixed-Sentences`
unusually valuable — see `docs/reference/training-data.md`.

### The recipe to copy

**EnTaCs** (English-Tamil code-switching, arXiv 2603.26587) is the closest published
template and it is deliberately small: ~500 utterances, ~3,500 tokens, three labels
(`en` / romanized-L2 / `na`), CoNLL format, fine-tune `xlm-roberta-base` for token
classification.

Reported: **macro-F1 0.844, romanized class F1 0.638.**

Treat 0.64 as the realistic expectation for the romanized class from a small
hand-annotated set, not 0.9. That is still useful — FR-6 explicitly accepts an
imperfect classifier — but it should be the number in mind when deciding whether the
downstream stages are worth building.

---

## Stage 2 — Latin script → Hebrew script

### What the task is called

Naming matters more than usual here, because ~95% of published Hebrew
transliteration work runs the other direction.

| Term | Useful? |
| --- | --- |
| **reverse transliteration** | **Yes — the precise term for this direction.** iiWAS'19, "Reverse-Transliteration of Hebrew script for Entity Disambiguation" |
| **back-transliteration** | Yes, but carries a trap: in the NEWS shared-task literature, "Hebrew→English back-transliteration" means restoring an *English* name written in Hebrew — the opposite of this |
| machine transliteration | Umbrella term, very broad |
| de-romanization / romanization reversal / transliteration restoration | **Not established terminology.** No useful results |

Search by artefact as well as by task name — *"Hebrew Wiktionary transliteration
dataset"*, *"ByT5 Hebrew transliteration"*.

### TaatikNet — the only purpose-built model in existence

| | |
| --- | --- |
| Model | <https://huggingface.co/malper/taatiknet> |
| Code | <https://github.com/morrisalp/taatiknet> |
| Demo | <https://huggingface.co/spaces/malper/taatiknet> |
| Architecture | **ByT5-small fine-tune** — byte-level, tokenizer-free |
| Open weights | **Yes** |
| Licence | **CC BY-SA 3.0** per the NNLP-IL index (CONFIRMED there). The HF repo itself carries **no licence field** — `cardData` is only `{"language":["he"]}` (CONFIRMED via API) |
| Last modified | **2023-06-25.** Created 2023-06-23. Untouched for ~3.25 years |
| Adoption | 73 downloads all-time, 1 like |
| Direction | **Bidirectional** — trained both ways, with nikkud and stress marks randomly dropped, so it accepts unvocalised Latin input |
| Training data | `data/he_transliterations.csv` — ~15K Hebrew words with nikkud + Latin forms, scraped from **Hebrew Wiktionary, mid-2023** |

**Two traps, both confirmed:**

- `morrisalp/taatiknet` on Hugging Face returns **401 / does not exist**. That is the
  GitHub org name. The HF repo is **`malper/taatiknet`**.
- **It is word-level, not phrase-level.** The README instructs you to split on
  whitespace and batch the words yourself; training data was explicitly split into
  single words. `Bituach Leumi` must be two calls. Also raise `max_length` or the
  output truncates.

The author's own caveat on the training data: transliterations are inconsistent,
stress is often wrong, spelling conventions are mixed. Expect it to handle *Shabbat*
and to be shaky on institutional multi-word terms — exactly the terms this project
cares about most.

**Verdict: FR-9 is satisfied.** An open-weight model exists. But it is small, stale,
word-level and barely used, so it is a component, not an answer.

### Nothing else exists, and this was checked exhaustively

- HF model search `transliteration`, 100 results (CONFIRMED): Hindi, Nepali,
  Malayalam, Bengali, Urdu, Punjabi, Sinhala, Dhivehi, Darija, Sumerian, Akkadian,
  Tibetan, Sanskrit — **zero Hebrew**. The `hi`/`hin` entries are *Hindi*, an easy
  misread.
- HF model search `hebrew`, 100 results (CONFIRMED): LLMs, ASR, NER, sentiment,
  punctuation. **No transliteration, romanization or nikud model.**
- HF dataset search `transliteration`, ~49 results (CONFIRMED): **zero Hebrew.**
- **NNLP-IL/Hebrew-Resources**, the canonical Hebrew NLP index (CONFIRMED, read the
  raw `.rst`): **TaatikNet is the only transliteration entry in the entire list.**
  This is the strongest single piece of evidence that nothing else exists.

**A search trap worth knowing:** HF search matches on repo-id substrings, so the
multi-word query `hebrew transliteration` returns `[]` — an empty list, not an
error. Do not read that as "nothing exists"; search single terms.

### Rule-based options

**ICU / CLDR `Latin-Hebrew` genuinely ships.** CONFIRMED by reading
`common/transforms/Hebrew-Latin.xml`:

```xml
<transform source="Hebr" target="Latn" direction="both"
           alias="Hebrew-Latin und-Latn-t-und-hebr"
           backwardAlias="Latin-Hebrew und-Hebr-t-und-latn">
```

`direction="both"` plus the explicit `backwardAlias` means
`Transliterator.getInstance("Latin-Hebrew")` — or `icu.Transliterator.createInstance`
via PyICU — is a real registered transform.

**But it will not do what you want unaided.** It is script-level and
round-trip-oriented: its Latin side uses ISO-259-style diacritics (ḥ, š, ṣ, ʾ), so
English ad-hoc spellings like *Shabbat* or *Bituach* will not round-trip. Use it as a
**candidate generator**, then filter against a Hebrew wordlist. Minimal/ICU-lite
builds strip transform data — check `Transliterator.getAvailableIDs()` first.

Others:

- **`hebrew-transliteration`** (npm, v2.11.0, MIT, Node ≥20.19, actively maintained)
  is **Hebrew→Latin only** and Biblical-Hebrew oriented. No reverse function.
  CONFIRMED.
- **gimeltra** — consonant transliteration across 24 Semitic scripts with Latin as
  the pivot, so Latin→Hebrew is mechanically available. Drops all vowels,
  non-standard scheme. Crude candidate generator at best. INFERRED.
- Standards tables — ISO 259-2/259-3, DIN 31636, ALA-LC, BGN/PCGN 2018, Academy of
  the Hebrew Language 2007. All designed for the forward direction; reversing them
  is many-to-many. INFERRED.
- **Sideways Transliteration** (arXiv 1911.12022) describes the best
  accuracy-per-effort hybrid for a closed vocabulary: letter-substitution table →
  candidate list → Hebrew n-gram LM rerank → lexicon lookup with edit distance.

### Hebrew NLP resources that are *not* substitutes

| Resource | Transliteration? | Note |
| --- | --- | --- |
| **DICTA** (`dicta-il`) — DictaBERT, Nakdan, DictaLM 2.0, Dicta-LM 3.0 (24B, open weights) | **No** | Nakdan adds nikkud to *Hebrew-script* input; it cannot consume Latin script |
| HeBERT / AlephBERT / AlephBERTGimmel | **No** | Hebrew-script encoders, no transliteration head |
| Hebrew-Gemma-11B / Hebrew-Mistral-7B (yam-peleg) | No endpoint | Open weights; could be *prompted*. Unmeasured — you would be the one measuring it |
| **Phonikud / ReNikud / Conikud** (2025–26, INTERSPEECH 2026) | **No** | Hebrew script → **IPA**. Wrong direction, wrong target alphabet, not reversible. The newest active work in the area — note the field has moved to G2P/IPA, not romanization |
| MILA morphological analyser (Technion) | Emits a `transliteration` attribute | GPLv3, non-commercial, **listed as down**. Forward direction |

---

## Lexicon sources

DR-6 wants a Latin↔Hebrew term list. Ranked:

1. **TaatikNet's `data/he_transliterations.csv`** — ~15K pairs from Hebrew Wiktionary,
   mid-2023, CC BY-SA. The only ready-made wordlist. CONFIRMED.
2. **Wiktionary via kaikki.org / wiktextract** — the English Wiktionary extraction
   carries a `roman` field on Hebrew examples, translations and linkages, downloadable
   per-language as JSONL (full dump ~23.5 GB, ~2.7 GB gz). Same source as TaatikNet's
   CSV, better extractor, three years newer — **the best route to a larger, fresher
   lexicon.** <https://kaikki.org/dictionary/rawdata.html> INFERRED.
3. **NETransliteration-COLING2018** — English↔Hebrew personal-name dictionaries mined
   from Wikidata. Names only, but real public parallel data. INFERRED.
4. **Sefaria** — no transliteration table, but the mapping is implicit in
   `/api/terms/:term` title groups and index `titleVariants`. No auth. Vocabulary is
   skewed liturgical/Talmudic and conventions will not match. INFERRED.

---

## What could not be found

- Any Latin→Hebrew model on Hugging Face **other than TaatikNet**.
- Any Hebrew transliteration model or dataset created **after mid-2023**.
- Any **`heb_Latn`** language-ID label, anywhere.
- Any **Hebrew-English code-switching corpus**.
- Public code or data for the iiWAS'19 reverse-transliteration paper — paywalled,
  no artifact badge.
- **Multi-word phrase handling anywhere.** Every artefact found is word-level or
  character-level. `Bituach Leumi` → `ביטוח לאומי` **as a single unit is unsolved by
  any off-the-shelf component.**

One verification gap, stated rather than papered over: **PyPI could not be searched.**
`pypi.org` returned a 403 / JS wall on both search and direct project fetch. Whether a
Python `hebrew-transliteration` package exists is **unverified, not proven absent**.
Worth one follow-up check.

---

## What this changes

1. **The classifier must be built.** The voice note suspected this; it is confirmed.
   No component tags romanized Hebrew tokens.
2. **Stage 2 should be a lexicon first, a model second** — inverting the note's
   framing. The terms that actually occur are a closed, small, high-frequency set of
   institutional names, and every available model is word-level while the hard cases
   are multi-word.
3. **TaatikNet becomes the fallback for out-of-lexicon words**, not the primary path.
4. **Publishing a `heb_Latn` token classifier and an English-Hebrew code-switching
   corpus would be genuinely new.** Both gaps are real and specific. That materially
   strengthens the note's instinct that the classifier is "worth having" beyond the
   podcast.
5. TaatikNet's **CC BY-SA 3.0** is share-alike. If its weights or CSV are used in a
   derivative, that constrains the licence of what is published — which matters given
   DR-7 prefers MIT. Building the lexicon from kaikki.org instead keeps the options
   open.

## Sources

[TaatikNet GitHub](https://github.com/morrisalp/taatiknet) ·
[malper/taatiknet](https://huggingface.co/malper/taatiknet) ·
[CLDR Hebrew-Latin.xml](https://raw.githubusercontent.com/unicode-org/cldr/main/common/transforms/Hebrew-Latin.xml) ·
[CLDR Latin-Hebrew chart](https://www.unicode.org/cldr/cldr-aux/charts/26/transforms/Latin-Hebrew.html) ·
[NNLP-IL/Hebrew-Resources](https://github.com/NNLP-IL/Hebrew-Resources/blob/master/models_tools_services.rst) ·
[charlesLoder/hebrew-transliteration](https://github.com/charlesLoder/hebrew-transliteration) ·
[GlotLID](https://github.com/cisnlp/GlotLID) ·
[papluca/xlm-roberta-base-language-detection](https://huggingface.co/papluca/xlm-roberta-base-language-detection) ·
[iiWAS'19 reverse transliteration](https://dl.acm.org/doi/10.1145/3366030.3366099) ·
[Sideways Transliteration (arXiv 1911.12022)](https://arxiv.org/pdf/1911.12022) ·
[NETransliteration-COLING2018](https://github.com/steveash/NETransliteration-COLING2018) ·
[Phonikud](https://github.com/thewh1teagle/phonikud) ·
[LinCE](https://arxiv.org/pdf/2005.04322) ·
[EnTaCs (arXiv 2603.26587)](https://arxiv.org/pdf/2603.26587) ·
[kaikki.org raw data](https://kaikki.org/dictionary/rawdata.html) ·
[Sefaria API](https://developers.sefaria.org/reference/getting-started)
