"""
Shared document loading — single source of truth for both the text Q&A
pipeline (Person B) and the photo diagnosis pipeline (Person C).

Both pipelines should import CROP_FILES / load_crop_docs from HERE instead
of keeping separate copies, so adding/renaming a reference file only needs
to happen in one place.
"""

# Which raw text files belong to each crop's reference material.
# These are unstructured prose extracted from PDFs/leaflets — no "##"
# headers, multiple diseases often described in the same file.
CROP_FILES = {
    "rice": [
        "ধানের_খোলপোড়া_রোগ.txt",
        "ধানের_চারাপোড়া_রোগ.txt",
        "ধানের_টুংরো_রোগ.txt",
        "ধানের_ব্লাস্ট_রোগ_কৃষকদের_করণীয়.txt",
        "ধানের_ব্লাস্ট_রোগ.txt"
    ],
    "jute": ["14-Diseases-of-Jute.txt"],
    "beans": ["bean.txt", "bean 2.txt", "bean3.txt"],
    "lemon": ["lemon.txt"],
    "mustard": ["shorisha_aphid_disease_summary.txt", "shorisha_blight_white_mold_summary.txt"],
    "potato": ["আলুর_রোগ_ও_প্রতিকার.txt"],
    "tomato": ["tomato.txt"],
    "wheat": ["Wheat_Diseases_Bangladesh.txt", "Wheat_Blast_Disease_Info.txt"],
    "tobacco": ["Tobacco_Diseases_Bangladesh.txt"],
    "maize": ["Maize_Diseases_Bangladesh.txt", "Fall_Armyworm_FAW_Info.txt"],
}

# Keywords (including common spelling variants) used to detect which crop(s)
# a farmer's TEXT question is about. Not needed for photo diagnosis, since
# the crop is already known there (from a UI dropdown / pre-selection), but
# kept here so Person B's text pipeline can import it from the same place.
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

DOCUMENTS_DIR = "documents"


def load_doc(filepath):
    """Load a text file safely, warning if it's missing."""
    import os
    full_path = os.path.join(DOCUMENTS_DIR, filepath)
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"WARNING: File not found — {full_path}")
        return ""


def load_crop_docs():
    """Load reference text for each crop separately.

    Returns {crop_name: combined_text_for_that_crop}, joining all files
    listed for that crop in CROP_FILES.
    """
    return {
        crop: "\n\n".join(filter(None, [load_doc(f) for f in files]))
        for crop, files in CROP_FILES.items()
    }


def get_available_crops():
    """Returns the list of crop names that have reference documents."""
    return list(CROP_FILES.keys())
