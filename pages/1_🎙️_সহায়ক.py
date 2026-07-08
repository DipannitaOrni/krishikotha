import streamlit as st
from voice_functions import listen, speak
from qa_pipeline_restructured import load_crop_docs, answer_question
from diagnose import diagnose_photo, get_available_crops
import subprocess
from styles import inject_css

st.set_page_config(
    page_title="সহায়ক - KrishiKotha",
    page_icon="🎙️",
    layout="centered"
)

inject_css()

# Load reference documents once and cache across reruns (avoids re-reading
# files from disk on every single interaction)
@st.cache_resource
def get_docs():
    crop_docs = load_crop_docs()
    combined_docs = "\n\n".join(filter(None, crop_docs.values()))
    return crop_docs, combined_docs

crop_docs, combined_docs = get_docs()

# Session-only chat history (resets when the browser tab closes/refreshes —
# no login, no database, just in-memory for this session)
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []  # list of {"question", "answer", "mode"}


def build_context_aware_question(new_question):
    """Prepend the last couple of exchanges as context, so follow-up
    questions like 'same problem but on the stem too' make sense to the
    model. Keeps only the last 2 exchanges to limit added cost."""
    if not st.session_state.chat_history:
        return new_question
    recent = st.session_state.chat_history[-2:]
    context = "\n".join(
        f"পূর্ববর্তী প্রশ্ন: {h['question']}\nউত্তর: {h['answer']}" for h in recent
    )
    return f"{context}\n\nবর্তমান প্রশ্ন: {new_question}"

# Header banner
st.markdown("""
<div class="kk-header">
    <h1>🌾 KrishiKotha সহায়ক</h1>
    <p>কথা বলে, লিখে, অথবা ছবি দিয়ে প্রশ্ন করুন</p>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="kk-divider">🌱 প্রশ্ন করার মাধ্যম বেছে নিন</div>', unsafe_allow_html=True)

# Show past Q&A for this session, if any
if st.session_state.chat_history:
    with st.expander(f"📜 আপনার পূর্ববর্তী প্রশ্ন ও উত্তর ({len(st.session_state.chat_history)})"):
        for h in reversed(st.session_state.chat_history):
            st.markdown(f"**প্রশ্ন:** {h['question']}")
            st.markdown(f"**উত্তর:** {h['answer']}")
            st.markdown("---")
        if st.button("🗑️ ইতিহাস মুছুন"):
            st.session_state.chat_history = []
            st.rerun()

tab_voice, tab_text, tab_photo = st.tabs(["🎙️  কথা বলে", "⌨️  লিখে", "📷  ছবি দিয়ে"])

# ---------------------------------------------------------
# TAB 1: Voice input
# ---------------------------------------------------------
with tab_voice:
    st.markdown("""
    <div class="kk-card">
        <p style="margin:0; color: var(--text-muted);">
        মাইক বাটনে চাপ দিন এবং আপনার ফসল সম্পর্কিত প্রশ্ন বাংলায় বলুন।
        </p>
    </div>
    """, unsafe_allow_html=True)

    audio_value = st.audio_input("আপনার প্রশ্ন রেকর্ড করুন")

    if audio_value is not None:
        try:
            with st.spinner("শুনছি..."):
                with open("temp_input.wav", "wb") as f:
                    f.write(audio_value.getbuffer())

                subprocess.run(
                    ["ffmpeg", "-y", "-i", "temp_input.wav", "-ar", "16000", "-ac", "1", "temp_fixed.wav"],
                    check=True,
                    capture_output=True
                )

                question_text = listen("temp_fixed.wav")

            st.markdown(f"""
            <div class="kk-answer-box">
                <div class="kk-answer-label">আপনি বলেছেন</div>
                <div style="font-size: 1.1rem;">{question_text}</div>
            </div>
            """, unsafe_allow_html=True)

            with st.spinner("উত্তর তৈরি হচ্ছে..."):
                context_aware_question = build_context_aware_question(question_text)
                answer_text = answer_question(context_aware_question, crop_docs, combined_docs)
                speak(answer_text, "response_voice.mp3")

            st.session_state.chat_history.append({
                "question": question_text,
                "answer": answer_text,
                "mode": "voice"
            })

            st.markdown(f"""
            <div class="kk-answer-box">
                <div class="kk-answer-label">উত্তর</div>
                <div style="font-size: 1.1rem;">{answer_text}</div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown('<div class="kk-divider">🔊 শুনুন</div>', unsafe_allow_html=True)
            st.audio("response_voice.mp3")

        except Exception as e:
            st.error("দুঃখিত, আবার চেষ্টা করুন। (Sorry, please try again.)")
            st.caption(f"Debug info: {e}")

# ---------------------------------------------------------
# TAB 2: Text input
# ---------------------------------------------------------
with tab_text:
    st.markdown("""
    <div class="kk-card">
        <p style="margin:0; color: var(--text-muted);">
        আপনার প্রশ্ন নিচে বাংলায় টাইপ করুন।
        </p>
    </div>
    """, unsafe_allow_html=True)

    typed_question = st.text_area(
        "আপনার প্রশ্ন লিখুন",
        placeholder="যেমন: আমার ধান গাছের পাতা হলুদ হয়ে যাচ্ছে, কেন?",
        height=100
    )

    if st.button("উত্তর জানতে চাই", key="text_submit"):
        if typed_question.strip() == "":
            st.warning("দয়া করে একটি প্রশ্ন লিখুন।")
        else:
            try:
                with st.spinner("উত্তর তৈরি হচ্ছে..."):
                    context_aware_question = build_context_aware_question(typed_question)
                    answer_text = answer_question(context_aware_question, crop_docs, combined_docs)
                    speak(answer_text, "response_text.mp3")

                st.session_state.chat_history.append({
                    "question": typed_question,
                    "answer": answer_text,
                    "mode": "text"
                })

                st.markdown(f"""
                <div class="kk-answer-box">
                    <div class="kk-answer-label">উত্তর</div>
                    <div style="font-size: 1.1rem;">{answer_text}</div>
                </div>
                """, unsafe_allow_html=True)

                st.audio("response_text.mp3")

            except Exception as e:
                st.error("দুঃখিত, আবার চেষ্টা করুন। (Sorry, please try again.)")
                st.caption(f"Debug info: {e}")

# ---------------------------------------------------------
# TAB 3: Photo upload
# ---------------------------------------------------------
with tab_photo:
    st.markdown("""
    <div class="kk-card">
        <p style="margin:0; color: var(--text-muted);">
        প্রথমে আপনার ফসল বেছে নিন, তারপর একটি ছবি তুলুন বা আপলোড করুন।
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Bangla labels shown to the user, mapped to the crop keys diagnose_photo() expects
    CROP_LABELS = {
        "ধান (Rice)": "rice",
        "আলু (Potato)": "potato",
        "পাট (Jute)": "jute",
        "গম (Wheat)": "wheat",
        "ভুট্টা (Maize)": "maize",
        "টমেটো (Tomato)": "tomato",
        "শিম (Beans)": "beans",
        "লেবু (Lemon)": "lemon",
        "সরিষা (Mustard)": "mustard",
        "তামাক (Tobacco)": "tobacco",
    }

    selected_label = st.selectbox("আপনার ফসল বেছে নিন", list(CROP_LABELS.keys()))
    selected_crop = CROP_LABELS[selected_label]

    uploaded_image = st.file_uploader(
        "ফসলের ছবি আপলোড করুন",
        type=["jpg", "jpeg", "png"],
        key="photo_upload"
    )

    camera_image = st.camera_input("অথবা সরাসরি ছবি তুলুন")

    final_image = uploaded_image if uploaded_image is not None else camera_image

    if final_image is not None:
        st.image(final_image, caption="আপনার আপলোড করা ছবি", use_container_width=True)

        if st.button("ছবি পরীক্ষা করুন", key="photo_submit"):
            try:
                with st.spinner("ছবি বিশ্লেষণ করা হচ্ছে..."):
                    # Save uploaded image to disk since diagnose_photo() needs a file path
                    image_ext = "png" if final_image.type == "image/png" else "jpg"
                    image_path = f"temp_photo.{image_ext}"
                    with open(image_path, "wb") as f:
                        f.write(final_image.getbuffer())

                    result = diagnose_photo(image_path, crop=selected_crop)
                    advice = result.get("advice_bangla", "দুঃখিত, উত্তর তৈরি করা যায়নি।")
                    diagnosis = result.get("diagnosis_bangla", "")
                    mismatch_suspected = result.get("crop_mismatch_suspected", False)

                    if not mismatch_suspected:
                        speak(advice, "response_photo.mp3")

                if mismatch_suspected:
                    st.warning(
                        f"⚠️ ছবিটি নির্বাচিত ফসল ({selected_label}) এর সাথে মিলছে না বলে মনে হচ্ছে। "
                        f"দয়া করে সঠিক ফসল বেছে আবার চেষ্টা করুন।"
                    )
                    st.caption(diagnosis)
                    st.stop()

                st.markdown(f"""
                <div class="kk-answer-box">
                    <div class="kk-answer-label">নির্ণয়</div>
                    <div style="font-size: 1.1rem;">{diagnosis}</div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown(f"""
                <div class="kk-answer-box">
                    <div class="kk-answer-label">পরামর্শ</div>
                    <div style="font-size: 1.1rem;">{advice}</div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown('<div class="kk-divider">🔊 শুনুন</div>', unsafe_allow_html=True)
                st.audio("response_photo.mp3")

            except Exception as e:
                st.error("দুঃখিত, আবার চেষ্টা করুন। (Sorry, please try again.)")
                st.caption(f"Debug info: {e}")

st.markdown("""
<div class="kk-footer-note">
    KrishiKotha — SciBlitz AI Challenge 2026 · IEEE Student Branch, CUET
</div>
""", unsafe_allow_html=True)