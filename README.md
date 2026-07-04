# KrishiKotha — Q&A Pipeline

This module handles grounded question-answering for KrishiKotha, an AI assistant 
for Bangladeshi farmers. It takes a farmer's question and a set of real 
agricultural reference documents, and returns an accurate, honest answer in Bangla.

## What it does

- Answers farmer questions **only** using provided reference material — no guessing 
  from general AI knowledge
- Asks a clarifying question when symptoms are ambiguous, instead of guessing wrong
- Honestly declines when a topic isn't covered by our documents, and suggests 
  contacting a local agricultural officer

## Setup

1. Install dependencies

2. Create a `.env` file in this folder with your OpenAI API key

3. Run:
```bash
   python qa_pipeline.py
```

## How it works

`get_answer(question, reference_docs)` sends the farmer's question plus the 
reference material to GPT-4o with a prompt that enforces three behaviors:

1. **Clear match** → gives a direct, confident diagnosis and treatment
2. **Ambiguous match** → asks ONE clarifying question to narrow it down
3. **No match at all** → honestly says it doesn't have reliable information

Temperature is set to `0.2` to keep answers consistent across repeated calls.

## Reference documents

Located in this folder, sourced from DAE/BARI/BRRI advisories:

| Crop  | Coverage |
|-------|----------|
| Rice  | Blast, Sheath blight, Seedling blight, Tungro |
| Jute  | Anthracnose, Black band, Stem rot, Dieback, Soft rot, Nematodes |
| Beans | Anthracnose, Pod borer, Aphid |
| Lemon | Canker |

**Known gaps:** Potato has no documents yet. Mustard (Shorisha.txt) has a corrupted 
encoding issue and needs to be re-extracted from source before use.

## Integration notes for the team

- `get_answer()` is the function to import for the main app — takes two strings, 
  returns one string (the answer in Bangla)
- If a farmer's question triggers a clarifying question, the app should let them 
  respond, then re-call `get_answer()` with the original question + their follow-up 
  combined into one string
- All reference docs are currently combined into a single string passed to every 
  call — no per-crop filtering yet (fine at current scale, may need optimization 
  if we add many more crops)
