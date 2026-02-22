# tts.py
import wave
from piper import PiperVoice

VOICE = PiperVoice.load("voice/en_US-arctic-medium.onnx")

def synthesize_to_file(text: str, output_path: str):
    with wave.open(output_path, "wb") as wav_file:
        VOICE.synthesize_wav(text, wav_file)

    return output_path