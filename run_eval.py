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
                           flips between runs at temperature 0.0.

Since the pipeline now runs in two calls (get_triage -> get_answer), each
row also logs the triage decision itself (situation + candidates), not just
the final Bangla text. This lets you catch a specific failure mode without
reading prose: situation == "multiple_match" but the answer contains no "?"
almost certainly means the answer call ignored its instruction, and
situation/candidates that look wrong on their own face (e.g. only 1
candidate for a case you know is 3-way ambiguous) point at the triage
prompt rather than the answer prompt.

Usage:
    python run_eval.py

Results append to eval.csv with blank columns for manual scoring:
    grounded (y/n), correct_behavior (y/n), simple (y/n), bangla_quality (y/n), notes

NOTE ON SCHEMA CHANGE: this version's header adds "situation" and
"candidates" columns that did not exist before. The existing schema-mismatch
guard below will detect that eval.csv was written by the older single-column
script and automatically start a fresh eval_<run_id>.csv instead of
misaligning columns — you don't need to do anything manually, but you will
end up with two files to merge if you want one combined history.
"""

import csv
import json
import os
from datetime import datetime

from qa_pipeline_restructured import load_crop_docs, answer_question

EVAL_CSV_PATH = "eval.csv"
CONSISTENCY_REPEATS = 3

EXPECTED_HEADER = [
    "run_id", "timestamp", "category", "crop", "question",
    "expected_behavior", "situation", "candidates", "answer",
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

    # Cotton (full coverage — 8 diseases)
    ("তুলার চারার বীজপত্র হলুদ হয়ে বাদামি হচ্ছে, বোঁটার গোড়ায় বাদামি রিং, গোড়ার পুরনো পাতা থেকে উপরের দিকে ঢলে যাচ্ছে", "cotton", "Fusarium wilt"),
    ("তুলা পাতায় শিরার মাঝে হলুদ ভাব, কিনারা শুকিয়ে বাঘের ডোরার মতো দাগ, কান্ড কাটলে গোলাপি রং", "cotton", "Verticillium wilt (\"tiger stripe\")"),
    ("তুলা গাছ হঠাৎ ঢলে পড়ছে জমিতে গুচ্ছ আকারে, শিকড় পচে গেছে শুধু মূল শিকড় ছাড়া, বাকলে কালচে বাদামি দানার মতো জিনিস", "cotton", "Root rot"),
    ("তুলার বলে ছোট পানিভেজা লালচে-বাদামি বসা দাগ, তুলার আঁশ হলুদ-বাদামি দাগযুক্ত ও শক্ত হয়ে যাচ্ছে", "cotton", "Anthracnose"),
    ("তুলার বল কালো দাগে ভরে গিয়ে পচে যাচ্ছে, বল ফাটছে না, বল ঝরে পড়ছে", "cotton", "Boll rot"),
    ("তুলা পাতায় ছোট গোলাকার বাদামি দাগ, দাগের মধ্যে চক্রাকার বলয় (রিং), দাগ একসাথে মিশে পাতা ঝরে পড়ছে", "cotton", "Leaf blight (Alternaria)"),
    ("তুলা পাতায় কৌণিক পানিভেজা দাগ শিরা দ্বারা সীমাবদ্ধ, কান্ডে কালো লম্বাটে দাগ, ডাল ভেঙে শুকনো কালো ডালের মতো ঝুলে আছে", "cotton", "Bacterial blight (\"black arm\" phase)"),
    ("তুলা পাতা উপরে-নিচে কুঁকড়ে যাচ্ছে, শিরা মোটা হয়ে যাচ্ছে, পাতার নিচে ছোট ছোট বাড়তি অংশ (এনেশন)", "cotton", "Leaf curl disease (CLCuV)"),

    # Sugarcane (full coverage — 11 diseases)
    ("আখ কাটলে ভেতরে লাল রং এবং মদের মতো গন্ধ বের হচ্ছে, পাতার মধ্যশিরায় লাল দাগ", "sugarcane", "Red rot"),
    ("আখ গাছ ৪-৫ মাস বয়সে হলুদ হয়ে শুকিয়ে ঢলে পড়ছে, চিরে দেখলে ভেতরে বেগুনি-লাল দাগ ও দুর্গন্ধ, সাদা তুলার মতো ছত্রাক", "sugarcane", "Stem canker / wilt"),
    ("আখ পাতায় মধ্যশিরা বরাবর সাদা-ক্রিম রঙের সমান্তরাল ডোরা, গাছ খাটো হয়ে যাচ্ছে পার্শ্ব কুশি ছাড়াই", "sugarcane", "White leaf disease"),
    ("আখ গাছের মাথা থেকে লম্বা কালো চাবুকের মতো পাকানো কান্ড বের হয়েছে, রূপালি পর্দায় ঢাকা", "sugarcane", "Whip smut"),
    ("আখ গাছ খাটো, কুশি কম, চিরলে গিঁটে ফোঁটা বা কমার মতো রঙিন দাগ দেখা যাচ্ছে কিন্তু বাইরে তেমন লক্ষণ নেই", "sugarcane", "Ratoon stunting disease (RSD)"),
    ("আখের সেট রোপণের ২-৩ সপ্তাহ পর পচে যাচ্ছে, আনারসের মতো গন্ধ বের হচ্ছে", "sugarcane", "Sett rot / pineapple disease"),
    ("আখ পাতায় মধ্যশিরা থেকে কিনারা পর্যন্ত সরু সাদা পেন্সিলের রেখার মতো দাগ শিরার সমান্তরালে", "sugarcane", "Leaf scald"),
    ("আখের কচি পাতায় হলুদাভ ডোরা স্বাভাবিক সবুজ অংশের সাথে পালাক্রমে, গাছ খাটো ও হলদেটে", "sugarcane", "Mosaic"),
    ("আখ পাতায় ক্লোরোটিক দাগে গাঢ় লাল রেখা, কান্ড ফাটালে দুর্গন্ধযুক্ত হলদে আঠা বের হচ্ছে", "sugarcane", "Red-stripe & top rot"),
    ("আখ গাছ খাটো ও হলদেটে, শিকড় খুঁড়লে গিঁটযুক্ত ফোলা দেখা যাচ্ছে", "sugarcane", "Root-knot disease"),
    ("আখের কচি পাতা পেঁচিয়ে ও কুঁচকে যাচ্ছে, গোড়া স্বাভাবিকের চেয়ে সরু, পরে সিঁড়ির ধাপের মতো দাগ কান্ডে", "sugarcane", "Pokkah boeng"),

    # Tea (full coverage of diseases with described symptoms — 8 of 10; Horse Hair Blight
    # and Branch Canker have no symptom text in the doc, see GROUNDING_STRESS_CASES)
    ("চা পাতায় হলুদ বা ছাই রঙের উঁচু ছোট ছোট গোলাকার দাগ, মার্চ-মে মাসে বেশি দেখা যাচ্ছে", "tea", "Algal leaf rust / red rust"),
    ("চা পাতা পচে কালো হয়ে যাচ্ছে", "tea", "Black rot"),
    ("চা গাছের ডালে সুতার মতো ছত্রাকের জাল জড়িয়ে আছে", "tea", "Thread blight"),
    ("চা পাতায় বাদামি অনিয়মিত দাগ, দাগের কেন্দ্রে হালকা ছাই রং এবং চারপাশে গাঢ় সীমানা, পুরনো পাতায় বেশি", "tea", "Brown blight"),
    ("চা পাতার কিনারা বা আগা থেকে ধূসর রঙের দাগ শুরু হয়ে ছড়াচ্ছে, দাগের মধ্যে কালো বিন্দু দেখা যাচ্ছে", "tea", "Grey blight"),
    ("চা গাছের শিকড় পচে যাচ্ছে, শিকড়ে লালচে-বাদামি ছত্রাকের তন্তু জমেছে, গাছ ধীরে ধীরে হলুদ হয়ে শুকিয়ে যাচ্ছে", "tea", "Red root rot"),
    ("চা পাতায় অনিয়মিত বাদামি-কালচে দাগ, আক্রান্ত অংশ শুকিয়ে ঝরে পড়ছে", "tea", "Leaf anthracnose"),
    ("চা গাছের ডালের আগা থেকে শুকাতে শুরু করে ক্রমশ নিচের দিকে নামছে, দুর্বল গাছে বেশি", "tea", "Dieback"),

    # Mango (representative subset of 20 — same convention as potato — spanning every
    # category: fungal major/minor, algal, bacterial, nematode, non-pathogenic)
    ("আম গাছের মুকুল কালো হয়ে শুকিয়ে ঝরে যাচ্ছে, ফলে কালো বসা দাগ", "mango", "Anthracnose"),
    ("আম গাছের মুকুল ও কচি পাতায় সাদা পাউডারের মতো আস্তরণ পড়েছে", "mango", "Powdery mildew"),
    ("আম গাছের মুকুল ছোট ঘন গুচ্ছাকার হয়ে বিকৃত হয়ে গেছে, ফল ধরছে না", "mango", "Mango malformation"),
    ("আম গাছের ডালের আগা থেকে শুকাতে শুরু করে নিচের দিকে নামছে, ডাল ঝলসে যাচ্ছে", "mango", "Die-back"),
    ("আম ফলের বোঁটার বিপরীত প্রান্তে পচন শুরু হয়ে কালচে বাদামি হয়ে যাচ্ছে", "mango", "Fruit end rot"),
    ("আম ফলের বোঁটার গোড়া থেকে পচন শুরু হয়ে কালো হয়ে যাচ্ছে, ভেতরটাও কালো", "mango", "Diplodia/charcoal rot (stem-end-rot)"),
    ("আম পাতা ও ফলের উপর কালো ঝুরঝুরে কালির মতো আস্তরণ, গাছে মিলিবাগ বা এফিড আছে", "mango", "Sooty mold"),
    ("আম ফল ও কাণ্ডে উঁচু বাদামি খসখসে দাগ", "mango", "Mango scab"),
    ("আম পাতায় গোলাকার বাদামি দাগ কেন্দ্রে বৃত্তাকার রিং সহ", "mango", "Alternaria leaf spot"),
    ("আম পাতায় লালচে মরিচা রঙের গোলাকার দাগ, প্রথমে ছাই রঙ পরে লালচে", "mango", "Leaf red rust (algal)"),
    ("আম পাতা ও ফলে কর্কের মতো উঁচু বাদামি দাগ, চারপাশে হলদে বলয়", "mango", "Asiatic canker"),
    ("আম গাছের কাণ্ডে ডালের সংযোগস্থলে আলুর মতো উঁচু টিউমার/গোটা", "mango", "Crown gall"),
    ("আম চারার শিকড়ে ছোট ছোট গিঁট/গুটি, চারা বৃদ্ধিতে বাধাগ্রস্ত ও পাতা হলদে", "mango", "Root-knot nematode"),
    ("আম ফলের গায়ে ফাটল দেখা যাচ্ছে, রোগের লক্ষণ নেই", "mango", "Fruit cracking due to boron deficiency (non-pathogenic — check it doesn't misdiagnose as a disease)"),
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
    (
        "তুলা গাছ ঢলে পড়ছে",
        "cotton",
        "Ambiguous across Fusarium wilt (older leaves first, yellowing then browning, black vascular streaks), Verticillium wilt (bronzing/interveinal chlorosis, 'tiger stripe', pinkish woody tissue), and root rot (sudden complete wilting in patches, roots rotted except taproot) — should ask about which leaves wilted first, vascular colour when cut, and whether it's sudden/patchy vs. gradual.",
    ),
    (
        "তুলার বলে দাগ পড়ে পচে যাচ্ছে",
        "cotton",
        "Ambiguous across anthracnose (small reddish-brown depressed spots, lint stained yellow/brown), boll rot (black dots enlarging to cover whole boll, bolls never burst), and bacterial blight's square/boll rot phase (water-soaked lesions turning dark black with bacterial ooze staining lint yellow) — should ask about spot colour and whether any bacterial ooze is present.",
    ),
    (
        "আখ গাছ ঢলে পড়ছে এবং ভেতরের রঙ পরিবর্তন হয়ে গেছে",
        "sugarcane",
        "Ambiguous across red rot (blood-red lesions, alcoholic smell, red internal tissue with whitish patches), stem canker/wilt (purple/dark red pith discolouration near node, disagreeable odour, cottony white mycelium), and pokkah boeng (reddish streaks/ladder-like lesions, distorted young leaves) — should ask about the internal colour/smell and whether young leaves are twisted.",
    ),
    (
        "আখ পাতায় সাদা বা হলুদ ডোরা দেখা যাচ্ছে",
        "sugarcane",
        "Ambiguous between white leaf disease (pure white/cream stripes parallel to midrib, stunted with no side shoots) and mosaic (chlorotic yellowish-green stripes alternating with normal green, more on younger foliage, spread by aphids) — should ask about the exact stripe colour and whether tillering/side-shoot growth is affected.",
    ),
    (
        "চা পাতায় দাগ পড়ে ধীরে ধীরে শুকিয়ে যাচ্ছে",
        "tea",
        "Ambiguous across brown blight (brown spot, light ash centre, dark border), grey blight (grey/ash spot starting from edge/tip, black dot fruiting bodies inside), and leaf anthracnose (irregular brown-blackish spots, no defined ring/border) — should ask where on the leaf the spot started and whether black dots or a ringed centre are visible.",
    ),
    (
        "আম পাতায় পানিভেজা দাগ দেখা যাচ্ছে",
        "mango",
        "Ambiguous across three different bacterial diseases with overlapping symptoms: Bacterial leaf blight — Pseudomonas syringae (water-soaked spots turning brown/black), Bacterial leaf blight — Xanthomonas campestris pv. mangiferae-indicae (irregular water-soaked spots spreading to leaf scorch), and Asiatic canker (raised corky brown lesions with yellow halo, once past the water-soaked stage) — should ask whether lesions are raised/corky vs. flat, and note that two distinct pathogens share the exact same disease name in this doc (duplication-bias check).",
    ),
    (
        "আম গাছের ডাল কালো হয়ে শুকিয়ে যাচ্ছে",
        "mango",
        "Ambiguous between anthracnose (twig-tip blackening, worse in wet/humid weather) and die-back (Botryosphaeria theobromae, tip-to-base drying, worse in weak/injured/old trees, not tied to a specific season) — should ask about recent weather and whether the tree was previously injured or old/weak.",
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
    (
        "চা গাছে হর্স হেয়ার ব্লাইট রোগের লক্ষণ কী?",
        "tea",
        "Doc names 'Horse Hair Blight (Marasmius equicrinis)' and gives management only, no symptom description at all. Should NOT invent symptoms — check if it hallucinates from general plant-pathology knowledge instead of admitting the doc lacks detail.",
    ),
    (
        "চা গাছে ব্রাঞ্চ ক্যাংকার রোগের লক্ষণ কী?",
        "tea",
        "Same issue — 'Branch Canker' is named in the doc with management steps only (cutting back infected wood, fungicide paste), no symptom text given at all.",
    ),
    (
        "সুগারকেন হোয়াইট লিফ ডিজিজ কীভাবে দমন করব?",
        "sugarcane",
        "Doc gives full symptom text for white leaf disease but explicitly states favourable conditions, disease cycle, and management are 'not specified in source document'. Should NOT invent a management/control regimen — check it admits the doc has no control measures for this one, rather than borrowing generic phytoplasma advice.",
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
    ("আমগাছে ফলে কালো দাগ পড়েছে", "mango (no-space compound 'আমগাছে')", "Crop-keyword bug check: CROP_KEYWORDS for mango only match 'আম গাছ'/'আমের'/'আম বাগান' (with a space); the natural no-space compound 'আমগাছে' may not match any of them. Check whether it still recognizes mango or silently fails/asks which crop instead of just answering correctly by luck."),
    ("চাগাছের পাতায় দাগ পড়েছে", "tea (no-space compound 'চাগাছের')", "Same crop-keyword bug check for tea: CROP_KEYWORDS require 'চা গাছ'/'চা বাগান'/'চায়ের' with a space; 'চাগাছের' has no space and may not match. Check graceful handling rather than a silent miss."),
    ("আমার তুলা আর আখ দুটো গাছই ঢলে পড়ছে", "cotton + sugarcane (mixed)", "Two crops in one question — check it addresses both or asks which one first, rather than silently answering only one (same pattern as the existing rice+potato case)."),
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
    ("তুলা গাছ ঢলে পড়ছে", "cotton", "ambiguous case across Fusarium wilt / Verticillium wilt / root rot — check whether it flips between answering directly and asking to clarify"),
    ("আম পাতায় পানিভেজা দাগ দেখা যাচ্ছে", "mango", "duplication-bias case — two distinct diseases in the doc are both literally named 'Bacterial Leaf Blight' (Pseudomonas syringae vs Xanthomonas campestris); check it doesn't arbitrarily/inconsistently favor one pathogen and that the clarify decision is stable"),
]


def _row_from_result(run_id, category, crop, question, expected, answer, triage):
    return [
        run_id,
        datetime.now().isoformat(timespec="seconds"),
        category,
        crop,
        question,
        expected,
        triage.get("situation", ""),
        json.dumps(triage.get("candidates", []), ensure_ascii=False),
        answer,
        "", "", "", "",  # grounded, correct_behavior, simple, bangla_quality, notes
    ]


def _write_rows(writer, run_id, rows):
    for question, crop, category, expected in rows:
        print(f"[{category}] {question[:50]}")
        answer, triage = answer_question(
            question, CROP_DOCS, COMBINED_DOCS, return_triage=True
        )
        writer.writerow(
            _row_from_result(run_id, category, crop, question, expected, answer, triage)
        )


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
            # version of this script wrote it, or — as of this version —
            # the "situation"/"candidates" columns were added for the
            # two-call pipeline). Appending now would silently misalign
            # columns. Write to a fresh, clearly-named file instead of
            # corrupting the old one.
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
                answer, triage = answer_question(
                    question, CROP_DOCS, COMBINED_DOCS, return_triage=True
                )
                writer.writerow(
                    _row_from_result(
                        run_id, f"consistency_run{i}", crop, question, expected,
                        answer, triage,
                    )
                )

    total = (
        len(COVERAGE_CASES) + len(RULE3_CLARIFY_CASES) + len(GROUNDING_STRESS_CASES)
        + len(ADVERSARIAL_CASES) + len(CONSISTENCY_CASES) * CONSISTENCY_REPEATS
    )
    print(f"\nDone. {total} rows appended to {csv_path} under run_id={run_id}")


if __name__ == "__main__":
    run_eval()
