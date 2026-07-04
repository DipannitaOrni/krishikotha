# Photo Diagnosis — Go/No-Go Test (KrishiKotha)

Person C's Day 1 task: test whether GPT-4o's vision capability can reasonably
diagnose crop diseases from photos, in Bangla. Result decides whether the
photo feature stays in scope for the rest of the hackathon.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Copy the env template and add your real API key:
   ```bash
   cp .env.example .env
   ```
   Then open `.env` and paste your OpenAI API key from
   platform.openai.com/api-keys.

3. Add 2–3 test photos to the `images/` folder. Aim for:
   - 1 clear/textbook example of a known disease
   - 1–2 harder/realistic cases (blurry, early-stage, or ambiguous)
   - Cover your chosen crops (rice, potato, jute)

## Run

```bash
python test.py
```

This will:
- Send each image to GPT-4o with a structured Bangla-diagnosis prompt
- Print a quick summary to the terminal
- Save the full raw response for each image to `outputs/`
- Append a row per image to `evaluation.csv`

## After running

Open `evaluation.csv` and manually fill in two columns by reading each
response:
- **correct_diagnosis**: yes / partial / no — does the diagnosis match
  what the photo actually shows?
- **bangla_quality**: good / ok / broken — is the Bangla natural, or
  stiff/awkward?

## Go/No-Go criteria

**GO** if, across your test photos:
- Crop identification is consistently correct
- Diagnosis is correct or close on the clear photo, reasonably hedged
  (low confidence, honest "not sure") on hard ones
- Bangla output is usable without heavy editing
- Response time is workable for a live demo (a few seconds, not 30+)

**NO-GO** (or flag as high-risk) if:
- The model is confidently wrong on diagnoses — this is worse than no
  feature at all, since a wrong diagnosis stated confidently could lead
  a farmer to the wrong action
- It only works on the obvious textbook case
- Bangla output needs heavy fixing to be usable

Report the result to the team at end-of-day sync, along with the filled
`evaluation.csv`. If GO, hand `test.py`'s image-encoding + API-call logic
to Person B as the seed for the real photo → diagnosis pipeline on Day 2.

## Files

- `images/` — test crop photos (not committed if using real farmer photos
  with any privacy concern — check before pushing to GitHub)
- `outputs/` — raw JSON response per image, for debugging/reference
- `test.py` — the test script
- `evaluation.csv` — auto-generated summary log, manually annotated after
- `.env.example` — template for your API key (real `.env` should be
  gitignored)
