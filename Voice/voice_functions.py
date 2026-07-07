from transformers import pipeline
from gtts import gTTS

# Speech-to-text (Bangla-specific model)
asr = pipeline(
    "automatic-speech-recognition",
    model="bangla-speech-processing/BanglaASR"
)

def listen(audio_file_path: str) -> str:
    result = asr(audio_file_path)
    return result["text"]

# Text-to-speech
def speak(text: str, output_path: str = "output.mp3") -> str:
    tts = gTTS(text=text, lang="bn")
    tts.save(output_path)
    return output_path
