"""
Compare improved (grounded + crop pre-selection) diagnosis
against the Day 1 baseline results.

Usage:
    1. Make sure images/ still has your Day 1 test photos
    2. Edit TEST_SET below to map each image filename to its known crop
       and (optionally) the expected/actual disease for scoring
    3. Run: python compare_day2.py
    4. Open evaluation_day2.csv and fill in correct_diagnosis by eye,
       same as Day 1 — then compare the "yes" rate against day 1.
"""

import csv
from datetime import datetime
from pathlib import Path

from diagnose import diagnose_photo

# Edit this to match your actual Day 1 test images and their known crop.
# expected_disease is optional — fill in if you know ground truth, for
# quick eyeball scoring; leave blank if you don't have confirmed labels.
TEST_SET = [
    {"image": "images/rice_blast_01.jpg", "crop": "rice", "expected_disease": ""},
    {"image": "images/potato_early_blight_01.jpg", "crop": "potato", "expected_disease": ""},
    {"image": "images/jute_stem_01.jpg", "crop": "jute", "expected_disease": ""},
]

OUTPUT_CSV = Path("evaluation_day2.csv")


def run_comparison():
    file_exists = OUTPUT_CSV.exists()
    with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow([
                "timestamp",
                "image",
                "crop_given",
                "diagnosis",
                "confidence",
                "advice_bangla",
                "found_in_documents",
                "response_time_sec",
                "expected_disease",
                "correct_diagnosis (fill: yes/partial/no)",
                "notes",
            ])

        for item in TEST_SET:
            image_path = Path(item["image"])
            if not image_path.exists():
                print(f"SKIP — not found: {image_path}")
                continue

            print(f"-> Diagnosing {image_path.name} (crop: {item['crop']}) ...")
            try:
                result = diagnose_photo(str(image_path), item["crop"])
            except Exception as e:
                print(f"   ERROR: {e}\n")
                continue

            writer.writerow([
                datetime.now().isoformat(timespec="seconds"),
                image_path.name,
                item["crop"],
                result.get("diagnosis", ""),
                result.get("confidence", ""),
                result.get("advice_bangla", ""),
                result.get("found_in_documents", ""),
                result.get("response_time_sec", ""),
                item.get("expected_disease", ""),
                "",  # fill manually
                "",  # fill manually
            ])

            print(f"   Diagnosis: {result.get('diagnosis')}")
            print(f"   Confidence: {result.get('confidence')}")
            print(f"   Found in documents: {result.get('found_in_documents')}")
            print(f"   Time: {result.get('response_time_sec')}s\n")

    print(f"Done. Compare {OUTPUT_CSV} against Day 1's evaluation.csv:")
    print("  - Did 'correct_diagnosis = yes' rate go up?")
    print("  - Did the model say grounded_in_docs = true where you expect it to?")
    print("  - Did confidence become more honest (lower on genuinely unclear cases)?")


if __name__ == "__main__":
    run_comparison()
