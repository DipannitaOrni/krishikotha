from gtts import gTTS

def speak(text: str, output_path: str = "output.mp3") -> str:
    tts = gTTS(text=text, lang="bn")
    tts.save(output_path)
    return output_path

if __name__ == "__main__":
    speak("আপনার ধান গাছের পাতা হলুদ হয়ে যাচ্ছে, একজন কৃষি বিশেষজ্ঞের পরামর্শ নিন।")
    print("Saved to output.mp3")