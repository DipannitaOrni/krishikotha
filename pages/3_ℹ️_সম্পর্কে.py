import streamlit as st
from styles import inject_css

st.set_page_config(page_title="সম্পর্কে - KrishiKotha", page_icon="ℹ️", layout="centered")
inject_css()

st.markdown("""
<div class="kk-header">
    <h1>🌾 KrishiKotha সম্পর্কে</h1>
    <p>বাংলাদেশের কৃষকদের জন্য একটি কণ্ঠ-ভিত্তিক এআই সহায়ক</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="kk-card">
    <h3>🎯 আমাদের লক্ষ্য</h3>
    <p style="margin:0; line-height: 1.8; color: var(--text-muted);">
    বাংলাদেশের অনেক কৃষকের কাছে সহজে কৃষি বিশেষজ্ঞের পরামর্শ পাওয়া কঠিন। লেখাপড়া বা প্রযুক্তিগত
    জ্ঞান না থাকলেও, KrishiKotha ব্যবহার করে যে কেউ শুধু কথা বলে ফসল সংক্রান্ত পরামর্শ পেতে পারেন —
    টাইপ করার বা পড়ার প্রয়োজন নেই।
    </p>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="kk-divider">⚙️ কীভাবে কাজ করে</div>', unsafe_allow_html=True)

st.markdown("""
<div class="kk-card">
    <p style="margin:0 0 0.8rem 0; line-height: 1.8; color: var(--text-muted);">
    আপনার কণ্ঠস্বর প্রথমে টেক্সটে রূপান্তরিত হয়, তারপর বিশ্বস্ত কৃষি নির্দেশিকা (DAE, BARI, BRRI)
    থেকে প্রাসঙ্গিক তথ্য খুঁজে বের করে একটি সহজবোধ্য উত্তর তৈরি করা হয়, এবং সবশেষে তা আবার
    কথ্য বাংলায় শোনানো হয়।
    </p>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="kk-divider">🛠️ প্রযুক্তি</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    st.markdown("""
    <div class="kk-card">
        <strong style="color: var(--paddy-green);">স্পিচ-টু-টেক্সট</strong><br>
        <span style="color: var(--text-muted);">Whisper (বাংলা ফাইন-টিউনড মডেল)</span>
    </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown("""
    <div class="kk-card">
        <strong style="color: var(--paddy-green);">টেক্সট-টু-স্পিচ</strong><br>
        <span style="color: var(--text-muted);">Google TTS</span>
    </div>
    """, unsafe_allow_html=True)

st.markdown("""
<div class="kk-card" style="margin-top: -0.5rem;">
    <strong style="color: var(--paddy-green);">তৈরি করেছে</strong><br>
    <span style="color: var(--text-muted);">Team KrishiKotha — SciBlitz AI Challenge 2026, IEEE Student Branch, CUET</span>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="kk-footer-note">
    KrishiKotha — SciBlitz AI Challenge 2026 · IEEE Student Branch, CUET
</div>
""", unsafe_allow_html=True)