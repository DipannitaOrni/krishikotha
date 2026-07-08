<!-- Replace this with your project logo/banner -->
<p align="center">
  <img src="./assets/krishikotha-banner.png" alt="KrishiKotha banner" width="600"/>
</p>

# KrishiKotha — Voice-First AI Farm Advisor for Bangladeshi Farmers

> A document-grounded, voice-first AI companion for smallholder farmers in Bangladesh — answering crop questions in Bangla by voice, text, or photo, using only verified DAE / BARI / BRRI reference material, and refusing to guess when it doesn't know.

**Event:** SciBlitz AI Challenge 2026 · Track D — Open Innovation · IEEE Student Branch, CUET

<!-- Optional: add a live demo link or concept video once available -->
<!-- **Live Demo:** [link] | **Demo video:** [link] -->

![Python](https://img.shields.io/badge/-Python-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/-Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![OpenAI](https://img.shields.io/badge/-GPT--4o-412991?logo=openai&logoColor=white)
![Whisper](https://img.shields.io/badge/-BanglaASR%20(Whisper)-000000?logo=openai&logoColor=white)
![gTTS](https://img.shields.io/badge/-gTTS-4285F4?logo=googlecloud&logoColor=white)
![Bangla](https://img.shields.io/badge/-বাংলা%20Language-006A4E?logoColor=white)

---

## Table of Contents

- [What is KrishiKotha?](#what-is-krishikotha)
- [Screenshots](#screenshots)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Tech Stack](#tech-stack)
- [Document Grounding Strategy](#document-grounding-strategy)
- [AI/ML Approach](#aiml-approach)
- [Results & Evaluation](#results--evaluation)
- [Getting Started](#getting-started)
- [Limitations](#limitations)
- [Future Work](#future-work)
- [Team](#team)

---

## What is KrishiKotha?

**KrishiKotha** (কৃষিকথা — *"farmer's conversation"*) is a voice-first AI advisory assistant that lets a farmer describe a crop problem the way they'd describe it to another person — by speaking, typing, or showing a photo — in Bangla, and get back a grounded, spoken answer.

A large share of Bangladesh's smallholder farmers face a persistent gap: extension officers are stretched thin, and most digital agriculture tools assume the user can read and type. When yellowing leaves or spreading spots show up on a rice, potato, or jute crop, the realistic options today are wait, guess, or ask a neighbor who's equally unsure — any of which can mean a lost harvest.

KrishiKotha closes that gap by never answering from the model's general knowledge alone. Every response is generated using retrieval-style grounding against a curated set of real agricultural reference documents from **DAE, BARI, and BRRI**, covering ten crops common in Bangladesh. If the answer isn't in the source material, KrishiKotha says so — it is deliberately designed to say *"I don't have reliable information on this"* rather than invent a plausible-sounding answer.

---

## Screenshots

<!--
  Add your app screenshots here. Suggested shots:
  1. Home / mode-selection screen
  2. Voice Q&A in action
  3. Photo Diagnosis result
  4. Seasonal Precaution Advisory for a selected district
  Recommended: 1200x750px PNGs, stored in an /assets or /docs/screenshots folder.
-->

<p align="center">
  <img src="./assets/screenshot-home.png" alt="KrishiKotha home screen" width="45%"/>
  <img src="./assets/screenshot-voice-qa.png" alt="Voice Q&A screen" width="45%"/>
</p>
<p align="center">
  <img src="./assets/screenshot-photo-diagnosis.png" alt="Photo diagnosis screen" width="45%"/>
  <img src="./assets/screenshot-seasonal-advisory.png" alt="Seasonal advisory screen" width="45%"/>
</p>

<!-- Optional: embed a short demo GIF or video -->
<!-- <p align="center"><img src="./assets/demo.gif" alt="KrishiKotha demo" width="700"/></p> -->

---

## Key Features

### Voice Q&A

The farmer speaks a question in Bangla and receives a spoken, grounded answer — no typing required, no reading required.

### Text Q&A

The same document-grounded engine, for users who prefer typing over speaking.

### Photo Diagnosis

The farmer selects their crop and uploads or captures a photo of the affected plant. The system diagnoses visible symptoms against the same reference documents used for voice and text — never guessing from the image alone.

### Seasonal Precaution Advisory

The farmer selects their district, and the system proactively surfaces which diseases and pests are commonly active for that district's major crops in the current month, along with preventive guidance — before a problem even appears.

### Anti-Hallucination by Design

The reasoning engine is instructed to enumerate every plausible match in the source material, ask a clarifying question instead of guessing when more than one condition fits, and never invent a symptom or treatment step that isn't written in the reference documents.

### Session-Aware Conversation

Follow-up questions like *"the same problem, but now on the stem too"* are understood in context, without the farmer needing to repeat themselves — all without requiring login or persistent storage.

---

## System Architecture

```
Farmer Input (Voice / Text / Photo)
        │
        ├── Voice ──► Speech-to-Text (BanglaASR, fine-tuned Whisper)
        │
        └── Photo ──► Vision Input (Photo + Crop selection)
                              │
                              ▼
              Document-Grounded Reasoning Engine
              (GPT-4o + curated DAE / BARI / BRRI documents)
                              │
                              ▼
                  Text-to-Speech (gTTS)
                              │
                              ▼
                Spoken + Written Answer to Farmer
```

<!-- Optional: swap the ASCII diagram above for an exported image -->
<!-- ![System architecture](./assets/architecture-diagram.png) -->

**Reference material:** ~18 curated DAE / BARI / BRRI disease & pest documents, spanning 10 crops.

---

## Tech Stack

| Layer                  | Technology                                                        |
| ----------------------- | ------------------------------------------------------------------ |
| Application shell       | Streamlit                                                          |
| Speech-to-Text          | `bangla-speech-processing/BanglaASR` (fine-tuned Whisper, via Hugging Face Transformers) |
| Answer Generation       | OpenAI GPT-4o, custom multi-step grounded-reasoning system prompt |
| Vision / Photo Diagnosis| GPT-4o vision                                                      |
| Text-to-Speech          | gTTS (Google Text-to-Speech)                                       |
| Document Grounding      | Keyword-based crop/document matching → direct context injection    |
| Conversation Memory     | Streamlit session state (session-scoped, no login)                 |
| Reference Sources       | DAE, BARI, BRRI — ~18 documents across 10 crops                    |

---

## Document Grounding Strategy

Rather than letting the model answer from general pretraining knowledge — which risks confidently wrong, non-localized, or fabricated advice — KrishiKotha grounds every answer in real reference material.

The team collected roughly **18 reference documents** covering common diseases and pests across **ten crops** (rice, potato, jute, wheat, maize, tomato, beans, lemon, mustard, and tobacco), sourced from DAE, BARI, and BRRI, several in Bangla.

Given the manageable document volume — well under what would justify a full vector-database RAG pipeline — the team used a simpler, equally sound approach for this scale: each farmer question is matched to the relevant crop's document set via keyword detection, and the matched document text is passed directly into the model's context window alongside the question, with explicit instructions to answer *only* from that material.

---

## AI/ML Approach

### Speech-to-Text

Bangla speech is transcribed using a Whisper model fine-tuned specifically for Bangla. An earlier attempt with the general multilingual Whisper model produced accurate phonetic transcription but frequently rendered it in Devanagari script instead of Bangla script — switching to the Bangla-specific fine-tuned checkpoint resolved this reliably.

### Document-Grounded Answer Generation

Answer generation uses GPT-4o with a carefully engineered system prompt enforcing explicit reasoning steps before any final answer:

1. **Identify the crop** — ask a clarifying question if genuinely ambiguous.
2. **Confirm coverage** — check the crop is actually covered by the reference material.
3. **Enumerate all plausible matches** — scan the full document rather than stopping at the first match.
4. **Resolve ambiguity** — answer directly if exactly one condition matches; ask one targeted clarifying question if multiple plausibly match.
5. **Stay in scope** — use only treatment steps present in the material for that specific condition, never borrowing from a neighboring disease.
6. **No invented symptoms** — never state a symptom that isn't written in the source material.

This design was refined specifically to counter observed failure modes such as document duplication biasing which diagnosis felt more "available," and surface-level word overlap causing misreads (e.g., an insect sighting misread as a fungal symptom purely because both mention "white").

### Photo-Based Diagnosis

Photo diagnosis uses GPT-4o's vision capability. The farmer selects their crop from a dropdown first — crop identification from an image is treated as a separate, less reliable problem than disease diagnosis, so it's given as known input rather than guessed.

The same reference documents and anti-hallucination reasoning steps used for text/voice are reused here, with an added visual-symptom-matching step. A safety check verifies the photo is plausibly consistent with the selected crop *before* attempting a diagnosis, surfacing a warning instead of a confidently wrong result if the photo shows a visually distinct crop.

### Text-to-Speech and Conversational Memory

Responses are converted to spoken Bangla using gTTS. A session-scoped conversation history (via Streamlit session state, no login or persistent storage) lets follow-up questions be answered with awareness of the immediately preceding exchange.

---

## Results & Evaluation

The system was validated through structured manual evaluation rather than assumed correctness. Sample farmer questions and test photographs — covering rice, potato, and jute conditions such as blast, brown spot, and early/late blight — were run through the pipeline and scored for:

- Diagnostic accuracy
- Appropriate use of clarifying questions under genuine ambiguity
- Absence of fabricated symptoms or treatments

Two evaluation passes were run for the photo pipeline specifically:

| Pass  | Setup                                                | Outcome                                                               |
| Day 1 | Crop guessed by the model, general knowledge only    | Baseline                                                              |
| Day 2 | Crop given, reference documents supplied (grounded)  | Qualitative improvement in reliability and hedging on ambiguous cases |

The end-to-end application was verified to function correctly across all four modes — voice, text, photo, and seasonal advisory — inside the deployed Streamlit interface, including the crop-mismatch safety check and session-based conversation memory.

---

## Getting Started

**Prerequisites**

- Python 3.10+
- An OpenAI API key (for GPT-4o answer generation and vision)
- ~2 GB free disk space for the Bangla Whisper model weights

### 1. Clone

```bash
git clone https://github.com/<your-org>/krishikotha.git
cd krishikotha
```

### 2. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Configure environment

Create a `.env` file in the project root:

```
OPENAI_API_KEY=sk-...
```

### 4. Run the app

```bash
streamlit run app.py
# Open http://localhost:8501
```

<!-- Optional: add a screenshot right here showing the app running locally -->
<!-- ![App running locally](./assets/screenshot-local-run.png) -->


## Future Work

- Expand document coverage to more crops and regional dialects
- Pilot with real extension officers to validate advice quality against expert judgment
- Explore on-device or open-weight models to reduce cost and single-provider dependency
- Add lightweight, optional accounts for farmers who want persistent history across visits

