"""
KrishiKotha — Photo Diagnosis (v3)
-------------------------------------
Rebuilt to match the REAL reference documents (unstructured prose, multiple
files per crop, no clean "## heading" separators) instead of assuming a
clean format that doesn't exist.

Uses the same document loading (crop_documents.py) as Person B's text Q&A
pipeline, and carries over the same anti-hallucination discipline:
  - Only report symptoms/treatment that are ACTUALLY written in the docs
  - Don't invent plausible-sounding details from general knowledge
  - If a disease is only named with no symptom detail, say so honestly
  - If genuinely ambiguous between 2+ diseases from the photo alone,
    say so explicitly and list what additional visible detail would help
    distinguish them, rather than confidently guessing one

Since crop is already known (from a UI dropdown, not guessed), this
pipeline does NOT need to ask "which crop" the way Person B's text
pipeline sometimes does — that ambiguity is already resolved upstream.

Usage:
    from diagnose import diagnose_photo
    result = diagnose_photo("images/rice_blast_01.jpg", crop="rice")
    print(result["advice_bangla"])
"""

import base64
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from crop_documents import load_crop_docs, get_available_crops

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

FALLBACK_MESSAGE = (
    "দুঃখিত, এই মুহূর্তে উত্তর দিতে সমস্যা হচ্ছে। "
    "একটু পরে আবার চেষ্টা করুন, অথবা স্থানীয় কৃষি অফিসারের সাথে যোগাযোগ করুন।"
)

_client = None
_crop_docs_cache = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        if not API_KEY:
            raise RuntimeError(
                "OPENAI_API_KEY not found. Copy .env.example to .env and add your key."
            )
        _client = OpenAI(api_key=API_KEY)
    return _client


def _get_crop_docs() -> dict:
    """Loads and caches all crop documents (loaded once, reused across calls)."""
    global _crop_docs_cache
    if _crop_docs_cache is None:
        _crop_docs_cache = load_crop_docs()
    return _crop_docs_cache


PHOTO_PROMPT_TEMPLATE = """You are an agricultural expert helping Bangladeshi
farmers who are using a voice/photo assistant called KrishiKotha.

The farmer has already told you the crop in this photo is: {crop}.
Do not question the crop — focus entirely on diagnosing what you see.

Reference material for this crop (this may be unstructured prose extracted
from leaflets/PDFs, with multiple diseases described in the same block of
text — read the ENTIRE material carefully, don't stop at the first disease
you notice):

{documents}

Before writing your final answer, work through these steps internally (do
not show this reasoning to the farmer — only give the final JSON answer):

STEP 1 — Look at the photo carefully. Note the visible symptoms: spot
shape/color, leaf discoloration pattern, wilting, insect presence, powdery
or fuzzy growth, lesion location (leaf/stem/root), etc.

STEP 2 — Scan the ENTIRE reference material (all of it, not just the first
disease mentioned) and list every disease/pest whose described symptoms
could plausibly match what you see in the photo. Do this based purely on
how well the described symptoms match the visual evidence — ignore how
much space or repetition a disease gets in the material. A disease
mentioned once briefly is just as valid a candidate as one described at
length.

STEP 3 — Decide how to respond:
  - If exactly ONE disease matches what's visible, give a direct diagnosis.
  - If TWO OR MORE diseases could plausibly match based on what's visible
    in the photo alone, do NOT pick one confidently. Instead, name the
    top candidates and explain what additional visible detail (e.g. "check
    if there's white powdery growth on the underside of the leaf" or
    "check if the stem base also has dark lesions") would help tell them
    apart — since you cannot ask the farmer a follow-up question about an
    already-submitted photo, give this as practical guidance instead.

STEP 4 — Only include treatment/control steps that are ACTUALLY written in
the reference material under that specific disease. Do not borrow
treatment from a different disease, even for the same crop. If a treatment
section is genuinely empty for that disease, say so honestly rather than
inventing generic advice.

STEP 5 — Never invent symptoms not written in the material. If a disease is
only named (with no symptom description anywhere in the material), do not
describe plausible-sounding symptoms for it from general plant-pathology
knowledge — say the material doesn't describe it in detail.

STEP 6 — Match the KIND of thing, not just a shared word. An insect/pest
sighting is not the same observation as a fungal growth or powdery residue,
even if both could loosely be described with the same color word.

Return ONLY a JSON object, nothing else (no markdown, no code fences):

{{
  "matched_diseases": ["disease name(s) that plausibly match — one name if certain, multiple if genuinely ambiguous"],
  "confidence": "high (one clear match), medium (narrowed to 2-3 candidates), or low (very unclear photo)",
  "diagnosis_bangla": "the diagnosis explained simply in Bangla — if ambiguous, name the top candidates and what would help distinguish them",
  "advice_bangla": "practical next-step advice in Bangla, using ONLY treatment text actually present in the material for the matched disease(s). If no treatment is written, say so honestly and suggest contacting a local agricultural officer.",
  "treatment_found_in_material": true or false,
  "reasoning_english": "short English note for the dev team on visual cues used and which candidates were considered"
}}"""


def _encode_image(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _guess_media_type(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in (".jpg", ".jpeg"):
        return "image/jpeg"
    if ext == ".png":
        return "image/png"
    if ext == ".webp":
        return "image/webp"
    return "image/jpeg"


def diagnose_photo(image_path: str, crop: str, debug: bool = False) -> dict:
    """
    Main hand-off function for app.py.

    Args:
        image_path: path to the crop photo
        crop: known crop name — must match a key in crop_documents.CROP_FILES
              (e.g. "rice", "potato", "jute", "wheat", "maize", "tomato",
              "beans", "lemon", "mustard", "tobacco")
        debug: if True, prints the document length and full prompt sent

    Returns:
        {
          "crop": str,
          "matched_diseases": list[str],
          "confidence": str,
          "diagnosis_bangla": str,
          "advice_bangla": str,           # what to show the farmer
          "treatment_found_in_material": bool,
          "reasoning_english": str,       # dev-facing only
          "response_time_sec": float,
        }
    """
    start = time.time()
    crop_key = crop.strip().lower()

    crop_docs = _get_crop_docs()

    if crop_key not in crop_docs or not crop_docs[crop_key]:
        return {
            "crop": crop,
            "matched_diseases": [],
            "confidence": "n/a",
            "diagnosis_bangla": "অজানা",
            "advice_bangla": (
                "দুঃখিত, এই ফসলের জন্য আমাদের কাছে কোনো তথ্য নেই। "
                "অনুগ্রহ করে স্থানীয় কৃষি অফিসারের সাথে যোগাযোগ করুন।"
            ),
            "treatment_found_in_material": False,
            "reasoning_english": f"No reference document loaded for crop '{crop}'. "
                                   f"Available crops: {get_available_crops()}",
            "response_time_sec": round(time.time() - start, 2),
        }

    documents = crop_docs[crop_key]

    if debug:
        print(f"[DEBUG] Crop: {crop_key} | Document length: {len(documents)} characters")

    path = Path(image_path)
    b64_image = _encode_image(path)
    media_type = _guess_media_type(path)
    prompt = PHOTO_PROMPT_TEMPLATE.format(crop=crop, documents=documents)

    if debug:
        print(f"[DEBUG] Prompt length: {len(prompt)} characters")
        print(f"[DEBUG] Prompt preview:\n{prompt[:500]}\n...\n{'-'*60}")

    client = _get_client()

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{media_type};base64,{b64_image}"},
                        },
                    ],
                }
            ],
            temperature=0.0,
            max_tokens=700,
        )
    except Exception as e:
        print(f"WARNING: API call failed: {e}")
        return {
            "crop": crop,
            "matched_diseases": [],
            "confidence": "n/a",
            "diagnosis_bangla": "",
            "advice_bangla": FALLBACK_MESSAGE,
            "treatment_found_in_material": False,
            "reasoning_english": f"API error: {e}",
            "response_time_sec": round(time.time() - start, 2),
        }

    raw_text = response.choices[0].message.content.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.lower().startswith("json"):
            raw_text = raw_text[4:].strip()

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        parsed = {
            "matched_diseases": [],
            "confidence": "n/a",
            "diagnosis_bangla": "PARSE_ERROR",
            "advice_bangla": FALLBACK_MESSAGE,
            "treatment_found_in_material": False,
            "reasoning_english": f"Model did not return valid JSON. Raw: {raw_text[:200]}",
        }

    parsed["crop"] = crop
    parsed["response_time_sec"] = round(time.time() - start, 2)
    return parsed


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print(f"Usage: python diagnose.py <image_path> <crop> [--debug]")
        print(f"Available crops: {get_available_crops()}")
        sys.exit(1)

    debug_flag = "--debug" in sys.argv
    result = diagnose_photo(sys.argv[1], sys.argv[2], debug=debug_flag)
    print(json.dumps(result, ensure_ascii=False, indent=2))
