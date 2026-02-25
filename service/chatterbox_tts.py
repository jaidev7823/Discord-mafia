# service/chatterbox_tts.py
import torchaudio as ta
import torch
from chatterbox.tts_turbo import ChatterboxTurboTTS

# SINGLE GLOBAL MODEL shared by all agents
_global_model = None
_global_sr = None
_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

async def load_global_model():
    """Load the model once globally"""
    global _global_model, _global_sr
    if _global_model is None:
        print("🔄 Loading Chatterbox Turbo model (SHARED for all agents)...")
        _global_model = ChatterboxTurboTTS.from_pretrained(device=_device)
        _global_sr = _global_model.sr
        print(f"✅ Model loaded on {_device} and will be shared")
    return _global_model, _global_sr

class ChatterboxTTS:
    def __init__(self, reference_audio_path: str):
        """Each agent just stores their reference audio path"""
        self.reference_audio_path = reference_audio_path
        
    async def synthesize(self, text: str, emotion: str = None):
        """Use the global shared model"""
        # Get the shared model
        model, sr = await load_global_model()
        
        # Generate audio
        wav = model.generate(
            text=text,
            audio_prompt_path=self.reference_audio_path
        )
        return wav, sr
    
    async def save_to_file(self, wav, sr, output_path):
        """Save audio to file"""
        ta.save(output_path, wav.cpu(), sr)