# Photo Diagnosis — Track 2 (Day 2)

Person C's Day 2 task: turn the Day 1 go/no-go prototype into a reliable,
hand-off-ready function by adding document grounding and crop pre-selection,
then proving it's actually better than the Day 1 baseline.

## What changed since Day 1

| | Day 1 (`test.py`) | Day 2 (`diagnose.py`) |
|---|---|---|
| Crop | Model guesses it | Passed in as a known fact (from a UI dropdown) |
| Knowledge | General model knowledge only | Grounded in real disease reference docs |
| Output | Loose JSON test | Clean `diagnose_photo()` function ready for `app.py` |

## Setup (same as Day 1)

```bash
pip install -r requirements.txt
cp .env.example .env
# paste your real OpenAI key into .env
```

## Files

- `documents/` — one `.txt` per crop (`rice.txt`, `potato.txt`, `jute.txt`)
  with disease symptoms. **Currently placeholders — replace with Person
  A's real cleaned DAE/BARI/BRRI content the moment it's ready.** Keep
  the same filename-per-crop pattern so `diagnose.py` finds them
  automatically.
- `diagnose.py` — the core module. Exposes `diagnose_photo(image_path, crop)`,
  the exact function to hand off for `app.py`.
- `compare_day2.py` — re-runs your Day 1 test photos through the new
  grounded pipeline and logs results to `evaluation_day2.csv`, so you can
  compare against Day 1's `evaluation.csv` and confirm things actually
  improved.
- `test.py`, `outputs/`, `evaluation.csv` — kept from Day 1 as your
  baseline reference.

## Step-by-step for today

1. **Confirm go/no-go is still GO.** Check Day 1's `evaluation.csv`. If
   results were mostly "no" with confident wrong answers, stop here and
   tell the team to cut the feature — don't keep refining something
   that's fundamentally unreliable.

2. **Swap in real documents.** As soon as Person A hands off cleaned
   text, replace the placeholder content in `documents/rice.txt`,
   `documents/potato.txt`, `documents/jute.txt` (or add more crop files
   if scope expanded).

3. **Update `compare_day2.py`'s `TEST_SET`** to point at your actual Day 1
   test image filenames and their known crop.

4. **Run the comparison:**
   ```bash
   python compare_day2.py
   ```

5. **Score it.** Open `evaluation_day2.csv` and fill in
   `correct_diagnosis` (yes/partial/no) by eye, same as Day 1. Then compare:
   - Did the "yes" rate go up vs. Day 1's `evaluation.csv`?
   - Is `grounded_in_docs` coming back `true` where you'd expect (i.e. is
     it actually using the reference material, not ignoring it)?
   - Is confidence more honestly calibrated (lower on genuinely unclear
     photos, not falsely confident)?

6. **Hand off `diagnose_photo()`.** Once you're satisfied it's an
   improvement, this function is done — whoever builds `app.py` calls:
   ```python
   from diagnose import diagnose_photo
   result = diagnose_photo(uploaded_image_path, selected_crop)
   ```
   No further changes needed from your side unless bugs turn up during
   Day 3 integration.

## Quick manual test (single image, no CSV logging)

```bash
python diagnose.py images/rice_blast_1.jpg rice
```

Prints the full JSON result to the terminal — useful for fast iteration
while tuning the prompt in `_build_prompt()`.
