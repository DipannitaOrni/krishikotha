import streamlit as st
from voice_functions import listen, speak
import subprocess

st.title("KrishiKotha - কৃষি সহায়ক")

audio_file = st.file_uploader("আপনার প্রশ্ন রেকর্ড করে আপলোড করুন", type=["wav", "mp3", "m4a"])

if audio_file is not None:
    with open("temp_input.wav", "wb") as f:
        f.write(audio_file.getbuffer())

    # Convert to proper format using ffmpeg
    subprocess.run(["ffmpeg", "-y", "-i", "temp_input.wav", "-ar", "16000", "-ac", "1", "temp_fixed.wav"])

    text = listen("temp_fixed.wav")
    st.write("**আপনি বলেছেন:**", text)

    # For now, just echo back — later this becomes Pair 2's grounded answer
    speak(text, "response.mp3")
    st.audio("response.mp3")