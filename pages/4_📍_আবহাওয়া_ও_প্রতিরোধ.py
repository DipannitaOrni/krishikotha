import streamlit as st
from datetime import datetime
from voice_functions import speak
from qa_pipeline_restructured import load_crop_docs, answer_question
from styles import inject_css

st.set_page_config(page_title="প্রতিরোধ - KrishiKotha", page_icon="📍", layout="centered")
inject_css()

st.markdown("""
<div class="kk-header">
    <h1>📍 মৌসুমি সতর্কতা ও প্রতিরোধ</h1>
    <p>আপনার এলাকার জন্য এই মাসের সাধারণ পরামর্শ</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="kk-card">
    <p style="margin:0; color: var(--text-muted);">
    এটি একটি সাধারণ মৌসুমি পরামর্শ, নির্দিষ্ট রোগ নির্ণয় নয়। সুনির্দিষ্ট সমস্যার জন্য
    "সহায়ক" পেজে ছবি বা প্রশ্ন দিয়ে জিজ্ঞাসা করুন।
    </p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# District -> common crops (stable public knowledge, hardcoded)
# ---------------------------------------------------------
DISTRICT_CROPS = {
    "ঢাকা": ["rice", "jute"],
    "ময়মনসিংহ": ["rice", "jute"],
    "রংপুর": ["rice", "maize", "tobacco"],
    "দিনাজপুর": ["rice", "wheat", "maize"],
    "রাজশাহী": ["rice", "wheat", "mustard"],
    "বগুড়া": ["rice", "potato", "maize"],
    "খুলনা": ["rice", "jute"],
    "যশোর": ["jute", "rice"],
    "মুন্সিগঞ্জ": ["potato", "rice"],
    "কুমিল্লা": ["rice", "potato"],
    "সিলেট": ["rice", "tea"],
    "চট্টগ্রাম": ["rice", "vegetables"],
    "বরিশাল": ["rice", "jute"],
}
# Some crops here (tea, vegetables) may not have documents yet — filtered below.

BANGLA_MONTHS = [
    "জানুয়ারি", "ফেব্রুয়ারি", "মার্চ", "এপ্রিল", "মে", "জুন",
    "জুলাই", "আগস্ট", "সেপ্টেম্বর", "অক্টোবর", "নভেম্বর", "ডিসেম্বর"
]

CROP_BANGLA_NAMES = {
    "rice": "ধান", "potato": "আলু", "jute": "পাট", "wheat": "গম",
    "maize": "ভুট্টা", "tomato": "টমেটো", "beans": "শিম",
    "lemon": "লেবু", "mustard": "সরিষা", "tobacco": "তামাক",
}

@st.cache_resource
def get_docs():
    crop_docs = load_crop_docs()
    combined_docs = "\n\n".join(filter(None, crop_docs.values()))
    return crop_docs, combined_docs

crop_docs, combined_docs = get_docs()


def get_seasonal_advice(district, crops_for_district):
    month_name = BANGLA_MONTHS[datetime.now().month - 1]
    responses = []
    for crop in crops_for_district:
        if crop not in crop_docs or not crop_docs[crop]:
            continue  # skip crops we don't have documents for
        crop_bn = CROP_BANGLA_NAMES.get(crop, crop)
        query = (
            f"এখন {month_name} মাস। {crop_bn} ফসলে এই সময়ে সাধারণত কোন রোগ বা "
            f"পোকার প্রাদুর্ভাব বেশি দেখা যায় এবং কী প্রতিরোধমূলক ব্যবস্থা নেওয়া উচিত? "
            f"সংক্ষেপে বলুন।"
        )
        answer = answer_question(query, crop_docs, combined_docs)
        responses.append(f"🌾 {crop_bn}:\n{answer}")
    return "\n\n".join(responses) if responses else None


st.markdown('<div class="kk-divider">📍 আপনার অবস্থান</div>', unsafe_allow_html=True)

selected_district = st.selectbox(
    "আপনার জেলা বেছে নিন",
    list(DISTRICT_CROPS.keys())
)

st.markdown(f"""
<div class="kk-answer-box">
    <div class="kk-answer-label">নির্বাচিত এলাকা</div>
    <div style="font-size: 1.1rem;">{selected_district}</div>
</div>
""", unsafe_allow_html=True)

if st.button("🌱 এই মাসের পরামর্শ দেখুন"):
    crops_for_district = DISTRICT_CROPS.get(selected_district, [])
    with st.spinner("পরামর্শ তৈরি হচ্ছে..."):
        advice = get_seasonal_advice(selected_district, crops_for_district)

    if advice:
        st.markdown(f"""
        <div class="kk-answer-box">
            <div class="kk-answer-label">এই মাসের পরামর্শ</div>
            <div style="font-size: 1.05rem; white-space: pre-line;">{advice}</div>
        </div>
        """, unsafe_allow_html=True)

        with st.spinner("অডিও তৈরি হচ্ছে..."):
            speak(advice, "response_seasonal.mp3")
        st.markdown('<div class="kk-divider">🔊 শুনুন</div>', unsafe_allow_html=True)
        st.audio("response_seasonal.mp3")
    else:
        st.warning("এই এলাকার ফসলের জন্য এখনো তথ্য প্রস্তুত নেই।")

st.markdown("""
<div class="kk-footer-note">
    KrishiKotha — SciBlitz AI Challenge 2026 · IEEE Student Branch, CUET
</div>
""", unsafe_allow_html=True)