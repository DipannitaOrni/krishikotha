import streamlit as st
from voice_functions import listen, speak
import subprocess

st.title("KrishiKotha - কৃষি সহায়ক")

st.write("আপনার প্রশ্ন বলুন এবং উত্তর শুনুন")

# Live mic recording instead of file upload
audio_value = st.audio_input("আপনার প্রশ্ন রেকর্ড করুন")

if audio_value is not None:
    try:
        with st.spinner("শুনছি..."):
            # Save the recorded audio
            with open("temp_input.wav", "wb") as f:
                f.write(audio_value.getbuffer())

            # Convert to proper format using ffmpeg
            subprocess.run(
                ["ffmpeg", "-y", "-i", "temp_input.wav", "-ar", "16000", "-ac", "1", "temp_fixed.wav"],
                check=True,
                capture_output=True
            )

            # Transcribe
            text = listen("temp_fixed.wav")

        st.write("**আপনি বলেছেন:**", text)

        with st.spinner("উত্তর তৈরি হচ্ছে..."):
            # For now, just echo back — later this becomes Pair 2's grounded answer
            speak(text, "response.mp3")

        st.audio("response.mp3")

    except Exception as e:
        st.error("দুঃখিত, আবার চেষ্টা করুন। (Sorry, please try again.)")
        st.caption(f"Debug info: {e}")