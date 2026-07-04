"""
KrishiKotha — Photo Diagnosis Go/No-Go Test
--------------------------------------------
Sends crop disease photos to GPT-4o (vision) and asks it to diagnose
the crop/disease in Bangla. Logs results to outputs/ and evaluation.csv
so the team can judge whether the photo feature is reliable enough to
keep in scope.

Usage:
    1. Put 2-3 test photos in the images/ folder (jpg/jpeg/png)
    2. Copy .env.example to .env and add your real OpenAI API key
    3. Run: python test.py
    4. Open evaluation.csv and fill in the "correct_diagnosis" column
       by eye (yes / partial / no) after reading each response.
"""

import base64
import csv
import json
import os
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

IMAGES_DIR = Path("images")
OUTPUTS_DIR = Path("outputs")
EVAL_CSV = Path("evaluation.csv")

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

PROMPT = """You are an agricultural expert helping Bangladeshi farmers who cannot read \
well and are speaking through a voice assistant called KrishiKotha.

Look at this crop photo carefully and respond in Bangla.

Return your answer as a single JSON object with exactly these keys, and nothing else \
(no markdown, no code fences, no extra text):

{
  "crop": "the crop you see, e.g. dhan (rice), alu (potato), pat (jute), or 'unclear'",
  "diagnosis": "the disease or pest problem you identify, in Bangla, or 'সুস্থ মনে হচ্ছে' if healthy, or 'নিশ্চিত নই' if you cannot tell",
  "confidence": "low, medium, or high",
  "advice_bangla": "1-2 short sentences of practical next-step advice for the farmer, in Bangla",
  "reasoning_english": "a short English note for the dev team explaining what visual cues led to this diagnosis"
}

Be honest. If the photo is unclear, blurry, or you are not confident, say so in the \
diagnosis field and set confidence to "low" rather than guessing."""


def encode_image(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def guess_media_type(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in (".jpg", ".jpeg"):
        return "image/jpeg"
    if ext == ".png":
        return "image/png"
    if ext == ".webp":
        return "image/webp"
    return "image/jpeg"


def diagnose_image(client: OpenAI, image_path: Path) -> dict:
    b64_image = encode_image(image_path)
    media_type = guess_media_type(image_path)

    start = time.time()
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{media_type};base64,{b64_image}"},
                    },
                ],
            }
        ],
        max_tokens=500,
    )
    elapsed = round(time.time() - start, 2)

    raw_text = response.choices[0].message.content.strip()

    # Strip accidental markdown code fences if the model adds them anyway
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.lower().startswith("json"):
            raw_text = raw_text[4:].strip()

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        parsed = {
            "crop": "PARSE_ERROR",
            "diagnosis": "PARSE_ERROR",
            "confidence": "n/a",
            "advice_bangla": "n/a",
            "reasoning_english": "Model did not return valid JSON. See raw output.",
        }

    return {
        "image": image_path.name,
        "response_time_sec": elapsed,
        "parsed": parsed,
        "raw_text": raw_text,
    }


def save_raw_output(result: dict):
    out_path = OUTPUTS_DIR / f"{Path(result['image']).stem}_response.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


def append_to_csv(result: dict):
    file_exists = EVAL_CSV.exists()
    with open(EVAL_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow([
                "timestamp",
                "image",
                "crop_predicted",
                "diagnosis_predicted",
                "confidence",
                "advice_bangla",
                "response_time_sec",
                "correct_diagnosis (fill: yes/partial/no)",
                "bangla_quality (fill: good/ok/broken)",
                "notes",
            ])
        parsed = result["parsed"]
        writer.writerow([
            datetime.now().isoformat(timespec="seconds"),
            result["image"],
            parsed.get("crop", ""),
            parsed.get("diagnosis", ""),
            parsed.get("confidence", ""),
            parsed.get("advice_bangla", ""),
            result["response_time_sec"],
            "",  # to be filled manually
            "",  # to be filled manually
            "",  # to be filled manually
        ])


def main():
    if not API_KEY:
        raise SystemExit(
            "OPENAI_API_KEY not found. Copy .env.example to .env and add your real key."
        )

    OUTPUTS_DIR.mkdir(exist_ok=True)

    image_paths = sorted(
        p for p in IMAGES_DIR.iterdir() if p.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    if not image_paths:
        raise SystemExit(
            f"No images found in {IMAGES_DIR}/. Add 2-3 test photos (jpg/png) and re-run."
        )

    client = OpenAI(api_key=API_KEY)

    print(f"Found {len(image_paths)} image(s). Using model: {MODEL}\n")

    for image_path in image_paths:
        print(f"-> Diagnosing {image_path.name} ...")
        try:
            result = diagnose_image(client, image_path)
        except Exception as e:
            print(f"   ERROR on {image_path.name}: {e}\n")
            continue

        save_raw_output(result)
        append_to_csv(result)

        parsed = result["parsed"]
        print(f"   Crop: {parsed.get('crop')}")
        print(f"   Diagnosis: {parsed.get('diagnosis')}")
        print(f"   Confidence: {parsed.get('confidence')}")
        print(f"   Time: {result['response_time_sec']}s")
        print()

    print(f"Done. Raw responses saved in {OUTPUTS_DIR}/, summary logged in {EVAL_CSV}")
    print("Next: open evaluation.csv and fill in correct_diagnosis + bangla_quality by eye.")


if __name__ == "__main__":
    main()
