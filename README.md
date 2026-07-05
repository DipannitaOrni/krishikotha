# KrishiKotha — Q&A Pipeline

This module handles grounded question-answering for KrishiKotha, an AI assistant
for Bangladeshi farmers. It takes a farmer's question, routes it to the right
crop's reference material, and returns an accurate, honest answer in Bangla.

## What it does

- Answers farmer questions **only** using provided reference material — no guessing
  from general AI knowledge
- Automatically detects which crop a question is about (via keyword matching) and
  narrows the reference material to just that crop, instead of always sending all
  ~10 crops' worth of text
- Asks a clarifying question when symptoms are ambiguous across two or more
  diseases, instead of guessing wrong
- Honestly declines when a topic isn't covered by our documents, and suggests
  contacting a local agricultural officer
- Never invents symptoms for a disease that's only named (not described) in the
  reference material
- Never borrows treatment steps from a different, neighboring disease when the
  matched disease's own treatment section is genuinely empty

## Setup

1. Install dependencies (`openai`, `python-dotenv`)
2. Create a `.env` file in this folder with:
   ```
   OPENAI_API_KEY=your_key_here
   ```
3. Run:
   ```bash
   python qa_pipeline_restructured.py
   ```
   This runs the built-in test questions at the bottom of the file.

## How it works

- `load_crop_docs()` — loads each crop's `.txt` reference files into a dict,
  `{crop_name: combined_text}`. Call once at app startup and reuse the result.
- `identify_crops(question)` — returns which crop(s) a question's keywords match.
- `answer_question(question, crop_docs, combined_docs)` — **the function to
  import for the main app.** Routes the question:
  - Exactly one crop matched → passes only that crop's docs to the model
  - Zero or 2+ crops matched → falls back to all crops combined, so the model
    can still ask "which crop do you mean?" or handle a mixed-crop question
- `get_answer(question, reference_docs)` — the low-level function that actually
  calls GPT-4o with the grounded prompt. Called internally by `answer_question()`;
  don't call this directly from the app unless you're deliberately bypassing crop
  routing (e.g. for testing).

Temperature is set to `0.0` (as of 2026-07-06) to minimize run-to-run flip-flopping
on ambiguous cases — testing at 0.2 showed real instability (e.g. the same
ambiguous question sometimes triggering a clarifying question and sometimes not).
Note this doesn't guarantee perfect determinism with this API, but it removes
sampling as a source of instability.

On API failure (network issue, rate limit, timeout), `get_answer()` returns a
graceful Bangla fallback message instead of raising, so a single failed call
doesn't crash a live demo.

## Reference documents

Located in this folder, sourced from DAE/BARI/BRRI/CIMMYT advisories and one
PlantwisePlus knowledge-bank fact sheet. Each crop is a separate entry in
`CROP_FILES` (see `qa_pipeline_restructured.py`):

| Crop    | Coverage |
|---------|----------|
| Rice    | Sheath blight (খোলপোড়া), Seedling blight (চারাপোড়া), Tungro virus, Blast (leaf/node/neck) |
| Jute    | Anthracnose, Black band, Stem rot, Dieback, Soft rot, Root-knot nematode |
| Beans   | Anthracnose, Pod borer, Aphid |
| Lemon   | Canker |
| Mustard | Alternaria blight, Aphid, Orobanche (parasitic plant) |
| Potato  | Late blight, Early blight, Bacterial wilt/brown rot, Scab, Stem canker/scurf, Leaf roll virus, Mosaic, Yellow disease, Dry rot, Soft rot, Cutworm, Tuber moth |
| Tomato  | Fusarium wilt, Bacterial wilt |
| Wheat   | Blast, Leaf spot/spot blotch, Stem/black rust, Powdery mildew |
| Tobacco | Black shank, Fusarium wilt, Tobacco mosaic virus, Frogeye leaf spot, Blue mold, Bacterial wilt |
| Maize   | Fall armyworm (FAW), Turcicum leaf blight, Common rust, Downy mildew, BLSB, Stalk rot |

**Known gaps / things to double check before shipping:**
- A few diseases are named in source docs but have no symptom description at all
  (e.g. jute's Cercospora leaf spot, target spot, bacterial leaf blight, mosaic
  virus) — the pipeline is designed to honestly decline on these rather than
  guess, but it's worth spot-checking with real user questions.
- If you add new crops whose disease names/documents overlap or duplicate across
  multiple source files (like wheat blast or maize FAW currently do), retest the
  ambiguous-symptom cases specifically — duplication across files has caused
  candidate-list instability before and is worth a regression check each time.

## Eval harness

`run_eval.py` runs a structured test suite (coverage per disease, deliberate
ambiguity cases, "named but undescribed" grounding-stress cases, adversarial/messy
input, and repeated consistency checks) and appends results to a timestamped CSV
for manual scoring. Run with:
```bash
python run_eval.py
```

## Integration notes for the team

- Import `answer_question()`, not `get_answer()`, for the main app — it handles
  crop routing; `get_answer()` alone does not.
- `answer_question()` takes `(question, crop_docs, combined_docs)` and returns one
  string (the answer in Bangla). Load `crop_docs` once via `load_crop_docs()` at
  startup, and build `combined_docs` once too (see `__main__` block for the
  pattern) — don't reload from disk on every call.
- If a farmer's question triggers a clarifying question, the app should let them
  respond, then re-call `answer_question()` with the original question + their
  follow-up combined into one string.
- Per-crop filtering is already implemented (see "How it works" above) — this is
  not a future optimization, it's live now.
