import streamlit as st
from styles import inject_css

st.set_page_config(page_title="ব্যবহার নির্দেশিকা - KrishiKotha", page_icon="📖", layout="centered")
inject_css()

st.markdown("""
<div class="kk-header">
    <h1>📖 ব্যবহার নির্দেশিকা</h1>
    <p>মাত্র তিনটি সহজ ধাপে KrishiKotha ব্যবহার করুন</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="kk-step">
    <div class="kk-step-number">১</div>
    <div class="kk-step-content">
        <strong>মাইক বাটনে চাপ দিন</strong>
        হোম পেজে গিয়ে মাইক আইকনে ক্লিক করুন। আপনার ব্রাউজার মাইক্রোফোন অনুমতি চাইতে পারে — অনুমতি দিন।
    </div>
</div>

<div class="kk-step">
    <div class="kk-step-number">২</div>
    <div class="kk-step-content">
        <strong>আপনার প্রশ্ন বলুন</strong>
        স্পষ্টভাবে এবং শান্ত পরিবেশে আপনার ফসল, রোগ, বা কৃষি সংক্রান্ত প্রশ্ন বাংলায় বলুন। যেমন: "আমার ধান গাছের পাতা হলুদ হয়ে যাচ্ছে, কেন?"
    </div>
</div>

<div class="kk-step">
    <div class="kk-step-number">৩</div>
    <div class="kk-step-content">
        <strong>উত্তর শুনুন</strong>
        কয়েক সেকেন্ডের মধ্যে আপনি লিখিত ও কথ্য উভয় আকারে উত্তর পাবেন। উত্তর আবার শুনতে অডিও প্লেয়ারে ক্লিক করুন।
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="kk-divider">💡 ভালো ফলাফলের জন্য পরামর্শ</div>', unsafe_allow_html=True)

st.markdown("""
<div class="kk-card">
    <ul style="margin:0; padding-left: 1.2rem; line-height: 1.9;">
        <li>শান্ত পরিবেশে প্রশ্ন করুন যাতে ব্যাকগ্রাউন্ড শব্দ না থাকে</li>
        <li>স্পষ্ট ও সহজ বাক্যে প্রশ্ন করুন</li>
        <li>একটি প্রশ্নে একটি বিষয় নিয়ে জিজ্ঞাসা করুন</li>
        <li>উত্তর সঠিক মনে না হলে প্রশ্নটি আবার ভিন্নভাবে বলে দেখুন</li>
    </ul>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="kk-divider">⚠️ সীমাবদ্ধতা</div>', unsafe_allow_html=True)

st.markdown("""
<div class="kk-card">
    <p style="margin:0; color: var(--text-muted); line-height: 1.8;">
    KrishiKotha একটি সহায়ক টুল, এটি সরাসরি কৃষি বিশেষজ্ঞের বিকল্প নয়। জটিল বা গুরুতর সমস্যার
    ক্ষেত্রে স্থানীয় কৃষি সম্প্রসারণ অফিসারের সাথে যোগাযোগ করার পরামর্শ দেওয়া হচ্ছে।
    </p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="kk-footer-note">
    KrishiKotha — SciBlitz AI Challenge 2026 · IEEE Student Branch, CUET
</div>
""", unsafe_allow_html=True)