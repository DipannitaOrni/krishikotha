"""
KrishiKotha — Agentic Follow-up Questioning
--------------------------------------------
Wraps diagnose_photo() with a conditional second turn: if the first-pass
diagnosis is ambiguous (confidence != "high", or 2+ matched_diseases),
ask the farmer ONE clarifying question by voice, then re-diagnose with
their answer folded into the prompt as extra context.

Reuses:
  - diagnose_photo() from diagnose.py  (Person C's image pipeline)
  - listen() / speak() from voice_functions.py  (Person A's voice pipeline)

This file does NOT reimplement either — it only adds the reasoning branch
that decides when to loop back for more info before committing.

IMPORTANT: crop_documents.py (used by diagnose.py) loads reference files
from a "documents" folder using a path relative to the CURRENT WORKING
DIRECTORY at runtime, not relative to this file. If you run this script
from the repo root (not from inside Image/), fix that in
Image/crop_documents.py first:

    from pathlib import Path
    DOCUMENTS_DIR = Path(__file__).parent / "documents"

Otherwise every crop doc load will silently return "" and diagnose_photo()
will report "no reference document loaded" for every crop.
"""

import sys
import os
import json
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

sys.path.append(str(Path(__file__).parent / "Image"))
sys.path.append(str(Path(__file__).parent / "Voice"))

from diagnose import diagnose_photo, _get_crop_docs
from voice_functions import listen, speak

load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=API_KEY)
    return _client


# ---------------------------------------------------------------------
# Step 1: decide whether we need to ask a follow-up at all
# ---------------------------------------------------------------------

def needs_followup(result: dict) -> bool:
    """
    Trigger condition. Since diagnose_photo() gives a STRING confidence
    (not a float), the threshold check is categorical, not numeric.
    """
    low_conf = result.get("confidence", "").lower() in ("low", "medium")
    ambiguous = len(result.get("matched_diseases", [])) >= 2
    return low_conf or ambiguous


# ---------------------------------------------------------------------
# Step 2: generate ONE clarifying question in Bangla
# ---------------------------------------------------------------------

FOLLOWUP_PROMPT_TEMPLATE = """You are helping a Bangladeshi farmer via a
voice assistant. Your first-pass photo diagnosis was ambiguous.

Candidate diseases: {matched_diseases}
Your internal reasoning: {reasoning_english}
What you already told the farmer: {diagnosis_bangla}

Write EXACTLY ONE short, simple clarifying question in Bangla that a
farmer (who may not read well) could answer easily out loud — e.g. about
which part of the plant is affected, how many days it's been happening,
or a visible detail that distinguishes the candidates.

Return ONLY the Bangla question text. No JSON, no English, no quotes."""


def generate_followup_question(result: dict) -> str:
    client = _get_client()
    prompt = FOLLOWUP_PROMPT_TEMPLATE.format(
        matched_diseases=result.get("matched_diseases", []),
        reasoning_english=result.get("reasoning_english", ""),
        diagnosis_bangla=result.get("diagnosis_bangla", ""),
    )
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=120,
    )
    return response.choices[0].message.content.strip()


# ---------------------------------------------------------------------
# Step 3: re-diagnose with the farmer's spoken answer folded in
# ---------------------------------------------------------------------

REDIAGNOSE_PROMPT_TEMPLATE = """You are an agricultural expert helping
Bangladeshi farmers using KrishiKotha.

Crop: {crop}

Reference material for this crop:
{documents}

FIRST-PASS photo analysis (before farmer clarification):
{first_pass_reasoning}
Candidates considered: {matched_diseases}

You asked the farmer this clarifying question:
"{followup_question}"

The farmer answered (voice transcript, may contain ASR errors — interpret
charitably):
"{farmer_answer}"

Using the photo evidence AND the farmer's answer together, give your
FINAL diagnosis. Same grounding rules as before: only report symptoms/
treatment actually written in the reference material, don't borrow
treatment across diseases, and if still genuinely unresolved after this
answer, say so honestly rather than forcing a guess.

Return ONLY this JSON object, nothing else:

{{
  "matched_diseases": ["final disease name(s)"],
  "confidence": "high, medium, or low",
  "diagnosis_bangla": "final diagnosis in Bangla, incorporating the farmer's answer",
  "advice_bangla": "practical advice in Bangla, using only treatment text present in the material",
  "treatment_found_in_material": true or false,
  "reasoning_english": "how the farmer's answer changed or confirmed the diagnosis"
}}"""


def rediagnose_with_answer(
    first_pass_result: dict,
    crop: str,
    followup_question: str,
    farmer_answer: str,
) -> dict:
    start = time.time()
    crop_docs = _get_crop_docs()
    documents = crop_docs.get(crop.strip().lower(), "")

    prompt = REDIAGNOSE_PROMPT_TEMPLATE.format(
        crop=crop,
        documents=documents,
        first_pass_reasoning=first_pass_result.get("reasoning_english", ""),
        matched_diseases=first_pass_result.get("matched_diseases", []),
        followup_question=followup_question,
        farmer_answer=farmer_answer,
    )

    client = _get_client()
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=600,
    )

    raw_text = response.choices[0].message.content.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.lower().startswith("json"):
            raw_text = raw_text[4:].strip()

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        parsed = {
            "matched_diseases": first_pass_result.get("matched_diseases", []),
            "confidence": "low",
            "diagnosis_bangla": "PARSE_ERROR — falling back to first-pass result",
            "advice_bangla": first_pass_result.get("advice_bangla", ""),
            "treatment_found_in_material": False,
            "reasoning_english": f"Re-diagnosis JSON parse failed. Raw: {raw_text[:200]}",
        }

    parsed["crop"] = crop
    parsed["response_time_sec"] = round(time.time() - start, 2)
    parsed["followup_question_asked"] = followup_question
    parsed["farmer_answer"] = farmer_answer
    return parsed


# ---------------------------------------------------------------------
# Step 4: the whole agentic loop, wired together
# (this is the version to call from a plain script / notebook / test.py)
# For Streamlit, see the session_state pattern below instead — you can't
# use a blocking input() there.
# ---------------------------------------------------------------------

def diagnose_with_followup(image_path: str, crop: str, get_farmer_answer_fn=None):
    """
    get_farmer_answer_fn: a callable that takes the follow-up question
    (str) and returns the farmer's spoken answer (str). In a plain script
    this can literally be: record -> save wav -> listen(path). Injected
    as a function so this file stays decoupled from how audio is captured.
    """
    first_pass = diagnose_photo(image_path, crop)

    if not needs_followup(first_pass):
        first_pass["followup_asked"] = False
        return first_pass

    question = generate_followup_question(first_pass)
    speak(question, "followup_question.mp3")

    if get_farmer_answer_fn is None:
        # No way to get an answer — return first pass but flag it
        first_pass["followup_asked"] = True
        first_pass["followup_question"] = question
        first_pass["followup_answer"] = None
        return first_pass

    farmer_answer = get_farmer_answer_fn(question)

    final = rediagnose_with_answer(first_pass, crop, question, farmer_answer)
    final["followup_asked"] = True
    return final


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python followup_engine.py <image_path> <crop>")
        sys.exit(1)

    def fake_answer_fn(question: str) -> str:
        print(f"\n[TTS] Question saved to followup_question.mp3:\n  {question}\n")
        return input("Type the farmer's answer (simulating listen() for a quick test): ")

    result = diagnose_with_followup(sys.argv[1], sys.argv[2], get_farmer_answer_fn=fake_answer_fn)
    print(json.dumps(result, ensure_ascii=False, indent=2))
