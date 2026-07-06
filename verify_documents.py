"""
Confirms Person A's real documents are actually where diagnose.py expects
them, for every crop listed in crop_documents.CROP_FILES.

Run: python verify_documents.py
"""

from crop_documents import CROP_FILES, load_crop_docs


def main():
    docs = load_crop_docs()

    print(f"Checking {len(CROP_FILES)} crops...\n")

    for crop, files in CROP_FILES.items():
        text = docs.get(crop, "")
        print(f"--- {crop} ---")
        print(f"  Expected files: {files}")
        print(f"  Combined length: {len(text)} characters")

        if len(text) == 0:
            print("  MISSING: none of the expected files were found/readable")
        elif len(text) < 100:
            print("  WARNING: suspiciously short — check file content")
        else:
            print("  OK")
            print(f"  Preview: {text[:120].strip()}...")
        print()

    missing = [crop for crop, text in docs.items() if not text]
    if missing:
        print(f"CROPS WITH NO DOCUMENTS LOADED: {missing}")
        print("Check that these files exist in documents/ with exact matching filenames.")
    else:
        print("All crops have at least some document content loaded.")


if __name__ == "__main__":
    main()
