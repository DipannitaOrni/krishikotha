import json
import re

from dotenv import load_dotenv
import os
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Fallback message shown if an API call fails (network, rate limit, etc.)
FALLBACK_MESSAGE = (
    "দুঃখিত, এই মুহূর্তে উত্তর দিতে সমস্যা হচ্ছে। "
    "একটু পরে আবার চেষ্টা করুন, অথবা স্থানীয় কৃষি অফিসারের সাথে যোগাযোগ করুন।"
)

# ---------------------------------------------------------------------------
# CALL 1 — TRIAGE
# Classifies the situation and enumerates candidate diseases as strict JSON.
# This is the piece that used to live entirely inside the model's own
# reasoning (STEP 1-3 of the old single-call prompt) with nothing checking
# whether it actually followed through. Now the candidate COUNT is a value
# the code can inspect and correct, instead of something the model quietly
# tracks across five paragraphs of instructions and then may abandon by the
# time it writes the final answer.
# ---------------------------------------------------------------------------
TRIAGE_PROMPT_TEMPLATE = """You are triaging a Bangladeshi farmer's crop-problem question.
Using ONLY the reference material below, decide which ONE situation applies,
in this exact priority order. Respond with STRICT JSON ONLY — no preamble, no
markdown fences, no explanation outside the JSON.

Reference material:
{documents}

Farmer's question:
{question}

Situations, in priority order:

1. "no_crop_named" — the question does not name a crop, AND the symptom
   described could reasonably apply to more than one crop in general.
   If the reference material below has already been narrowed to a single
   crop, the crop was already identified for the farmer from their wording
   (including unusual spellings or no-space compounds) — do NOT pick this
   situation in that case, even if the crop word isn't a clean dictionary
   spelling.

2. "crop_not_covered" — a crop IS identified, but it is not mentioned
   anywhere in the reference material at all.

3. "no_matching_disease" — the crop is covered, but nothing in the material
   describes this actual KIND of thing the farmer described. A shared word
   or color is not a real match unless the underlying observation is the
   same kind of thing (e.g. an insect sighting is not the same as a fungal
   growth, even if both are described as "white"). Treat this as uncovered
   rather than forcing the nearest-sounding entry.

4. "single_match" — the crop is covered and EXACTLY ONE disease/pest's
   described symptoms plausibly match.

5. "multiple_match" — TWO OR MORE diseases/pests plausibly match. This
   includes:
   - a disease described in more than one source document for this crop —
     count it ONCE, not once per document (duplication must never make a
     disease feel more or less likely than one described only once);
   - two different diseases that happen to share an IDENTICAL name in the
     material (e.g. two distinct causal organisms both labeled "Bacterial
     Leaf Blight") — list each one separately in "candidates" with a
     distinguishing tag, e.g. "Bacterial Leaf Blight (Pseudomonas syringae)"
     vs "Bacterial Leaf Blight (Xanthomonas campestris)".

Before deciding, scan the ENTIRE reference material for this crop — do not
stop as soon as you've found one or two plausible candidates. A third or
fourth candidate elsewhere in the material, or one only described in a single
short sentence, is exactly as valid as one repeated or given more space, and
must not be silently dropped.

Output JSON with exactly this shape:
{{
  "situation": "no_crop_named" | "crop_not_covered" | "no_matching_disease" | "single_match" | "multiple_match",
  "crop": "<crop name if known, else null>",
  "candidates": ["<disease name 1>", "<disease name 2>", ...]
}}
"candidates" must contain exactly one entry for "single_match", two or more
for "multiple_match", and be an empty list for every other situation.
"""


TRIAGE_MODEL = "gpt-4o"      # keep on the full model -- eval showed gpt-4o-mini
                              # fabricating/garbling candidate names and mis-splitting
                              # clear single-disease cases here; this call's mistakes
                              # cascade into everything downstream, and the routing +
                              # section-trimming fixes already shrank its token cost a lot
ANSWER_MODEL = "gpt-4o-mini"  # generation-following-fixed-instructions task; no
                              # obvious quality issues seen in spot checks


def get_triage(question, reference_docs):
    """Call 1: classify the situation and enumerate candidate diseases.

    Returns a dict, e.g.:
      {"situation": "multiple_match", "crop": "cotton",
       "candidates": ["Anthracnose", "Boll Rot"]}

    On API failure or invalid JSON, returns situation "_error" so the caller
    degrades gracefully via FALLBACK_MESSAGE instead of crashing.
    """
    prompt = TRIAGE_PROMPT_TEMPLATE.format(documents=reference_docs, question=question)
    try:
        response = client.chat.completions.create(
            model=TRIAGE_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"⚠️  Triage call failed or returned invalid JSON: {e}")
        return {"situation": "_error", "crop": None, "candidates": []}

    situation = data.get("situation")
    candidates = data.get("candidates") or []

    # Don't trust the model's self-reported situation label blindly — check
    # it against the candidate list it actually produced, and correct it if
    # the two disagree. This is the main thing that fixes the "said multiple
    # in its head, answered single in prose" failure mode.
    if situation == "single_match" and len(candidates) != 1:
        situation = "multiple_match" if len(candidates) >= 2 else "no_matching_disease"
    elif situation == "multiple_match" and len(candidates) < 2:
        situation = "single_match" if len(candidates) == 1 else "no_matching_disease"

    return {"situation": situation, "crop": data.get("crop"), "candidates": candidates}


# ---------------------------------------------------------------------------
# CALL 2 — ANSWER
# Writes the farmer-facing Bangla answer under an instruction fixed by the
# situation from get_triage(). The model does not get to re-decide whether
# to ask a clarifying question here — that decision was already made in code.
# ---------------------------------------------------------------------------
ANSWER_PROMPT_TEMPLATE = """You are a helpful farming assistant for Bangladeshi farmers.
Using ONLY the reference material below, write the final answer in Bangla for
the farmer. Do not show any internal reasoning — only the final answer.

Reference material:
{documents}

Farmer's question:
{question}

The situation has ALREADY been determined to be: {situation}
Your instruction for this answer: {instruction}

Rules that apply no matter which situation this is:
- Never invent symptoms, favourable conditions, disease cycle detail, or
  management/treatment steps that are not explicitly written in the
  reference material under that specific disease's own heading.
- If a disease's treatment section has even one concrete step written
  (however short, even a single sentence), use it directly — do not claim
  you lack treatment information in that case.
- If a disease's treatment section truly has nothing written under its own
  heading, say so honestly and suggest contacting a local agricultural
  officer, rather than borrowing steps written for a different disease.
- If a disease is only named (e.g. inside a list) with no symptom text
  given anywhere in the material, do not describe symptoms for it — say
  plainly that this isn't described in your material, even if the disease's
  name sounds self-explanatory.
"""

INSTRUCTIONS = {
    "no_crop_named": (
        "Ask the farmer exactly ONE clarifying question asking which crop "
        "they mean. Do not guess a crop and do not give any diagnosis yet."
    ),
    "crop_not_covered": (
        "Tell the farmer honestly that you don't have reliable information "
        "on that crop, and suggest contacting a local agricultural officer. "
        "Do NOT ask a clarifying question."
    ),
    "no_matching_disease": (
        "Tell the farmer honestly that your material doesn't describe "
        "anything matching what they described, and suggest contacting a "
        "local agricultural officer. Do NOT guess a diagnosis."
    ),
    "single_match": (
        "Give a direct, confident diagnosis for exactly this disease: "
        "{candidates}. Do NOT ask any clarifying question — you already "
        "have enough information. Give its treatment/management using only "
        "what is written under its own heading."
    ),
    "multiple_match": (
        "You MUST ask exactly ONE clarifying question that helps "
        "distinguish between ALL of the following candidates, mentioned "
        "together in your question: {candidates}. Target the specific "
        "details that actually differ between them (e.g. exact colour "
        "progression, which part of the plant, speed of onset, texture). "
        "Do NOT commit to a single diagnosis and do NOT give treatment "
        "steps yet — asking the question is the entire job of this answer."
    ),
    "_error": (
        "Apologize briefly and suggest the farmer try again shortly or "
        "contact a local agricultural officer."
    ),
}


# Situations whose instruction never references document content (they
# just ask a clarifying question or decline honestly) don't need the
# reference docs in the answer prompt at all. Only single_match and
# multiple_match actually cite symptoms/treatment from the material.
SITUATIONS_NEEDING_DOCS = {"single_match", "multiple_match"}


# ---------------------------------------------------------------------------
# Section trimming for multi-disease crop files (mango/tea/cotton/sugarcane
# each cover many diseases in ONE file). The triage call needs the whole
# file to enumerate candidates, but by the time we reach the answer call we
# already know which disease(s) won -- there's no reason to re-send the
# other 7-19 diseases' worth of text. This looks for either heading style
# actually used in the reference docs ("DISEASE NAME: X" or "রোগ N: X"),
# splits into per-disease sections, and keeps only the section(s) matching
# triage's candidates.
#
# Fails safe by design: if a file uses neither heading style (e.g. rice,
# where each disease is already its own separate file), or a candidate name
# can't be confidently matched to a section, the FULL original text is
# returned rather than risk silently dropping grounding text the answer
# needs.
# ---------------------------------------------------------------------------
_DISEASE_HEADING_PATTERNS = [
    re.compile(r"^DISEASE NAME:\s*(.+)$", re.M),
    re.compile(r"^রোগ\s*[০-৯0-9]+\s*[:।]\s*(.+)$", re.M),
]

_NAME_STOPWORDS = {"রোগ", "ও", "এর", "of", "disease", "and", "the"}


def _split_by_disease(doc_text):
    """Split reference text into {heading_name: section_text} using
    whichever known heading pattern is actually present. Returns None if
    fewer than 2 headings are found (nothing meaningful to split)."""
    for pattern in _DISEASE_HEADING_PATTERNS:
        matches = list(pattern.finditer(doc_text))
        if len(matches) >= 2:
            sections = {}
            for i, m in enumerate(matches):
                start = m.start()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(doc_text)
                sections[m.group(1).strip()] = doc_text[start:end].strip()
            return sections
    return None


def _name_tokens(s):
    s = re.sub(r"[()\-\u2013\u2014:।,\[\]]", " ", s)
    tokens = [t.lower() for t in re.split(r"\s+", s.strip()) if t]
    return {t for t in tokens if t not in _NAME_STOPWORDS and len(t) > 1}


def _match_score(candidate, heading):
    """Fraction of the CANDIDATE's own words found in the heading, so a
    heading's extra editorial text (severity notes, alt names, etc.) doesn't
    dilute the score against a short, exact candidate name."""
    wc, wh = _name_tokens(candidate), _name_tokens(heading)
    if not wc or not wh:
        return 0.0
    return len(wc & wh) / len(wc)


def trim_to_candidates(doc_text, candidates, min_score=0.5):
    """Shrink reference text to just the section(s) matching triage's
    candidate disease name(s). Falls back to the full text if it can't
    split the doc, or can't confidently match every candidate."""
    if not candidates:
        return doc_text
    sections = _split_by_disease(doc_text)
    if sections is None:
        return doc_text
    selected = []
    for cand in candidates:
        best_name, best_score = None, 0.0
        for name in sections:
            score = _match_score(cand, name)
            if score > best_score:
                best_name, best_score = name, score
        if best_score < min_score:
            return doc_text
        selected.append(sections[best_name])
    return "\n\n".join(selected)


def get_answer(question, reference_docs, triage):
    """Call 2: write the farmer-facing answer, following the situation and
    candidate list decided by get_triage()."""
    situation = triage["situation"]
    if situation == "_error":
        return FALLBACK_MESSAGE

    candidates_str = ", ".join(triage["candidates"])
    instruction_template = INSTRUCTIONS.get(situation, INSTRUCTIONS["no_matching_disease"])
    instruction = instruction_template.format(candidates=candidates_str)

    if situation in SITUATIONS_NEEDING_DOCS:
        docs_for_prompt = trim_to_candidates(reference_docs, triage["candidates"])
    else:
        docs_for_prompt = ""

    prompt = ANSWER_PROMPT_TEMPLATE.format(
        documents=docs_for_prompt,
        question=question,
        situation=situation,
        instruction=instruction,
    )

    try:
        response = client.chat.completions.create(
            model=ANSWER_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"⚠️  Answer call failed: {e}")
        return FALLBACK_MESSAGE


def load_doc(filepath):
    """Load a text file safely, warning if it's missing."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"⚠️  WARNING: File not found — {filepath}")
        return ""


# Which files belong to each crop's reference material.
CROP_FILES = {
    "rice": [
        "ধানের_খোলপোড়া_রোগ.txt",
        "ধানের_চারাপোড়া_রোগ.txt",
        "ধানের_টুংরো_রোগ.txt",
        "ধানের_ব্লাস্ট_রোগ_কৃষকদের_করণীয়.txt",
    ],
    "jute": ["14-Diseases-of-Jute.txt"],
    "beans": ["bean.txt", "bean 2.txt", "bean3.txt"],
    "lemon": ["lemon.txt"],
    "mustard": ["shorisha_aphid.txt", "shorisha_blight.txt"],
    "potato": ["potato.txt"],
    "tomato": ["tomato.txt"],
    "wheat": ["Wheat_Diseases_Bangladesh.txt", "Wheat_Blast_Disease_Info.txt"],
    "tobacco": ["Tobacco_Diseases_Bangladesh.txt"],
    "maize": ["Maize_Diseases_Bangladesh.txt", "Fall_Armyworm_FAW_Info.txt"],
    "mango": ["Mango_Diseases.txt"],
    "tea": ["Tea_Diseases_Bangladesh.txt"],
    "sugarcane": ["Sugarcane_Diseases.txt"],
    "cotton": ["Cotton_Diseases.txt"],
}

# Keywords (including common spelling/spacing variants) used to detect which
# crop(s) a farmer's question is about, so we can narrow the reference
# material passed to the model instead of always sending all ~14 crops'
# worth of text.
#
# NOTE: these are matched against a WHITESPACE-STRIPPED version of both the
# keyword and the question (see _normalize / identify_crops below), so
# multi-word entries like "আম গাছ" also match no-space compounds like
# "আমগাছে". Keep entries here in their natural spaced form for readability;
# normalization happens at match time, not by hand-enumerating every
# spacing variant.
#
# COST-CRITICAL: any question that fails to match exactly one crop here
# falls back to ALL ~14 crops' combined text (see answer_question below).
# The original "আম"/"চা" avoidance (dropping the bare root entirely because
# it collides with আমার/চাল) meant a huge fraction of real mango/tea
# questions -- ones that just say "আম পাতায়" or "চা পাতায়" with a space,
# rather than a compound like "আমগাছে" -- matched NOTHING and silently
# ballooned to the full-corpus path on every single call. See
# CROP_TOKEN_REGEXES below for the fix: match the bare root, but only as
# its own token, so আমার/আমি/চাল/চাষ/চারা don't false-trigger it.
CROP_KEYWORDS = {
    "rice": ["ধান", "চাল", "ভাত"],
    "jute": ["পাট"],
    "beans": ["শিম", "বরবটি"],
    "lemon": ["লেবু"],
    "mustard": ["সরিষা", "সরিষার"],
    "potato": ["আলু"],
    "tomato": ["টমেটো"],
    "wheat": ["গম"],
    "tobacco": ["তামাক"],
    "maize": ["ভুট্টা", "মকা", "মকাই"],
    "mango": ["আমের", "আম গাছ", "আম বাগান"],
    "tea": ["চা গাছ", "চা বাগান", "চায়ের"],
    "sugarcane": ["আখ", "ইক্ষু", "সুগারকেন"],
    "cotton": ["তুলা", "কার্পাস"],
}

# Short roots that are only safe to match as a STANDALONE token (bounded by
# whitespace/punctuation/string edges), not as a plain substring, because
# they're prefixes of common unrelated words:
#   দান  -> misspelling of ধান, but also the start of দানার ("granule-like")
#   আম   -> mango, but also the start of আমার/আমি/আমরা ("my"/"I"/"we")
#   চা   -> tea, but also the start of চাষ ("cultivation")/চারা ("seedling")
_TOKEN_BOUNDARY = r"(?:^|(?<=[\s,।!?]))%s(?=[\s,।!?]|$)"
CROP_TOKEN_REGEXES = {
    "rice": re.compile(_TOKEN_BOUNDARY % "দান"),
    "mango": re.compile(_TOKEN_BOUNDARY % "আম"),
    "tea": re.compile(_TOKEN_BOUNDARY % "চা"),
}

# Figurative "like X" comparisons that must NOT count as a real crop
# mention (e.g. describing a wheat symptom as "সাদা তুলার মতো" = "white
# like cotton wool" was previously misdetected as a cotton question,
# triggering a full-corpus, ambiguous-crop routing for an unambiguous
# single-crop question). Stripped from the text before matching.
FALSE_POSITIVE_PHRASES = {
    "cotton": ["তুলার মতো", "তুলার ন্যায়"],
    "potato": ["আলুর মতো", "আলুর ন্যায়"],
}


def _normalize(text):
    """Strip whitespace so spaced keywords also match no-space compounds
    (e.g. "আম গাছ" vs "আমগাছে")."""
    return re.sub(r"\s+", "", text)


def load_crop_docs():
    """Load reference text for each crop separately.

    Returns a dict {crop_name: combined_text_for_that_crop}. Call this once
    (e.g. at app startup) and reuse the result.
    """
    return {
        crop: "\n\n".join(filter(None, [load_doc(f) for f in files]))
        for crop, files in CROP_FILES.items()
    }


def identify_crops(question):
    """Return the list of crop names whose keywords appear in the question."""
    working_text = question
    for crop, phrases in FALSE_POSITIVE_PHRASES.items():
        for phrase in phrases:
            working_text = working_text.replace(phrase, "")

    norm_q = _normalize(working_text)
    matched = {
        crop for crop, keywords in CROP_KEYWORDS.items()
        if any(_normalize(kw) in norm_q for kw in keywords)
    }
    for crop, pattern in CROP_TOKEN_REGEXES.items():
        if pattern.search(working_text):
            matched.add(crop)
    return list(matched)


def load_all_docs():
    """Load and combine ALL crops' reference documents into one string.

    Kept for cases where the crop can't be narrowed down (no crop named, or
    more than one crop named) — see answer_question().
    """
    return "\n\n".join(filter(None, load_crop_docs().values()))


def answer_question(question, crop_docs, combined_docs, return_triage=False):
    """Route a question to the right crop's reference material, triage it,
    then answer it.

    - Exactly one crop keyword matched -> pass ONLY that crop's docs.
    - 2+ crops matched -> pass ONLY the union of those matched crops' docs
      (not all ~14 crops). This is the actual mixed-crop case, so the model
      still sees both/all named crops, just without the ~10 other unrelated
      crops' text along for the ride.
    - Zero crops matched -> fall back to the full combined docs. This is the
      only case that genuinely needs everything, since the model may need
      to spot a crop mentioned in unusual phrasing our keyword list missed,
      or recognize the question as off-topic.

    If return_triage=True, returns (answer, triage_dict) instead of just the
    answer string — useful for logging *why* a decision was made (e.g. in
    run_eval.py), not just what the final text says.
    """
    matched = identify_crops(question)
    if len(matched) == 1:
        reference_docs = crop_docs[matched[0]]
    elif len(matched) > 1:
        reference_docs = "\n\n".join(
            filter(None, (crop_docs[c] for c in matched))
        )
    else:
        reference_docs = combined_docs

    triage = get_triage(question, reference_docs)
    answer = get_answer(question, reference_docs, triage)

    if return_triage:
        return answer, triage
    return answer


if __name__ == "__main__":
    crop_docs = load_crop_docs()
    combined_docs = "\n\n".join(filter(None, crop_docs.values()))
    print(f"Total combined document length: {len(combined_docs)} characters\n")

    test_questions = [
        "আমার ধানের পাতায় চোখের মতো দাগ দেখা যাচ্ছে",        # rice blast — single_match
        "আমার পাটের গাছে কালো দাগ দেখা যাচ্ছে",               # jute — multiple_match
        "আমগাছে ফলে কালো দাগ পড়েছে",                        # mango, no-space compound
        "চাগাছের পাতায় দাগ পড়েছে",                          # tea, no-space compound
        "আম পাতায় পানিভেজা দাগ দেখা যাচ্ছে",                # mango — duplicate disease name
        "পাতা হলুদ হয়ে যাচ্ছে",                             # no crop named
        "আমার ভুট্টা গাছে পোকা দেখা যাচ্ছে",                 # crop not covered (example)
    ]

    for q in test_questions:
        answer, triage = answer_question(q, crop_docs, combined_docs, return_triage=True)
        print(f"Q: {q}")
        print(f"TRIAGE: {triage}")
        print(f"A: {answer}")
        print("\n" + "=" * 60 + "\n")
