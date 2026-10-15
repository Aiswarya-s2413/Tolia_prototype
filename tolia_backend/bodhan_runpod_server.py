"""
Bodhan AI Indic-Speak Standalone Server for RunPod / NVIDIA GPU
Runs on port 8000 to deliver real-time (<1.5s) Hindi, Marathi, and English voice synthesis.
"""

import os
import io
import sys
import threading
import torch
import soundfile as sf
from fastapi import FastAPI, Query, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Thread-safe GPU inference lock to prevent KV-cache corruption from concurrent requests
_gpu_lock = threading.Lock()

# Ensure CUDA GPU is available
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"[Bodhan Server] Starting on hardware: {DEVICE}")
if DEVICE == "cuda":
    print(f"[Bodhan Server] GPU: {torch.cuda.get_device_name(0)}")

# Global model holder
_tts_engine = None

def get_tts():
    global _tts_engine
    if _tts_engine is None:
        model_dir = os.getenv("MODEL_DIR", "indic_speak_models")
        if not os.path.exists(os.path.join(model_dir, "model.safetensors")):
            print(f"[Bodhan Server] Model not found in {model_dir}, downloading from Hugging Face...")
            from huggingface_hub import snapshot_download
            token = os.getenv("HF_TOKEN", None)
            snapshot_download(
                repo_id=os.getenv("INDIC_SPEAK_MODEL_ID", "bodhan-ai/indic-speak"),
                local_dir=model_dir,
                token=token
            )
        
        if model_dir not in sys.path:
            sys.path.insert(0, model_dir)
            
        from inference import TTS
        print(f"[Bodhan Server] Loading Bodhan 3.8B weights onto {DEVICE}...")
        _tts_engine = TTS(model_dir, device=DEVICE)
        print("[Bodhan Server] Model loaded and ready!")
    return _tts_engine

app = FastAPI(title="Bodhan AI Indic-Speak GPU Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "engine": "Bodhan AI Indic-Speak 3.8B",
        "device": DEVICE,
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "none"
    }

@app.get("/synthesize")
def synthesize_get(
    text: str = Query(..., description="Text to synthesize"),
    lang: str = Query("en", description="Language code: en, hi, mr, or mixed")
):
    return generate_speech(text, lang)

@app.post("/synthesize")
def synthesize_post(payload: dict):
    text = payload.get("text", "").strip()
    lang = payload.get("lang", "en")
    if not text:
        raise HTTPException(status_code=400, detail="Text parameter is required")
    return generate_speech(text, lang)

def generate_speech(text: str, lang: str = "en"):
    tts = get_tts()
    speaker = "Anagha" if lang == "mr" else "Amit"
    
    # Scale tokens to accommodate complete continuous speech without cutting off
    words = len(text.split())
    scaled = max(140, min(words * 32 + 140, 1820))
    max_new_tokens = (scaled // 7) * 7
    
    with _gpu_lock:
        try:
            # Run inference on NVIDIA GPU safely serialized to 1 request at a time
            wav = tts(text, speaker=speaker, max_new_tokens=max_new_tokens, temperature=0.6)
            if wav is None:
                raise HTTPException(status_code=500, detail="Synthesis failed")

            buf = io.BytesIO()
            sf.write(buf, wav, 24000, format="WAV", subtype="PCM_16")
            audio_bytes = buf.getvalue()

            return Response(
                content=audio_bytes,
                media_type="audio/wav",
                headers={
                    "Content-Length": str(len(audio_bytes)),
                    "X-TTS-Engine": "bodhan-indic-speak-gpu",
                    "X-Speaker": speaker
                }
            )
        except Exception as e:
            print(f"[Synthesis Error]: {e}")
            raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    # Pre-load model on startup so first request has 0 warmup delay
    get_tts()
    uvicorn.run(app, host="0.0.0.0", port=port)
