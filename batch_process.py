import re
import json
import argparse
from pathlib import Path

# ---------- CONFIG ----------
EXTRACTORS = {
    ".pdf": "pdf",
    ".docx": "docx",
}

CROPS = ["rice", "potato", "jute"]

# ---------- EXTRACTION ----------
def extract_pdf(path: Path) -> str:
    import pdfplumber
    text = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text.append(page.extract_text() or "")
    return "\n".join(text)


def extract_docx(path: Path) -> str:
    import docx
    doc = docx.Document(path)
    return "\n".join(p.text for p in doc.paragraphs)


def extract_file(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        return extract_pdf(path)
    elif path.suffix.lower() == ".docx":
        return extract_docx(path)
    return ""


# ---------- CLEANING ----------
def strip_noise(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)

    noise_patterns = [
        r"bangladesh .*? institute",
        r"department of agricultural extension",
        r"^\s*page\s*\d+",
        r"^\s*\d+\s*$",
        r"www\..*",
        r".*@.*",
    ]

    for p in noise_patterns:
        text = re.sub(p, "", text, flags=re.IGNORECASE | re.MULTILINE)

    return text.strip()


# ---------- CROP DETECTION (FIXED - IMPORTANT) ----------
def get_crop_from_path(file_path: Path) -> str:
    parts = [p.lower() for p in file_path.parts]
    for crop in CROPS:
        if crop in parts:
            return crop
    return "unknown"


# ---------- SIMPLE SYMPTOM NORMALIZER ----------
def normalize(text: str):
    text = text.lower()
    text = text.replace("পাতা", "leaf")
    text = text.replace("লাল", "red")
    text = text.replace("বাদামী", "brown")
    text = text.replace("দাগ", "spot")
    return text


# ---------- STRUCTURING ----------
def structure(text: str, file_path: Path):
    crop = get_crop_from_path(file_path)

    # crude disease guess (improvable later)
    title = file_path.stem.replace("_", " ")

    symptoms = []
    control = []

    # split rough sentences
    sentences = re.split(r"[।.\n]", text)

    for s in sentences:
        s = s.strip()
        if not s:
            continue

        if any(k in s for k in ["লক্ষণ", "symptom", "দাগ", "spot", "পচ", "rot"]):
            symptoms.append(normalize(s))

        if any(k in s for k in ["করণীয়", "control", "ব্যবস্থাপনা", "spray", "apply"]):
            control.append(s)

    # remove duplicates
    symptoms = list(set(symptoms))
    control = list(set(control))

    return {
        "crop": crop,
        "problem": title,
        "type": "unknown",
        "symptoms": symptoms,
        "control": control,
        "keywords": symptoms[:5],  # simple baseline
        "source_file": file_path.name
    }


# ---------- MAIN PIPELINE ----------
def process(input_dir: Path, clean_dir: Path, json_dir: Path):

    if not input_dir.exists():
        print(f"Missing: {input_dir}")
        return

    clean_dir.mkdir(parents=True, exist_ok=True)
    json_dir.mkdir(parents=True, exist_ok=True)

    files = [f for f in input_dir.rglob("*") if f.suffix.lower() in [".pdf", ".docx"]]

    if not files:
        print("No files found")
        return

    for f in files:
        try:
            raw = extract_file(f)
            cleaned = strip_noise(raw)

            structured = structure(cleaned, f)

            # save txt
            txt_path = clean_dir / f"{f.stem}.txt"
            txt_path.write_text(cleaned, encoding="utf-8")

            # save json
            json_path = json_dir / f"{f.stem}.json"
            json_path.write_text(
                json.dumps(structured, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

            print(f"OK: {f.name}")

        except Exception as e:
            print(f"FAIL: {f.name} -> {e}")


# ---------- RUN ----------
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="raw")
    ap.add_argument("--output", default=".")
    args = ap.parse_args()

    process(
        input_dir=Path(args.input),
        clean_dir=Path(args.output) / "clean",
        json_dir=Path(args.output) / "json"
    )