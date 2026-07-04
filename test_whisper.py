from transformers import pipeline

# Bangla fine-tuned Whisper model
asr = pipeline(
    "automatic-speech-recognition",
    model="bangla-speech-processing/BanglaASR"
)

def listen(audio_file_path: str) -> str:
    result = asr(audio_file_path)
    return result["text"]

if __name__ == "__main__":
    result = listen("test_audio_fixed.wav")
    print("Transcribed text:", result)