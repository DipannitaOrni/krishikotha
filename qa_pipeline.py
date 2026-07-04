from dotenv import load_dotenv
import os
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def load_doc(filepath):
    """Load a text file safely, warning if it's missing."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"⚠️  WARNING: File not found — {filepath}")
        return ""


def get_answer(question, reference_docs):
    prompt = f"""You are a helpful farming assistant for Bangladeshi farmers. 
Using ONLY the reference material below, answer the farmer's question 
simply and clearly in Bangla.

Follow these rules in order:
1. If the question is about a crop or topic NOT mentioned anywhere in the 
   reference material at all, say honestly that you don't have reliable 
   information on that topic, and suggest contacting a local agricultural 
   officer. Do NOT ask a clarifying question in this case.
2. If the question is about a crop that IS covered, and the symptoms 
   described clearly and specifically match a condition in the reference 
   material, give a direct, confident answer with the diagnosis and treatment. 
   Do NOT ask an unnecessary clarifying question if you already have enough 
   information to answer.
3. Only ask ONE clarifying question if the crop is covered, but the symptoms 
   described are too vague to distinguish between two or more possible 
   conditions in the reference material.

Reference material:
{reference_docs}

Farmer's question:
{question}"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    # --- Rice ---
    rice_docs = "\n\n".join(filter(None, [
        load_doc("ধানের_খোলপোড়া_রোগ.txt"),
        load_doc("ধানের_চারাপোড়া_রোগ.txt"),
        load_doc("ধানের_টুংরো_রোগ.txt"),
        load_doc("ধানের_ব্লাস্ট_রোগ_কৃষকদের_করণীয়.txt"),
    ]))

    # --- Jute ---
    jute_docs = load_doc("14-Diseases-of-Jute.txt")

    # --- Beans ---
    beans_docs = "\n\n".join(filter(None, [
        load_doc("bean.txt"),
        load_doc("bean 2.txt"),
        load_doc("bean3.txt"),
    ]))

    # --- Lemon ---
    lemon_docs = load_doc("lemon.txt")

    combined_docs = "\n\n".join(filter(None, [rice_docs, jute_docs, beans_docs, lemon_docs]))

    print(f"Total combined document length: {len(combined_docs)} characters\n")

    # --- Test questions across crops ---
    test_questions = [
        "আমার ধানের পাতায় চোখের মতো দাগ দেখা যাচ্ছে",       # rice blast
        "আমার পাটের গাছে কালো দাগ দেখা যাচ্ছে",              # jute (ambiguous)
        "আমার শিমের ফলে ছিদ্র দেখা যাচ্ছে",                  # bean pod borer
        "আমার লেবু গাছের পাতায় হলুদ দাগ দেখা যাচ্ছে",         # lemon canker
    ]

    for q in test_questions:
        print(f"Question: {q}")
        print(get_answer(q, combined_docs))
        print("\n" + "="*60 + "\n")

    print("--- Specific rice symptom (should answer directly) ---")
    print(get_answer(
        "আমার ধানের ডিগ পাতা ও শীষের গোড়ায় কালচে বাদামি দাগ, ঘন কুয়াশার সময়",
        combined_docs
    ))
    print()

    print("--- Potato (genuinely out of scope, should decline) ---")
    print(get_answer("আমার আলুর গাছে সাদা পোকা দেখা যাচ্ছে", combined_docs))