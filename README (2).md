# KrishiKotha — Agentic Follow-up Questioning

## What this is

KrishiKotha helps Bangladeshi farmers diagnose crop diseases via photo, voice,
and text, in Bangla. This part of the project adds **agentic follow-up
questioning** to the photo diagnosis pipeline: instead of always giving a
one-shot diagnosis from a single photo, the system recognizes when it isn't
confident enough to commit, asks the farmer ONE clarifying question by voice,
and folds their spoken answer into a second, better-grounded diagnosis.

This demonstrates reasoning under uncertainty (deciding *when* to ask vs.
just answering) rather than a single fixed API call.

## How it works

```
Photo + crop  →  diagnose_photo()  →  confident?
                                         │
                         ┌───────────────┴───────────────┐
                        yes                              no
                         │                                │
                   show diagnosis          generate_followup_question()
                   speak advice                    │
                                              speak() the question
                                                     │
                                          farmer answers by voice
                                                     │
                                                listen() transcribes
                                                     │
                                        rediagnose_with_answer()
                                                     │
                                        final grounded diagnosis
                                            speak() the advice
```

**Trigger condition** (`needs_followup()` in `followup_engine.py`):
- `confidence` is `"low"` or `"medium"` (string, not numeric — `diagnose_photo()`
  returns a categorical confidence, not a float), **or**
- `matched_diseases` has 2 or more candidates (genuine ambiguity from the
  photo alone)

## Files

| File | Role |
|---|---|
| `Image/diagnose.py` | First-pass photo diagnosis (`diagnose_photo()`) — Person C's pipeline |
| `Image/crop_documents.py` | Shared crop reference document loading |
| `Voice/voice_functions.py` | `listen()` (Bangla ASR) and `speak()` (Bangla TTS) — Person A's pipeline |
| `Text/qa_pipeline_restructured.py` | Typed/spoken text Q&A pipeline (`answer_question()`) — Person B's pipeline |
| `followup_engine.py` | **This feature.** Wraps `diagnose_photo()` with the confidence-gated follow-up branch |
| `combined_app.py` | Streamlit app with three modes: photo diagnosis (+ follow-up), voice Q&A, text Q&A |

## Setup

### 1. Python environment
```powershell
python -m venv krishikotha_env
krishikotha_env\Scripts\Activate.ps1
pip install streamlit openai python-dotenv transformers torch torchvision gtts
```
(If PowerShell blocks the activation script: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`)

### 2. ffmpeg (required for voice recording — converts browser audio to 16kHz mono WAV)
```powershell
winget install ffmpeg
```
Close and reopen your terminal (and VS Code, if using its integrated terminal)
after installing, so PATH changes take effect. Verify with `ffmpeg -version`.

### 3. `.env` file
Place a `.env` file at the **repo root** (not just inside a subfolder) containing:
```
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o
```
`load_dotenv()` is called from multiple modules but only needs to succeed
once per process — as long as `.env` is discoverable from wherever you launch
Streamlit (the root), every module sees the key.

### 4. Path fixes (required — see "Known gotchas" below)
Both of these MUST resolve paths relative to their own file location, not
the current working directory, since `combined_app.py` runs from the repo
root while the original scripts were written assuming they'd run from
inside their own subfolder:

**`Image/crop_documents.py`:**
```python
from pathlib import Path
DOCUMENTS_DIR = Path(__file__).parent / "documents"
```

**`Text/qa_pipeline_restructured.py`:**
```python
from pathlib import Path
TEXT_DIR = Path(__file__).parent

def load_doc(filepath):
    full_path = TEXT_DIR / filepath
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"WARNING: File not found — {full_path}")
        return ""
```

## Running

```powershell
streamlit run combined_app.py
```
Run from the **repo root** (same folder as `followup_engine.py`, `Image/`,
`Voice/`, `Text/`).

## Known gotchas (things that will bite you if skipped)

- **Relative paths break depending on where you run from.** Both crop-doc
  loaders in this repo were originally written assuming they'd run from
  inside their own subfolder. Running from root (required for
  `combined_app.py` to see all three tracks) breaks that unless the fixes
  above are applied. Symptom: `diagnose_photo()` or `answer_question()`
  silently says "no information for this crop" even though the docs exist.
- **`transformers` will print a wall of harmless `ModuleNotFoundError:
  torchvision` warnings** on first run — this is Streamlit's file watcher
  introspecting every vision model class in the library, most of which
  KrishiKotha doesn't use. Installing `torchvision` (see setup) silences it;
  it does not indicate anything is broken.
- **`answer_question()` (Text pipeline) is stateless per call.** It has no
  memory of previous turns on its own. `combined_app.py`'s Text/Voice modes
  work around this by resending the *entire* conversation so far as one
  combined string on every turn — if you call `answer_question()` directly
  elsewhere, remember to do the same or multi-turn context will be lost
  (the model will ask "which crop?" again even after you already answered).
- **ffmpeg PATH changes need a fresh terminal/IDE session** — installing it
  while a terminal is already open won't be picked up until you close and
  reopen (VS Code's integrated terminal inherits PATH from when VS Code
  itself launched).

## Testing the follow-up branch

To confirm the branch actually fires without needing a naturally ambiguous
photo, temporarily force it in `followup_engine.py`:
```python
def needs_followup(result: dict) -> bool:
    return True  # TEMPORARY — revert after testing
```
Then verify all four checkpoints:
1. A sensible, farmer-answerable Bangla question is generated and spoken
2. The second recorder appears and accepts an answer
3. The answer transcribes correctly and `rediagnose_with_answer()` runs without error
4. The final result is labeled "with follow-up" and genuinely incorporates
   the farmer's answer (check the `reasoning_english` field in Dev info —
   it should reference the specific detail the farmer gave, not just repeat
   the first-pass reasoning)

Revert to the real trigger condition (`return low_conf or ambiguous`) before
using real test photos.
