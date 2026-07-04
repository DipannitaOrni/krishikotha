from voice_functions import listen, speak

text = listen("test_audio_fixed.wav")
print("Heard:", text)

speak(text, "roundtrip_output.mp3")
print("Spoken back — check roundtrip_output.mp3")