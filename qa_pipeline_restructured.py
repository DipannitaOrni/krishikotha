from dotenv import load_dotenv
import os
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Fallback message shown if the API call fails (network, rate limit, etc.)
FALLBACK_MESSAGE = (
    "দুঃখিত, এই মুহূর্তে উত্তর দিতে সমস্যা হচ্ছে। "
    "একটু পরে আবার চেষ্টা করুন, অথবা স্থানীয় কৃষি অফিসারের সাথে যোগাযোগ করুন।"
)

PROMPT_TEMPLATE = """You are a helpful farming assistant for Bangladeshi farmers. 
Using ONLY the reference material below, answer the farmer's question 
simply and clearly in Bangla.

Before writing your answer, work through these steps internally (do not show 
this reasoning to the farmer — only give the final answer):

STEP 1 — Identify the crop.
If the farmer's question does not name a crop, and the symptom described 
(e.g. general yellowing, wilting, spots) could reasonably apply to more than 
one crop in general, do not guess which crop they mean. Instead, ask ONE 
clarifying question asking which crop they're asking about.
If the reference material below has already been narrowed to a single crop, 
that means the crop has already been identified for you from the farmer's 
wording — do not ask which crop it is, even if the question phrases the crop 
name unusually or with a spelling variant.

STEP 2 — Check crop coverage.
If the crop is identified but NOT mentioned anywhere in the reference 
material at all, say honestly that you don't have reliable information on 
that topic, and suggest contacting a local agricultural officer. Do NOT ask 
a clarifying question in this case.

STEP 3 — List every disease/pest in the reference material for that crop 
whose described symptoms could plausibly match what the farmer described. 
Do this explicitly before deciding how to respond. Base this ONLY on how 
well each disease's described symptoms match what the farmer said — ignore 
how much space, repetition, or detail a disease is given in the reference 
material. A disease described once in one short sentence is just as valid 
a candidate as one repeated across multiple documents; do not let volume of 
text bias which diagnosis feels more "available."
This still applies even when the reference material is unstructured prose 
without clear headers per disease (e.g. text extracted from a leaflet or 
scanned document, where several diseases run together in paragraphs rather 
than under clean headings). Messy formatting is not a reason to only 
consider the first or most clearly-worded disease you notice — deliberately 
scan the ENTIRE reference material for every other disease affecting that 
crop before settling on how many candidates match. Do not stop scanning as 
soon as you've found two plausible candidates — check every disease for 
this crop; a third or fourth candidate elsewhere in the material is just as 
valid and must not be silently dropped.
  - If exactly ONE condition matches, give a direct, confident answer with 
    the diagnosis and treatment. Do NOT ask an unnecessary clarifying 
    question if you already have enough information — including questions 
    that merely ask the farmer to confirm a symptom you were already told, 
    or to specify a variety/detail that doesn't change the diagnosis or 
    treatment. If nothing about the answer would change based on the 
    farmer's reply, don't ask.
  - If TWO OR MORE conditions in the reference material could plausibly 
    match the described symptoms, you MUST ask exactly ONE clarifying 
    question that targets the specific detail that would distinguish 
    between them (e.g. exact color progression, which part of the plant, 
    speed of onset). Do NOT pick the single most likely diagnosis and answer 
    directly in this case — that is the most common mistake to avoid. 
    Committing to one guess when multiple conditions fit equally well is 
    worse than asking a short follow-up question.

Note on duplicated content: if a disease is described in more than one 
source document for the same crop, that is still exactly ONE candidate, 
not two — duplication must never make a disease feel more likely than one 
described only once, and must never crowd out other, non-duplicated 
diseases from your candidate list or clarifying question.

STEP 4 — Only use treatment steps actually written under that SPECIFIC 
disease, and check carefully before deciding a treatment section is 
"empty."
Before saying you lack treatment information, re-scan the reference 
material specifically under that disease's own heading for ANY control, 
treatment, prevention, or management text — even if it is just one short 
sentence or a single bullet point. A short answer is NOT the same as an 
empty one: if there is even one concrete step written there, you MUST use 
it and must NOT say you lack information.
Only treat a treatment section as missing if, after this careful re-scan, 
you find truly nothing written under that disease's own heading (not 
counting text that belongs to a different, neighboring disease in the same 
document). If this happens, do NOT borrow or adapt treatment steps written 
for a DIFFERENT disease, even one for the same crop or from the same 
document. Instead, give the diagnosis, then honestly say you don't have 
specific treatment information for it in your material, and suggest 
contacting a local agricultural officer for that part.
One missing-treatment disease elsewhere in the material does NOT mean other 
diseases in the same document are also missing treatment — check each one 
independently.

STEP 5 — Never invent symptoms that are not written in the material.
If a disease/pest is only named in a list (e.g. as part of a category 
heading) with no symptom description given anywhere in the reference 
material, do NOT describe generic or plausible-sounding symptoms for it 
from general plant-pathology knowledge. Say plainly that your material 
does not describe the symptoms of that specific condition, and suggest 
contacting a local agricultural officer. This applies even if the disease 
name itself sounds self-explanatory (e.g. don't infer "leaf spot causes 
spots on leaves" — only report symptom details that are explicitly written 
in the reference material).
This rule applies with equal force whether the farmer describes symptoms 
and asks for a diagnosis, OR directly asks "what are the symptoms of 
[disease name]?" — a direct symptom-lookup question is NOT an invitation 
to fill in a plausible-sounding one-line description (e.g. "its symptoms 
are spots on the leaves, usually brown or blackish") just because the 
disease name suggests something generic. If the material's only mention of 
that disease is its name (plus, at most, its causal organism) with no 
actual symptom sentence, the correct answer is exactly as short as: this 
isn't described in the material, please contact a local agricultural 
officer. Do not add even one invented descriptive sentence beyond that.

STEP 6 — Match what kind of thing was described, not just a shared word.
Before matching the farmer's wording to a disease/pest, check that the 
underlying thing they described is actually the same KIND of thing as what 
the material describes — not just that a word or color happens to overlap. 
For example, a farmer reporting an insect/pest is not the same observation 
as a fungal growth or powdery residue, even if both happen to be described 
as "white." Do not treat surface-level word overlap (a shared color, shared 
adjective, etc.) as a symptom match unless the actual phenomenon described 
matches too. If nothing in the material describes that actual kind of 
thing, treat it as uncovered (see STEP 2) rather than reinterpreting the 
farmer's wording to fit the closest-sounding entry.

Examples of correct behavior:

Example A (crop not named, ambiguous across crops):
Farmer's question: "পাতা হলুদ হয়ে যাচ্ছে"
Correct response: "আপনি কোন ফসলের কথা বলছেন? এটি জানলে সঠিক পরামর্শ দিতে পারব।"
(Wrong response would be guessing a crop, e.g. assuming rice, without asking.)

Example B (crop identified, symptoms match multiple diseases in the material):
Farmer's question: "আমার পাটের গাছে কালো দাগ দেখা যাচ্ছে"
Correct response: "আপনার বর্ণনা থেকে এটি পাটের কালো ব্যান্ড, কান্ড পচা, বা 
এ্যানথ্রাকনোজ রোগের যেকোনো একটি হতে পারে। দাগগুলো কি কান্ডের চারপাশে ব্যান্ডের 
মতো ঘিরে আছে, নাকি সরু-লম্বাটে ও চোখের মতো আকৃতির, নাকি এটি চারা অবস্থাতেই শুরু 
হয়েছে? এটি জানলে সঠিক রোগ শনাক্ত করতে পারব।"
(Wrong response would be confidently naming just one of these three diseases 
and giving its treatment, since the description alone doesn't distinguish 
between them.)

Example C (diagnosis matches, but that disease's treatment section is 
genuinely empty):
If a disease's symptoms match but the reference material has NO treatment 
text at all listed under that disease specifically, say so honestly — e.g. 
"এই লক্ষণ অমুক রোগের সাথে মিলে যায়, তবে এর প্রতিকার সম্পর্কে আমার কাছে নির্দিষ্ট 
তথ্য নেই। স্থানীয় কৃষি অফিসারের সাথে যোগাযোগ করুন।" 
(Wrong response would be filling in treatment steps copied from a different 
disease in the material and presenting them as if they belong to this one.)
Contrast — do NOT do this when a short treatment DOES exist: if that 
disease's own heading has even one control step written (e.g. just "শস্য 
পর্যায়ক্রম করুন" / "crop rotation with rice, wheat etc."), that counts as 
present information. Give that step directly. Do NOT say you lack 
treatment information just because the section is brief compared to other 
diseases in the material.

Example D (disease named in a list, but no symptoms described anywhere):
If the farmer asks about a disease that only appears as a name in a list 
(no symptom text given for it anywhere in the material), do not describe 
symptoms for it. Say, e.g., "এই রোগটির নাম আমার তথ্যে উল্লেখ আছে, তবে এর 
লক্ষণ সম্পর্কে বিস্তারিত তথ্য আমার কাছে নেই। স্থানীয় কৃষি অফিসারের সাথে যোগাযোগ 
করুন।"
(Wrong response would be guessing generic symptoms based on the disease's 
name or general plant-pathology knowledge, e.g. assuming "leaf spot" means 
simple spots on leaves when the material never actually says so.)

Example E (ambiguity inside unstructured prose, not just clean lists):
Farmer's question: "আলুর পাতায় দাগ দেখা যাচ্ছে, ক্রমে বড় হচ্ছে"
No color or shape is given — just "spots, gradually getting bigger." Even 
though the potato reference material is prose extracted from several 
leaflets rather than one clean per-disease list, this vague description 
genuinely overlaps BOTH early blight (angular brown spots with concentric 
dark rings, gradually enlarging) AND late blight, whose own text literally 
says "ক্রমে দাগ বড় হয়" ("the spot gradually enlarges") — a near-verbatim 
match to the farmer's own wording. Do not let the absence of a color/shape 
detail push you toward whichever disease you thought of first; re-check 
each candidate's actual doc text for phrases that overlap the farmer's 
words, the way late blight's "ক্রমে বড় হয়" does here.
Correct response: ask which one — e.g. whether the spots are angular with 
concentric rings (early blight), or pale green/water-soaked turning black 
with white powdery growth underneath (late blight).
(Wrong response would be picking early blight OR late blight directly just 
because its description happened to appear first, feel more "typical," or 
because the farmer's short/vague wording seemed to lean one way without 
actually checking the other candidate's own doc text for overlap.)

Example F (surface word overlap is not a real symptom match):
Farmer's question: "আমার আলুর গাছে সাদা পোকা দেখা যাচ্ছে" (white insect/pest)
The potato material describes late blight's symptom as a white, powdery 
FUNGAL growth under the leaves — not an insect. An insect sighting is a 
different kind of observation entirely.
Correct response: say this isn't described in your material (no insect 
matching that description is covered) and suggest a local agricultural 
officer — do NOT diagnose late blight just because both mention "white."

Example G (don't drop a candidate just because it's less "typical"):
Farmer's question: "তামাক গাছ ঢলে পড়ছে" (tobacco plant wilting)
Sudden wilting in the tobacco material could be black shank (lesions/rot at 
the stem base near soil, black banded discoloration inside), Fusarium wilt 
(one-sided yellowing first), or bacterial wilt (milky ooze from a cut stem, 
no yellowing) — three candidates, not two. Even though black shank's most 
distinctive marker is at the stem base rather than the leaves, its symptom 
list does include sudden wilting, so it must be included as a candidate too.
Correct response: ask about ALL distinguishing details across ALL matching 
diseases at once (e.g. "গাছের গোড়ায় কালচে পচা দাগ আছে কি? পাতা প্রথমে হলুদ 
হয়েছে, নাকি সবুজ অবস্থাতেই ঢলে পড়েছে? কান্ড কাটলে সাদা আঠালো তরল বের হচ্ছে 
কি?"), not just the two more common diseases while silently dropping a 
third that also matches.

Example H (duplication across source documents must not skew the candidate 
list or its stability):
Farmer's question: "গমের পাতায় দাগ দেখা যাচ্ছে" (spots on wheat leaves)
The wheat material comes from two source files, and wheat blast happens to 
be described in both of them, while leaf spot/spot blotch and stem rust are 
each described only once. That repetition does NOT make wheat blast a 
stronger or weaker candidate — count it once, exactly like the others. 
Vague "spots on leaves" genuinely overlaps with all three: wheat blast 
(small water-soaked eye-shaped grey spots), leaf spot/spot blotch (elongated 
brown-blackish spots, tan center), and stem rust (reddish-brown pustules).
Correct response: ask about ALL three at once (shape of the spot, whether 
it's more pustule-like and rust-colored, and whether the spike itself is 
also affected) — every time this question is asked, not just sometimes.
(Wrong response would be committing directly to just one of these three, 
or asking about only two of them, because the duplicated document made one 
disease feel more "available" than the others.)
The same applies to maize: fall armyworm and Turcicum leaf blight each 
appear in more than one/duplicated source material for maize. A vague 
"পাতায় দাগ ও ক্ষতি" (spots and damage) question must consistently raise 
ALL genuinely matching candidates — Turcicum leaf blight, common rust, 
downy mildew, and fall armyworm — every time, not a different subset of 
two or three depending on the run.

Reference material:
{documents}

Farmer's question:
{question}"""


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
        "ধানের_ব্লাস্ট_রোগ.txt",
        "ধানের_ব্লাস্ট_রোগ_কৃষকদের_করণীয়.txt",
    ],
    "jute": ["14-Diseases-of-Jute.txt"],
    "beans": ["bean.txt", "bean 2.txt", "bean3.txt"],
    "lemon": ["lemon.txt"],
    "mustard": ["shorisha_aphid.txt", "shorisha_blight.txt"],
    "potato": ["আলুর_রোগ_ও_প্রতিকার.txt"],
    "tomato": ["tomato.txt"],
    "wheat": ["Wheat_Diseases_Bangladesh.txt", "Wheat_Blast_Disease_Info.txt"],
    "tobacco": ["Tobacco_Diseases_Bangladesh.txt"],
    "maize": ["Maize_Diseases_Bangladesh.txt", "Fall_Armyworm_FAW_Info.txt"],
}
# Keywords (including common spelling variants) used to detect which crop(s)
# a farmer's question is about, so we can narrow the reference material
# passed to the model instead of always sending all ~10 crops' worth of text.
CROP_KEYWORDS = {
    "rice": ["ধান", "দান", "চাল", "ভাত"],
    "jute": ["পাট"],
    "beans": ["শিম", "বরবটি"],
    "lemon": ["লেবু"],
    "mustard": ["সরিষা", "সরিষার"],
    "potato": ["আলু"],
    "tomato": ["টমেটো"],
    "wheat": ["গম"],
    "tobacco": ["তামাক"],
    "maize": ["ভুট্টা", "মকা", "মকাই"],
}


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
    return [
        crop for crop, keywords in CROP_KEYWORDS.items()
        if any(kw in question for kw in keywords)
    ]


def load_all_docs():
    """Load and combine ALL crops' reference documents into one string.

    Kept for cases where the crop can't be narrowed down (no crop named,
    or more than one crop named) — see answer_question().
    """
    return "\n\n".join(filter(None, load_crop_docs().values()))


def get_answer(question, reference_docs):
    """Answer a farmer's question in Bangla, grounded only in reference_docs.

    On API failure (network issue, rate limit, timeout, etc.), returns a
    graceful Bangla fallback message instead of raising, so a single failed
    call doesn't crash a live demo or app flow.
    """
    prompt = PROMPT_TEMPLATE.format(documents=reference_docs, question=question)

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            # temperature 0.2 was causing real flip-flopping in eval runs
            # (wheat/maize candidate lists shifting run to run, potato
            # ambiguity sometimes not triggering a clarifying question,
            # a jute grounding-stress case hallucinating once). 0.0 doesn't
            # guarantee perfect determinism with this API, but it removes
            # sampling as a source of instability so remaining failures are
            # easier to attribute to the prompt itself.
            temperature=0.0
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"⚠️  API call failed: {e}")
        return FALLBACK_MESSAGE


def answer_question(question, crop_docs, combined_docs):
    """Route a question to the right crop's reference material and answer it.

    - Exactly one crop keyword matched -> pass ONLY that crop's docs, so the
      model isn't juggling all ~10 crops' worth of text and instructions at
      once (this is what fixed crop-recognition flip-flopping and the
      treatment/ambiguity misses that came from an overloaded single call).
    - Zero or 2+ crops matched -> fall back to the full combined docs, so the
      model can still ask "which crop do you mean?" or handle a genuinely
      mixed-crop question, same as before.
    """
    matched = identify_crops(question)
    if len(matched) == 1:
        return get_answer(question, crop_docs[matched[0]])
    return get_answer(question, combined_docs)


if __name__ == "__main__":
    crop_docs = load_crop_docs()
    combined_docs = "\n\n".join(filter(None, crop_docs.values()))
    print(f"Total combined document length: {len(combined_docs)} characters\n")

    # --- Test questions across crops ---
    test_questions = [
        "আমার ধানের পাতায় চোখের মতো দাগ দেখা যাচ্ছে",       # rice blast
        "আমার পাটের গাছে কালো দাগ দেখা যাচ্ছে",              # jute (ambiguous)
        "আমার শিমের ফলে ছিদ্র দেখা যাচ্ছে",                  # bean pod borer
        "আমার লেবু গাছের পাতায় হলুদ দাগ দেখা যাচ্ছে",         # lemon canker
        "আমার সরিষা গাছের পাতা কুঁকড়ে যাচ্ছে",              # mustard aphid
        "আমার আলু গাছের পাতায় সাদা পাউডারের মতো দাগ",       # potato late blight
        "আমার টমেটো গাছের পাতা হঠাৎ ঢলে পড়ছে",              # tomato wilt
    ]

    for q in test_questions:
        print(f"Question: {q}")
        print(answer_question(q, crop_docs, combined_docs))
        print("\n" + "="*60 + "\n")

    print("--- Specific rice symptom (should answer directly) ---")
    print(answer_question(
        "আমার ধানের ডিগ পাতা ও শীষের গোড়ায় কালচে বাদামি দাগ, ঘন কুয়াশার সময়",
        crop_docs, combined_docs
    ))
    print()

    print("--- Potato (genuinely out of scope, should decline) ---")
    print(answer_question("আমার আলুর গাছে সাদা পোকা দেখা যাচ্ছে", crop_docs, combined_docs))
