"""
run_eval.py — Rigorous eval suite for the QA pipeline.

Structure:
  1. COVERAGE_CASES     — at least one question per disease/pest actually
                           described in your reference docs (not just one
                           question per crop).
  2. RULE3_CLARIFY_CASES — deliberately vague/ambiguous symptoms that SHOULD
                           trigger a single clarifying question (Rule 3),
                           because they genuinely overlap between two+
                           diseases in the same doc.
  3. GROUNDING_STRESS_CASES — questions about things named in a doc's disease
                           LIST but never given actual symptom text (e.g.
                           jute leaf spot / target spot / bacterial leaf
                           blight / root-knot / mosaic — the source doc lists
                           these but gives no symptoms for them). Tests
                           whether the model honestly admits it lacks detail
                           instead of hallucinating from general knowledge.
  4. ADVERSARIAL_CASES  — messy, real-world-style input: no crop named,
                           misspellings, mixed crops, off-topic questions,
                           empty/gibberish input.
  5. CONSISTENCY_CASES  — same question run N times to check whether the
                           diagnosis or rule-decision (answer/clarify/decline)
                           flips between runs at temperature 0.2.

Usage:
    python run_eval.py

Results append to eval.csv with blank columns for manual scoring:
    grounded (y/n), correct_behavior (y/n), simple (y/n), bangla_quality (y/n), notes
"""

import csv
import os
from datetime import datetime

from qa_pipeline_restructured import load_crop_docs, answer_question

EVAL_CSV_PATH = "eval.csv"
CONSISTENCY_REPEATS = 3

EXPECTED_HEADER = [
    "run_id", "timestamp", "category", "crop", "question",
    "expected_behavior", "answer",
    "grounded", "correct_behavior", "simple", "bangla_quality", "notes",
]

# ---------------------------------------------------------------------------
# 1. COVERAGE — one question per actual disease/pest with described symptoms
# ---------------------------------------------------------------------------
COVERAGE_CASES = [
    # Rice
    ("ধানের গোড়ার পাতার খোলে পানি ভেজা দাগ, দেখতে সাপের চামড়ার মতো", "rice", "sheath blight (খোলপোড়া)"),
    ("ট্রেতে ধানের চারা বাদামি হয়ে যাচ্ছে এবং মাটিতে সাদা ছত্রাক দেখা যাচ্ছে", "rice", "seedling blight (চারাপোড়া)"),
    ("ধান গাছ খাটো হয়ে যাচ্ছে এবং পাতা কমলা-হলুদ রং ধারণ করছে", "rice", "tungro virus"),
    ("ধানের পাতায় চোখের মতো দাগ দেখা যাচ্ছে", "rice", "leaf blast"),
    ("ধানের গিঁট কালো হয়ে ভেঙ্গে যাচ্ছে", "rice", "node blast"),
    ("আমার ধানের ডিগ পাতা ও শীষের গোড়ায় কালচে বাদামি দাগ, ঘন কুয়াশার সময়", "rice", "neck blast"),

    # Jute
    ("পাটের গাছে মাটি থেকে ২-৩ ফুট উপরে ঘন কালো ব্যান্ড দেখা যাচ্ছে", "jute", "black band"),
    ("পাটের কান্ডে হলদে-বাদামি পানিভেজা দাগ, দেখতে অনেকটা চোখ বা টাকু আকৃতির", "jute", "anthracnose"),
    ("পাটের চারা মাটির উপরিভাগে কালচে রেখা নিয়ে ঢলে মরে যাচ্ছে", "jute", "stem rot (seedling stage)"),

    # Beans
    ("শিমের পাতার নিচে লালচে-বেগুনি শিরা দেখা যাচ্ছে, ক্রমে কালো হয়ে যাচ্ছে", "beans", "anthracnose"),
    ("আমার শিমের ফলে ছিদ্র দেখা যাচ্ছে", "beans", "pod borer"),
    ("শিমের পাতা কুঁকড়ে যাচ্ছে এবং কালো ছত্রাকের (সুটিমোল্ড) মতো দেখা যাচ্ছে", "beans", "aphid"),

    # Lemon
    ("আমার লেবু গাছের পাতায় হলুদ দাগ দেখা যাচ্ছে", "lemon", "canker"),

    # Mustard
    ("আমার সরিষা গাছের পাতা কুঁকড়ে যাচ্ছে", "mustard", "aphid"),
    ("সরিষার নিচের পুরনো পাতায় গোল কালচে দাগ, পাতা ঝলসে যাচ্ছে", "mustard", "Alternaria blight"),
    ("সরিষা গাছ দুর্বল হয়ে যাচ্ছে এবং শিকড়ের সাথে অচেনা একটি গাছ জড়িয়ে আছে", "mustard", "Orobanche (parasitic plant)"),

    # Potato (representative subset of 12 — extend using this pattern)
    ("আমার আলু গাছের পাতায় সাদা পাউডারের মতো দাগ", "potato", "late blight"),
    ("আলুর নিচের পাতায় বাদামি কৌণিক দাগ, চক্রাকার, এবং টিউবারে কালচে দাগ", "potato", "early blight"),
    ("আলু গাছ ধীরে ধীরে ঢলে পড়ছে, পাতা সবুজ অবস্থাতেই নেতিয়ে যাচ্ছে, হলুদ হচ্ছে না", "potato", "bacterial wilt/brown rot"),
    ("আলুর গায়ে উঁচু, ভাসা বাদামি দাগ বা গোলাকার গর্ত", "potato", "scab (দাদ রোগ)"),

    # Tomato
    ("আমার টমেটো গাছের পাতা হঠাৎ ঢলে পড়ছে, হলুদ না হয়েই", "tomato", "bacterial wilt"),
    ("টমেটোর নিচের পাতা বেঁকে যাচ্ছে ও ঢলে পড়ছে, কান্ডে বাদামি দাগ", "tomato", "Fusarium wilt"),

    # Wheat
    ("গমের শীষে কালচে-ধূসর দাগ, শীষ সাদা হয়ে শুকিয়ে যাচ্ছে", "wheat", "wheat blast"),
    ("গমের পাতায় লম্বাটে বাদামি-কালচে দাগ, মাঝখানে হালকা বাদামি কিনারা গাঢ়", "wheat", "leaf spot/spot blotch"),
    ("গমের কান্ড ও পাতার খোলে লালচে-বাদামি ফোস্কার মতো দাগ, ফেটে গুঁড়া বের হচ্ছে", "wheat", "stem/black rust"),
    ("গমের পাতায় সাদা তুলার মতো গুঁড়া জমছে, নিচে হলুদ দাগ", "wheat", "powdery mildew"),

    # Tobacco
    ("তামাকের কান্ডের গোড়া মাটির কাছে কালচে ও পচা, ভিতরে কালো ব্যান্ড", "tobacco", "black shank"),
    ("তামাক গাছের একপাশের পাতা হলুদ হয়ে ঢলে পড়ছে, কান্ড কাটলে বাদামি দাগ", "tobacco", "Fusarium wilt"),
    ("তামাক পাতায় হালকা সবুজ-হলুদ ছোপ ছোপ মোজাইক প্যাটার্ন, পাতা কুঁচকানো", "tobacco", "tobacco mosaic virus"),
    ("তামাক পাতায় গোল দাগ, মাঝখানে সাদাটে বাদামি ও কিনারা গাঢ় বাদামি (ব্যাঙের চোখের মতো)", "tobacco", "frogeye leaf spot"),
    ("তামাক পাতার নিচে নীলচে-ধূসর তুলার মতো ছত্রাক, উপরে হালকা হলুদ ছোপ", "tobacco", "blue mold"),
    ("তামাক গাছ হঠাৎ ঢলে পড়ছে, কান্ড কাটলে সাদা আঠালো তরল বের হচ্ছে", "tobacco", "bacterial wilt"),

    # Maize (incl. Fall Armyworm)
    ("ভুট্টার পাতার মাঝখানের কুঁড়িতে ছিদ্র ও বিষ্ঠা জমে আছে", "maize", "fall armyworm (FAW)"),
    ("ভুট্টার পাতায় লম্বা সিগারেট আকৃতির ধূসর-বাদামি দাগ, শিরার সমান্তরালে", "maize", "Turcicum leaf blight"),
    ("ভুট্টার পাতায় ছোট গোলাকার লালচে-বাদামি ফোস্কা, ফেটে গুঁড়া বের হচ্ছে", "maize", "common rust"),
    ("ভুট্টার কচি পাতায় ফ্যাকাশে হলুদ সরু রেখা শিরা বরাবর, গাছ খাটো ও পাতা বাঁকা", "maize", "downy mildew"),
    ("ভুট্টার পাতার খোলে ধূসর-সবুজ পানিভেজা ব্যান্ড, গোড়া থেকে উপরে ছড়াচ্ছে", "maize", "banded leaf and sheath blight (BLSB)"),
    ("ভুট্টার কান্ডের নিচের অংশ নরম কালচে হয়ে পচে যাচ্ছে, ভিতরটা ফাঁপা", "maize", "stalk rot"),
]

# ---------------------------------------------------------------------------
# 2. RULE-3 STRESS TESTS — genuinely ambiguous within the SAME doc
# ---------------------------------------------------------------------------
RULE3_CLARIFY_CASES = [
    (
        "আমার পাটের গাছে কালো দাগ দেখা যাচ্ছে",
        "jute",
        "Ambiguous across stem rot / black band / anthracnose — all three involve blackening. Should ask which part of plant + shape of lesion.",
    ),
    (
        "আলুর পাতায় দাগ দেখা যাচ্ছে, ক্রমে বড় হচ্ছে",
        "potato",
        "Genuinely ambiguous between early blight (brown, angular, concentric) and late blight (pale green turning black, white powder underneath) — deliberately no color given, so both remain plausible. Should ask about color/shape (previous version of this test used 'বাদামি'/brown, which per the doc text only matches early blight and isn't a genuine ambiguity — fixed 2026-07-06).",
    ),
    (
        "আমার টমেটো গাছ ঢলে পড়ছে",
        "tomato",
        "Ambiguous between Fusarium wilt (yellowing before wilting) and bacterial wilt (fast wilt, no yellowing) — should ask whether leaves yellowed first.",
    ),
    (
        "গমের পাতায় দাগ দেখা যাচ্ছে",
        "wheat",
        "Ambiguous across wheat blast (small water-soaked eye-shaped grey leaf spots), leaf spot/spot blotch (elongated brown-blackish spots with tan center), and stem rust (reddish-brown pustules) — should ask about shape/color and whether the spike is also affected. Also checks whether wheat blast (duplicated across two source docs) is over-favored just from repetition.",
    ),
    (
        "তামাক গাছ ঢলে পড়ছে",
        "tobacco",
        "Ambiguous across black shank (black lesions at stem base, banded discoloration inside stem), Fusarium wilt (one-sided yellowing first), and bacterial wilt (milky ooze, no yellowing) — should ask about lesion color at the base, yellowing pattern, or ooze from a cut stem.",
    ),
    (
        "ভুট্টার পাতায় দাগ ও ক্ষতি দেখা যাচ্ছে",
        "maize",
        "Ambiguous across Turcicum leaf blight (cigar-shaped grey-tan lesions), common rust (round reddish-brown pustules), downy mildew (pale streaking parallel to veins), and fall armyworm (holes/window-pane patches, a pest not a disease) — should ask whether the damage is holes/frass (pest) vs. spots/lesions (disease), and if disease, the lesion shape. Also checks whether FAW (duplicated across two source docs) is over-favored just from repetition.",
    ),
]

# ---------------------------------------------------------------------------
# 3. GROUNDING STRESS TESTS — named in doc's disease list, but no symptoms given
# ---------------------------------------------------------------------------
GROUNDING_STRESS_CASES = [
    (
        "পাটের লিফ স্পট রোগের লক্ষণ কী?",
        "jute",
        "Doc lists 'Leaf spot (Cercospora corchori)' by name only, no symptom description. Should NOT confidently describe symptoms it wasn't given — check if it hallucinates general plant-pathology knowledge instead of admitting the doc lacks detail.",
    ),
    (
        "পাটে রুট নট বা শিকড়ে গিঁট রোগ কীভাবে বুঝব?",
        "jute",
        "Same issue — root-knot nematode is named but undescribed in the doc.",
    ),
]

# ---------------------------------------------------------------------------
# 4. ADVERSARIAL — messy, real-world-style input
# ---------------------------------------------------------------------------
ADVERSARIAL_CASES = [
    ("পাতা হলুদ হয়ে যাচ্ছে", "unspecified", "No crop named at all — check it asks which crop rather than guessing."),
    ("আমার দান গাছের পাতায় দাগ", "rice (misspelled ধান as দান)", "Misspelled/phonetic crop name — check it still recognizes rice, or asks for clarification instead of silently failing."),
    ("আমার ধান আর আলু দুটোতেই পাতায় দাগ দেখা যাচ্ছে", "rice + potato (mixed)", "Two crops in one question — check it addresses both or asks which one first, rather than answering only one silently."),
    ("আজকে আবহাওয়া কেমন থাকবে?", "n/a", "Off-topic (weather) — check it declines gracefully rather than forcing a crop-disease answer."),
    ("চালের দাম কত এখন?", "n/a", "Off-topic (market price) — check graceful decline."),
    ("আসসালামু আলাইকুম", "n/a", "Greeting only, no question — check it doesn't hallucinate a diagnosis."),
    ("আমার ভুট্টা গাছে পোকা দেখা যাচ্ছে", "corn (not covered)", "Genuinely out-of-scope crop — should decline, not guess from general knowledge."),
    ("", "n/a", "Empty string — check it doesn't crash or return something nonsensical."),
    ("asdkjfh qwoeiuroiu ৩২৪৩২", "n/a", "Gibberish input — check graceful handling."),
]

# ---------------------------------------------------------------------------
# 5. CONSISTENCY — same question, repeated, checking for flip-flopping
# ---------------------------------------------------------------------------
CONSISTENCY_CASES = [
    ("আমার ধানের পাতায় চোখের মতো দাগ দেখা যাচ্ছে", "rice", "direct-answer case — diagnosis should be identical every run"),
    ("আমার আলুর গাছে সাদা পোকা দেখা যাচ্ছে", "potato", "decline case — decision (decline vs guess) should be identical every run"),
    ("আমার পাটের গাছে কালো দাগ দেখা যাচ্ছে", "jute", "ambiguous case — check whether it flips between answering directly and asking to clarify"),
    ("গমের পাতায় দাগ দেখা যাচ্ছে", "wheat", "duplication-bias case — wheat blast is repeated across two source docs; check it doesn't get silently favored and that the clarify decision is stable"),
    ("ভুট্টার পাতায় দাগ ও ক্ষতি দেখা যাচ্ছে", "maize", "duplication-bias case — FAW is repeated across two source docs; check it doesn't get silently favored and that the clarify decision is stable"),
]


def _write_rows(writer, run_id, rows):
    for question, crop, category, expected in rows:
        print(f"[{category}] {question[:50]}")
        answer = answer_question(question, CROP_DOCS, COMBINED_DOCS)
        writer.writerow([
            run_id,
            datetime.now().isoformat(timespec="seconds"),
            category,
            crop,
            question,
            expected,
            answer,
            "", "", "", "",  # grounded, correct_behavior, simple, bangla_quality, notes
        ])


def run_eval():
    global CROP_DOCS, COMBINED_DOCS
    CROP_DOCS = load_crop_docs()
    COMBINED_DOCS = "\n\n".join(filter(None, CROP_DOCS.values()))
    print(f"Loaded reference docs: {len(COMBINED_DOCS)} characters\n")

    run_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    csv_path = EVAL_CSV_PATH
    file_exists = os.path.isfile(csv_path)

    if file_exists:
        with open(csv_path, encoding="utf-8-sig") as f:
            existing_header = next(csv.reader(f), [])
        if existing_header != EXPECTED_HEADER:
            # Schema changed since this file was created (e.g. an older
            # version of this script wrote it). Appending now would
            # silently misalign columns, like it did before. Write to a
            # fresh, clearly-named file instead of corrupting the old one.
            csv_path = f"eval_{run_id}.csv"
            file_exists = False
            print(
                f"⚠️  {EVAL_CSV_PATH} has an older/different column layout "
                f"than this script produces. Writing to {csv_path} instead "
                f"so columns don't get misaligned. You can manually merge "
                f"the two files later if needed."
            )

    with open(csv_path, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow(EXPECTED_HEADER)

        _write_rows(writer, run_id, [
            (q, c, "coverage", e) for q, c, e in COVERAGE_CASES
        ])
        _write_rows(writer, run_id, [
            (q, c, "rule3_clarify", e) for q, c, e in RULE3_CLARIFY_CASES
        ])
        _write_rows(writer, run_id, [
            (q, c, "grounding_stress", e) for q, c, e in GROUNDING_STRESS_CASES
        ])
        _write_rows(writer, run_id, [
            (q, c, "adversarial", e) for q, c, e in ADVERSARIAL_CASES
        ])

        # Consistency: repeat each case N times, labeled with repeat index
        for question, crop, expected in CONSISTENCY_CASES:
            for i in range(1, CONSISTENCY_REPEATS + 1):
                print(f"[consistency #{i}] {question[:50]}")
                answer = answer_question(question, CROP_DOCS, COMBINED_DOCS)
                writer.writerow([
                    run_id,
                    datetime.now().isoformat(timespec="seconds"),
                    f"consistency_run{i}",
                    crop,
                    question,
                    expected,
                    answer,
                    "", "", "", "",
                ])

    total = (
        len(COVERAGE_CASES) + len(RULE3_CLARIFY_CASES) + len(GROUNDING_STRESS_CASES)
        + len(ADVERSARIAL_CASES) + len(CONSISTENCY_CASES) * CONSISTENCY_REPEATS
    )
    print(f"\nDone. {total} rows appended to {csv_path} under run_id={run_id}")


if __name__ == "__main__":
    run_eval()
