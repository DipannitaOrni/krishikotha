"""
KrishiKotha — Combined App (Photo + Voice + Text)
----------------------------------------------------
Place at the REPO ROOT, next to followup_engine.py, Image/, Voice/, Text/.
Run with:  streamlit run combined_app.py   (from the repo root)

Three modes, chosen via a top-level selector:
  1. ছবি দিয়ে রোগ নির্ণয় (Photo diagnosis) — diagnose_photo() + agentic
     voice follow-up when ambiguous (followup_engine.py).
  2. কথা বলে প্রশ্ন করুন (Voice question)   — listen() -> answer_question()
     -> speak(). Chat-style: farmer can keep asking follow-ups as new
     spoken turns, since answer_question() itself may respond with a
     clarifying question (e.g. "which crop?") rather than a diagnosis.
  3. লিখে প্রশ্ন করুন (Text question)       — same answer_question() pipeline,
     typed input instead of spoken.

REQUIRED ONE-TIME FIX before running (see chat for why):
  In Text/qa_pipeline_restructured.py, change load_doc() to resolve paths
  relative to that file's own folder:

      from pathlib import Path
      TEXT_DIR = Path(__file__).parent

      def load_doc(filepath):
          full_path = TEXT_DIR / filepath
          try:
              with open(full_path, "r", encoding="utf-8") as f:
                  return f.read()
          except FileNotFoundError:
              print(f"WARNING: File not found — {full_path}")
              return ""

Also confirm Image/crop_documents.py has the equivalent fix:
      DOCUMENTS_DIR = Path(__file__).parent / "documents"
"""

import subprocess
import sys
from pathlib import Path

import streamlit as st

sys.path.append(str(Path(__file__).parent / "Image"))
sys.path.append(str(Path(__file__).parent / "Voice"))
sys.path.append(str(Path(__file__).parent / "Text"))

from followup_engine import (
    needs_followup,
    generate_followup_question,
    rediagnose_with_answer,
)
from diagnose import diagnose_photo, get_available_crops
from voice_functions import listen, speak
from qa_pipeline_restructured import (
    answer_question,
    load_crop_docs as load_text_crop_docs,
    load_all_docs,
)

st.set_page_config(page_title="KrishiKotha", page_icon="🌾")

# ---------------------------------------------------------------------
# Cache the Text pipeline's document loading (loaded once per session)
# ---------------------------------------------------------------------
if "text_crop_docs" not in st.session_state:
    st.session_state.text_crop_docs = load_text_crop_docs()
if "text_combined_docs" not in st.session_state:
    st.session_state.text_combined_docs = load_all_docs()


def convert_to_wav(raw_bytes: bytes, out_path: str = "temp_fixed.wav") -> str:
    with open("temp_input_raw", "wb") as f:
        f.write(raw_bytes)
    subprocess.run(
        ["ffmpeg", "-y", "-i", "temp_input_raw", "-ar", "16000", "-ac", "1", out_path],
        check=True,
        capture_output=True,
    )
    return out_path


st.title("KrishiKotha - কৃষি সহায়ক")

mode = st.radio(
    "আপনি কীভাবে সাহায্য চান?",
    [
        "📷 ছবি দিয়ে রোগ নির্ণয় (Photo diagnosis)",
        "🎤 কথা বলে প্রশ্ন করুন (Voice question)",
        "⌨️ লিখে প্রশ্ন করুন (Text question)",
    ],
)

st.divider()

# =======================================================================
# MODE 1 — Photo diagnosis (+ agentic voice follow-up)
# =======================================================================
if mode.startswith("📷"):

    if "photo_stage" not in st.session_state:
        st.session_state.photo_stage = "idle"
    if "photo_first_pass" not in st.session_state:
        st.session_state.photo_first_pass = None
    if "photo_followup_q" not in st.session_state:
        st.session_state.photo_followup_q = None
    if "photo_crop" not in st.session_state:
        st.session_state.photo_crop = None
    if "photo_final" not in st.session_state:
        st.session_state.photo_final = None

    def reset_photo_flow():
        st.session_state.photo_stage = "idle"
        st.session_state.photo_first_pass = None
        st.session_state.photo_followup_q = None
        st.session_state.photo_crop = None
        st.session_state.photo_final = None

    def show_photo_result(result: dict, heading: str):
        st.subheader(heading)
        st.write(f"**রোগ:** {', '.join(result.get('matched_diseases', []))}")
        st.write(f"**আত্মবিশ্বাস:** {result.get('confidence', 'n/a')}")
        st.write(f"**নির্ণয়:** {result.get('diagnosis_bangla', '')}")
        st.write(f"**পরামর্শ:** {result.get('advice_bangla', '')}")
        with st.expander("Dev info (English)"):
            st.json(result)

    if st.session_state.photo_stage == "idle":
        crop = st.selectbox("ফসল বেছে নিন (select crop)", get_available_crops())
        photo = st.file_uploader("ফসলের ছবি আপলোড করুন", type=["jpg", "jpeg", "png", "webp"])

        if photo is not None and st.button("রোগ নির্ণয় করুন (Diagnose)"):
            image_path = f"temp_upload_{photo.name}"
            with open(image_path, "wb") as f:
                f.write(photo.getbuffer())

            with st.spinner("ছবি বিশ্লেষণ হচ্ছে..."):
                first_pass = diagnose_photo(image_path, crop)

            st.session_state.photo_crop = crop
            st.session_state.photo_first_pass = first_pass

            if needs_followup(first_pass):
                with st.spinner("একটি স্পষ্টীকরণ প্রশ্ন তৈরি হচ্ছে..."):
                    question = generate_followup_question(first_pass)
                speak(question, "followup_question.mp3")
                st.session_state.photo_followup_q = question
                st.session_state.photo_stage = "awaiting_followup"
            else:
                first_pass["followup_asked"] = False
                st.session_state.photo_final = first_pass
                speak(first_pass.get("advice_bangla", ""), "final_advice.mp3")
                st.session_state.photo_stage = "done"

            st.rerun()

    elif st.session_state.photo_stage == "awaiting_followup":
        st.info("প্রথম বিশ্লেষণ অস্পষ্ট — একটি স্পষ্টীকরণ প্রশ্ন আছে।")
        st.write(f"**প্রশ্ন:** {st.session_state.photo_followup_q}")
        st.audio("followup_question.mp3")

        answer_audio = st.audio_input("আপনার উত্তর রেকর্ড করুন")

        if answer_audio is not None:
            try:
                with st.spinner("শুনছি..."):
                    wav_path = convert_to_wav(answer_audio.getbuffer().tobytes())
                    farmer_answer = listen(wav_path)

                st.write(f"**আপনি বলেছেন:** {farmer_answer}")

                with st.spinner("চূড়ান্ত নির্ণয় হচ্ছে..."):
                    final = rediagnose_with_answer(
                        st.session_state.photo_first_pass,
                        st.session_state.photo_crop,
                        st.session_state.photo_followup_q,
                        farmer_answer,
                    )
                    final["followup_asked"] = True

                speak(final.get("advice_bangla", ""), "final_advice.mp3")
                st.session_state.photo_final = final
                st.session_state.photo_stage = "done"
                st.rerun()

            except Exception as e:
                st.error("দুঃখিত, আবার চেষ্টা করুন। (Sorry, please try again.)")
                st.caption(f"Debug info: {e}")

        if st.button("বাদ দিন, প্রথম নির্ণয়ই দেখান (Skip, show first-pass result)"):
            fp = st.session_state.photo_first_pass
            fp["followup_asked"] = True
            fp["farmer_answer"] = None
            st.session_state.photo_final = fp
            st.session_state.photo_stage = "done"
            st.rerun()

    elif st.session_state.photo_stage == "done":
        result = st.session_state.photo_final
        heading = (
            "চূড়ান্ত নির্ণয় (with follow-up)"
            if result.get("followup_asked")
            else "নির্ণয় (first-pass, high confidence)"
        )
        show_photo_result(result, heading)

        if Path("final_advice.mp3").exists():
            st.audio("final_advice.mp3")

        if st.button("নতুন করে শুরু করুন (Start over)"):
            reset_photo_flow()
            st.rerun()

# =======================================================================
# MODE 2 — Voice question (chat-style, since answer_question() may itself
# respond with a clarifying question rather than a final answer)
# =======================================================================
elif mode.startswith("🎤"):

    if "voice_chat" not in st.session_state:
        st.session_state.voice_chat = []  # list of {"question": ..., "answer": ..., "triage": ...}
    if "voice_raw_turns" not in st.session_state:
        st.session_state.voice_raw_turns = []

    for turn in st.session_state.voice_chat:
        st.write(f"**আপনি জিজ্ঞাসা করেছেন:** {turn['question']}")
        st.write(f"**উত্তর:** {turn['answer']}")
        with st.expander("Dev info (triage)"):
            st.json(turn["triage"])
        st.divider()

    audio_value = st.audio_input("আপনার প্রশ্ন রেকর্ড করুন")

    if audio_value is not None:
        try:
            with st.spinner("শুনছি..."):
                wav_path = convert_to_wav(audio_value.getbuffer().tobytes())
                question_text = listen(wav_path)

            st.write(f"**আপনি বলেছেন:** {question_text}")

            # Same statelessness issue as Text mode: resend the FULL
            # conversation so far, not just this latest spoken fragment.
            st.session_state.voice_raw_turns.append(question_text)
            combined_question = "\n".join(
                f"কৃষকের বক্তব্য {i+1}: {t}"
                for i, t in enumerate(st.session_state.voice_raw_turns)
            )

            with st.spinner("উত্তর তৈরি হচ্ছে..."):
                answer, triage = answer_question(
                    combined_question,
                    st.session_state.text_crop_docs,
                    st.session_state.text_combined_docs,
                    return_triage=True,
                )

            speak(answer, "voice_qa_response.mp3")
            st.session_state.voice_chat.append(
                {"question": question_text, "answer": answer, "triage": triage}
            )
            st.rerun()

        except Exception as e:
            st.error("দুঃখিত, আবার চেষ্টা করুন। (Sorry, please try again.)")
            st.caption(f"Debug info: {e}")

    if Path("voice_qa_response.mp3").exists() and st.session_state.voice_chat:
        st.audio("voice_qa_response.mp3")

    if st.session_state.voice_chat and st.button("নতুন করে শুরু করুন (Start over)"):
        st.session_state.voice_chat = []
        st.session_state.voice_raw_turns = []
        st.rerun()

# =======================================================================
# MODE 3 — Text question (same pipeline, typed input, chat-style)
# =======================================================================
elif mode.startswith("⌨️"):

    if "text_chat" not in st.session_state:
        st.session_state.text_chat = []
    if "text_raw_turns" not in st.session_state:
        st.session_state.text_raw_turns = []  # accumulated for context

    for turn in st.session_state.text_chat:
        st.write(f"**আপনি জিজ্ঞাসা করেছেন:** {turn['question']}")
        st.write(f"**উত্তর:** {turn['answer']}")
        with st.expander("Dev info (triage)"):
            st.json(turn["triage"])
        st.divider()

    last_situation = (
        st.session_state.text_chat[-1]["triage"].get("situation")
        if st.session_state.text_chat
        else None
    )
    if last_situation in ("no_crop_named", "multiple_match"):
        st.info("উপরের প্রশ্নের উত্তর নিচে লিখুন (Answer the question above below)")

    with st.form("text_question_form", clear_on_submit=True):
        question_text = st.text_input("আপনার প্রশ্ন লিখুন (বা উপরের প্রশ্নের উত্তর দিন)")
        submitted = st.form_submit_button("জিজ্ঞাসা করুন (Ask)")

    if submitted and question_text.strip():
        # IMPORTANT: answer_question() is stateless per call — it has no
        # memory of earlier turns. So each call must resend the FULL
        # conversation so far (original question + every farmer answer),
        # not just this latest fragment, or context like "which crop" and
        # "what symptom" gets lost the moment a follow-up is answered.
        st.session_state.text_raw_turns.append(question_text)
        combined_question = "\n".join(
            f"কৃষকের বক্তব্য {i+1}: {t}"
            for i, t in enumerate(st.session_state.text_raw_turns)
        )

        with st.spinner("উত্তর তৈরি হচ্ছে..."):
            answer, triage = answer_question(
                combined_question,
                st.session_state.text_crop_docs,
                st.session_state.text_combined_docs,
                return_triage=True,
            )
        st.session_state.text_chat.append(
            {"question": question_text, "answer": answer, "triage": triage}
        )
        st.rerun()

    if st.session_state.text_chat and st.button("নতুন করে শুরু করুন (Start over) "):
        st.session_state.text_chat = []
        st.session_state.text_raw_turns = []
        st.rerun()
