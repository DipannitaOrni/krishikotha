import streamlit as st
from styles import inject_css

st.set_page_config(
    page_title="KrishiKotha - কৃষি সহায়ক",
    page_icon="🌾",
    layout="centered"
)

inject_css()

# Hero section
st.markdown("""
<div class="kk-hero">
    <div class="kk-hero-icon">🌾</div>
    <h1 class="kk-hero-title">KrishiKotha</h1>
    <p class="kk-hero-subtitle">কৃষি সহায়ক</p>
    <p class="kk-hero-tagline">কথা বলুন, পরামর্শ পান — কোনো টাইপ করার প্রয়োজন নেই</p>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="kk-divider">✨ কেন KrishiKotha</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("""
    <div class="kk-feature-card">
        <div class="kk-feature-icon">🎙️</div>
        <strong>শুধু কথা বলুন</strong>
        <p>টাইপ বা পড়ার প্রয়োজন নেই, বাংলায় প্রশ্ন বলুন</p>
    </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown("""
    <div class="kk-feature-card">
        <div class="kk-feature-icon">📚</div>
        <strong>বিশ্বস্ত তথ্য</strong>
        <p>DAE, BARI, BRRI-এর প্রকৃত কৃষি নির্দেশিকা থেকে উত্তর</p>
    </div>
    """, unsafe_allow_html=True)
with col3:
    st.markdown("""
    <div class="kk-feature-card">
        <div class="kk-feature-icon">🔊</div>
        <strong>কথ্য উত্তর</strong>
        <p>লিখিত ও শোনার মতো উভয় আকারে সহজ উত্তর</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<div class="kk-divider"></div>', unsafe_allow_html=True)

# Call to action
st.markdown('<div class="kk-cta-wrap">', unsafe_allow_html=True)
_, center_col, _ = st.columns([1, 2, 1])
with center_col:
    if st.button("🎙️  প্রশ্ন জিজ্ঞাসা করুন শুরু করি", use_container_width=True, type="primary"):
        st.switch_page("pages/1_🎙️_সহায়ক.py")
st.markdown('</div>', unsafe_allow_html=True)

st.markdown("""
<div class="kk-footer-note">
    KrishiKotha — SciBlitz AI Challenge 2026 · IEEE Student Branch, CUET
</div>
""", unsafe_allow_html=True)