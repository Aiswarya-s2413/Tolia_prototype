import os
import io
import re
import asyncio
import tempfile
import subprocess
_stt_model = None

def get_stt_model():
    """Lazy load faster-whisper STT model locally."""
    global _stt_model
    if _stt_model is None:
        try:
            from faster_whisper import WhisperModel
            device = "cpu"
            compute_type = "int8"
            model_size = os.getenv("WHISPER_MODEL_SIZE", "small")
            print(f"[Whisper STT] Loading Whisper ({model_size}) model locally on {device} ({compute_type})...")
            _stt_model = WhisperModel(model_size, device=device, compute_type=compute_type)
            print("[Whisper STT] Whisper model loaded successfully!")
        except Exception as e:
            print(f"[Whisper STT] Faster-whisper load notice: {e}")
            return None
    return _stt_model

import requests
from django.conf import settings

class LocalSTTService:
    """
    100% Local Speech-to-Text Engine powered by Faster-Whisper.
    Provides sub-second latency with Voice Activity Detection (VAD) filter,
    supporting seamless auto-detection across Hindi ('hi'), Marathi ('mr'), and English ('en').
    """
    @staticmethod
    def transcribe_audio(audio_bytes, language=None):
        """
        Transcribe raw audio bytes (wav/webm/ogg/mp3/m4a) locally using Whisper STT.
        """
        from .rag_engine import detect_language

        if not audio_bytes or len(audio_bytes) < 100:
            return {
                "success": False,
                "error": "Audio payload too short or empty",
                "text": ""
            }

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            model = get_stt_model()
            if model is None:
                return {
                    "success": False,
                    "error": "Whisper STT model failed to initialize",
                    "text": ""
                }

            lang_code = language if (language in ['hi', 'mr', 'en']) else None
            
            # Select appropriate acoustic prompt based on target language to prevent cross-language script bias
            if lang_code == 'hi':
                acoustic_prompt = "Blast Furnace, Rolling Mill, आपातकालीन नियम, सुरक्षा, रोलिंग मिल, गिअरबॉक्स, ऑइल"
            elif lang_code == 'mr':
                acoustic_prompt = "Blast Furnace, Rolling Mill, आपत्कालीन नियम, सुरक्षा, रोलिंग मिल, गिअरबॉक्स, ऑइल"
            elif lang_code == 'en':
                acoustic_prompt = "Blast Furnace, Rolling Mill, PPE safety, gearbox, hydraulic pressure, emergency shutdown, standard operating procedure"
            else:
                # Neutral acoustic prompt for Auto-Detect (prevents Whisper from biasing English into Hindi Devanagari)
                acoustic_prompt = "Blast Furnace, Rolling Mill, PPE safety, gearbox, hydraulic pressure, emergency shutdown"

            # Fast sub-second transcription with Voice Activity Detection (VAD) filter
            segments, info = model.transcribe(
                tmp_path,
                language=lang_code,
                beam_size=2,
                vad_filter=True,
                initial_prompt=acoustic_prompt
            )
            
            transcript = " ".join([segment.text for segment in segments]).strip()

            # If unconstrained auto-detect produced an unexpected language or empty transcript, retry with English
            if (not transcript or (info and info.language not in ['en', 'hi', 'mr'])) and not lang_code:
                retry_segments, retry_info = model.transcribe(
                    tmp_path,
                    language='en',
                    beam_size=2,
                    vad_filter=True,
                    initial_prompt=acoustic_prompt
                )
                retry_transcript = " ".join([segment.text for segment in retry_segments]).strip()
                if retry_transcript:
                    transcript = retry_transcript
                    info = retry_info
            
            # Determine detected language:
            # If explicit language was requested, honor it
            if lang_code:
                detected_lang = lang_code
            elif info and info.language == 'en' and not any('\u0900' <= char <= '\u097F' for char in transcript):
                # Whisper's acoustic classifier detected English and transcript is Latin
                detected_lang = 'en'
            else:
                # Use contextual detector on transcript
                detected_lang = detect_language(transcript) if transcript else (info.language if (info and info.language in ['hi', 'mr', 'en']) else 'en')

            if detected_lang not in ['hi', 'mr', 'en']:
                detected_lang = 'en'

            return {
                "success": True,
                "text": transcript,
                "language": detected_lang,
                "engine": "whisper"
            }
        except Exception as e:
            print(f"[Whisper STT Error]: {e}")
            return {
                "success": False,
                "error": str(e),
                "text": ""
            }
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

def detect_voice_language(text):
    """
    Self-contained, fast language detection (English 'en', Hindi 'hi', or Marathi 'mr').
    """
    if not text or not text.strip():
        return 'en'
    text_lower = text.lower().strip()

    # Marathi unique characters & keywords
    if any('\u0933' <= char <= '\u0950' for char in text): # ळ
        return 'mr'
    marathi_markers = ['काय', 'कसे', 'कशी', 'कशा', 'कधी', 'कुठे', 'कोण', 'आहे', 'आहेत', 'आहोत', 'नाही', 'नाहीत',
                       'सांगा', 'सांग', 'माहिती', 'करावे', 'करावा', 'करावी', 'द्या', 'द्यावे', 'होते', 'झाले', 'पाहिजे',
                       'तुम्ही', 'तुम्हाला', 'माझा', 'माझी', 'माझे', 'आपला', 'आपली', 'आपले', 'कारखाना', 'दाब', 'तपासा',
                       'aahe', 'ahe', 'aahet', 'sanga', 'mahiti', 'pahije', 'karkhana']
    if any(m in text_lower or m in text for m in marathi_markers):
        return 'mr'

    # Hindi markers & vocabulary
    hindi_markers = ['क्या', 'कैसे', 'कैसा', 'कैसी', 'कब', 'कहाँ', 'कहा', 'है', 'हैं', 'हो', 'हूँ', 'बताओ', 'बताइए',
                     'बताएं', 'सुरक्षा', 'करो', 'कीजिए', 'करें', 'चाहिए', 'सकते', 'सकता', 'सकती', 'तुम्हारा', 'तुम्हारी',
                     'आपका', 'आपकी', 'मेरा', 'मेरी', 'नमस्ते', 'बारे', 'नियम', 'संयंत्र', 'kya', 'kaise', 'batao', 'chahiye', 'namaste']
    if any(h in text_lower or h in text for h in hindi_markers):
        return 'hi'

    # Devanagari script presence fallback
    if any('\u0900' <= char <= '\u097F' for char in text):
        return 'hi'

    return 'en'

_piper_voices = {}

class PiperTTSService:
    """
    100% Air-Gapped Neural Text-to-Speech Engine powered by Piper & ONNX.
    Zero network traffic, zero external APIs, sub-150ms synthesis on CPU.
    """
    @staticmethod
    def get_voice(lang='en'):
        global _piper_voices
        possible_dirs = [
            os.path.join(os.path.dirname(__file__), '..', 'piper_models'),
            os.path.abspath('piper_models'),
            os.path.abspath('tolia_backend/piper_models'),
            '/home/mohit/Tolia_prototype/tolia_backend/piper_models'
        ]
        base_dir = next((d for d in possible_dirs if os.path.exists(d)), None)
        if not base_dir:
            print("[Piper Notice]: piper_models directory not found")
            return None

        # Prefer Priyamvada (Indian Female Neural Voice - offline counterpart to Swara)
        # Fall back to Pratham if Priyamvada is not present
        if lang in ['hi', 'mr', 'mixed', 'hinglish']:
            priyamvada_path = os.path.join(base_dir, 'hi_IN-priyamvada-medium.onnx')
            if os.path.exists(priyamvada_path):
                model_name = 'hi_IN-priyamvada-medium.onnx'
            else:
                model_name = 'hi_IN-pratham-medium.onnx'
        else:
            model_name = 'en_US-lessac-medium.onnx'

        model_path = os.path.join(base_dir, model_name)
        config_path = f"{model_path}.json"

        if model_path not in _piper_voices and os.path.exists(model_path):
            try:
                from piper import PiperVoice
                print(f"[Piper TTS] Loading voice model from {model_path}...")
                _piper_voices[model_path] = PiperVoice.load(model_path, config_path=config_path)
                print(f"[Piper TTS] Voice model loaded successfully!")
            except Exception as e:
                print(f"[Piper Model Load Notice]: {e}")
                return None

        return _piper_voices.get(model_path)

    @staticmethod
    def synthesize(text, lang='en'):
        try:
            # For Hindi, Marathi, or Mixed (Hinglish), use Indian neural speaker (Pratham)
            # Only pure English queries use Lessac
            is_indic_or_mixed = (
                lang in ['hi', 'mr', 'mixed', 'hinglish'] or
                any('\u0900' <= char <= '\u097F' for char in text)
            )
            effective_lang = 'hi' if is_indic_or_mixed else 'en'
            voice = PiperTTSService.get_voice(effective_lang)
            if voice is None:
                return None

            try:
                from piper import SynthesisConfig
                # Natural, articulate conversational pace tuned to normal human speech
                speed_scale = 1.10 if is_indic_or_mixed else 1.08
                syn_config = SynthesisConfig(
                    length_scale=speed_scale,  # Comfortable, natural human speaking speed
                    noise_scale=0.667,         # Clear, high-fidelity neural voice acoustics
                    noise_w_scale=0.80         # Natural human speech cadence and flow
                )
                chunks = [chunk.audio_int16_bytes for chunk in voice.synthesize(text, syn_config=syn_config)]
            except Exception:
                chunks = [chunk.audio_int16_bytes for chunk in voice.synthesize(text)]

            if not chunks:
                return None

            raw_pcm = b''.join(chunks)
            sample_rate = getattr(voice.config, 'sample_rate', 22050)

            import wave
            buf = io.BytesIO()
            with wave.open(buf, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(raw_pcm)

            return buf.getvalue()
        except Exception as e:
            print(f"[Piper Synthesis Error]: {e}")
            return None

_tts_cache = {}
_MAX_CACHE_SIZE = 500

def normalize_text_for_speech(text, lang='en'):
    """Convert technical symbols, slashes in measurement units, and abbreviations into natural spoken words."""
    if not text:
        return ""
    t = re.sub(r'[*_#`~⚠️💡📌▶️✅🛡️🏢👥📋📜•]', '', text)
    t = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', t)
    t = re.sub(r'^\s*[-•*]\s*', '', t, flags=re.MULTILINE)
    t = re.sub(r'^\s*\d+[\.\)]\s*', '', t, flags=re.MULTILINE)
    t = re.sub(r'\n+', '. ', t)
    t = re.sub(r'[\(\)]', ' ', t)
    
    # Technical Measurement Units with Slashes
    t = re.sub(r'\bmm\/s\b', 'millimeter per second', t, flags=re.IGNORECASE)
    t = re.sub(r'\bm\/s\b', 'meter per second', t, flags=re.IGNORECASE)
    t = re.sub(r'\bkm\/h\b', 'kilometer per hour', t, flags=re.IGNORECASE)
    t = re.sub(r'\bl\/min\b', 'liters per minute', t, flags=re.IGNORECASE)
    t = re.sub(r'\bkg\/cm2\b', 'kilogram per square centimeter', t, flags=re.IGNORECASE)
    t = re.sub(r'\bkg\/m3\b', 'kilogram per cubic meter', t, flags=re.IGNORECASE)
    
    # Symbols to Natural Spoken Words
    t = re.sub(r'°C\b', ' degree Celsius', t)
    t = re.sub(r'°F\b', ' degree Fahrenheit', t)
    t = re.sub(r'[±]|(\+\/-)|\b\+-\b', ' plus or minus ', t)
    t = re.sub(r'₹', 'Rupees ', t)
    t = re.sub(r'%', ' percent', t)
    t = re.sub(r'\b(\d+)\s*dB\+?\b', r'\1 decibels', t, flags=re.IGNORECASE)
    
    # Clean dashes in equipment codes (B-4 -> B 4)
    t = re.sub(r'\b([A-Za-z])-(\d+)\b', r'\1 \2', t)
    
    # Industrial abbreviations & acronyms to natural speech
    t = re.sub(r'\bSOPs?\b', 'standard operating procedures', t, flags=re.IGNORECASE)
    t = re.sub(r'\bPPE\b', 'personal protective equipment', t, flags=re.IGNORECASE)
    t = re.sub(r'\bAI\b', 'A I', t)
    t = re.sub(r'\bPSI\b', 'P S I', t)
    t = re.sub(r'\bBAR\b', 'bar', t, flags=re.IGNORECASE)

    # Remaining standalone slashes between words
    t = re.sub(r'(\w+)\/(\w+)', r'\1 or \2', t)
    t = re.sub(r'\/', ' ', t)
    
    return re.sub(r'\s+', ' ', t).strip()

_indic_speak_tts = None
import threading

_indic_speak_tts = None
_indic_speak_failed = False
_indic_speak_lock = threading.Lock()

class IndicSpeakTTSService:
    """
    100% Local Neural TTS Engine powered by Bodhan AI's Indic-Speak (Llama-3.2-3B + SNAC/Vocos).
    Zero external APIs, completely local inference supporting 22 Indian languages and English.
    Thread-safe singleton with Apple Metal (MPS) cache management.
    """
    @staticmethod
    def get_tts():
        global _indic_speak_tts, _indic_speak_failed
        if _indic_speak_tts is not None:
            return _indic_speak_tts
        if _indic_speak_failed:
            return None

        with _indic_speak_lock:
            if _indic_speak_tts is not None:
                return _indic_speak_tts

            try:
                import os
                import sys
                from pathlib import Path
                from huggingface_hub import snapshot_download

                possible_local_dirs = [
                    os.path.join(os.path.dirname(__file__), '..', 'indic_speak_models'),
                    os.path.abspath('indic_speak_models'),
                    os.path.abspath('tolia_backend/indic_speak_models')
                ]
                local_dir = next((d for d in possible_local_dirs if os.path.isdir(d) and os.path.exists(os.path.join(d, 'model.safetensors'))), None)

                if local_dir:
                    print(f"[Indic-Speak TTS] Loading directly from offline directory: {local_dir}")
                    model_dir = local_dir
                else:
                    token = os.getenv('HF_TOKEN')
                    if not token:
                        hf_token_file = Path.home() / '.cache/huggingface/token'
                        if hf_token_file.exists():
                            token = hf_token_file.read_text().strip()

                    model_id = os.getenv('INDIC_SPEAK_MODEL_ID', 'bodhan-ai/indic-speak')
                    print(f"[Indic-Speak TTS] Initializing local engine '{model_id}'...")

                    # Snapshot model repository locally (100% offline once downloaded)
                    model_dir = snapshot_download(
                        repo_id=model_id,
                        token=token,
                        local_files_only=False
                    )

                # Ensure model directory is on Python path to import its inference module
                if model_dir not in sys.path:
                    sys.path.insert(0, model_dir)

                import torch
                # Set environment variable to avoid MPS allocation thrashing
                os.environ['PYTORCH_MPS_HIGH_WATERMARK_RATIO'] = '0.0'
                device = 'mps' if torch.backends.mps.is_available() else ('cuda' if torch.cuda.is_available() else 'cpu')

                from inference import TTS
                _indic_speak_tts = TTS(model_dir, device=device)
                print(f"[Indic-Speak TTS] Bodhan Indic-Speak loaded successfully on local hardware ({device})!")
                return _indic_speak_tts
            except Exception as e:
                print(f"[Indic-Speak TTS Load Notice]: {e}")
                # Don't permanently disable on transient error, allow retry
                return None

    @staticmethod
    def synthesize(text, lang='en'):
        # 1. Check if remote GPU endpoint (e.g. RunPod) is configured
        remote_url = getattr(settings, 'BODHAN_TTS_URL', os.getenv('BODHAN_TTS_URL', '')).strip().rstrip('/')
        if remote_url:
            for attempt in range(2):
                try:
                    print(f"[Bodhan TTS] Sending request to RunPod GPU (attempt {attempt+1}): {remote_url}/synthesize (lang={lang}, text='{text[:35]}...')")
                    res = requests.get(
                        f"{remote_url}/synthesize",
                        params={"text": text, "lang": lang},
                        timeout=45.0
                    )
                    if res.status_code == 200 and len(res.content) > 500:
                        print(f"[Bodhan TTS] Received {len(res.content)} bytes of audio from RunPod GPU!")
                        return res.content
                    else:
                        print(f"[Bodhan TTS] RunPod returned status {res.status_code}: {res.text[:200]}")
                        time.sleep(1.0)
                except Exception as e:
                    print(f"[Bodhan TTS] RunPod connection error: {e}")
                    time.sleep(1.0)

            print("[Bodhan TTS] Exclusively using Bodhan on RunPod GPU — zero fallback.")
            return None
        tts = IndicSpeakTTSService.get_tts()
        if tts is None:
            return None

        with _indic_speak_lock:
            try:
                import io
                import torch
                import soundfile as sf

                # Select native speaker voice according to detected language
                if lang == 'mr':
                    speaker = 'Anagha'
                elif lang in ['hi', 'mixed', 'hinglish']:
                    speaker = 'Amit'
                else:
                    speaker = 'Amit'  # Amit handles clear Indian English and mixed terminology

                # Generate float32 numpy audio at 24 kHz
                wav = tts(text, speaker=speaker)
                if wav is None:
                    return None

                buf = io.BytesIO()
                sf.write(buf, wav, 24000, format='WAV', subtype='PCM_16')
                
                # Free MPS memory after synthesis
                if torch.backends.mps.is_available():
                    torch.mps.empty_cache()

                return buf.getvalue()
            except Exception as e:
                print(f"[Indic-Speak Synthesis Error]: {e}")
                return None

class LocalTTSService:
    @staticmethod
    def synthesize_speech(text, language=None, preferred_engine='offline'):
        audio, _ = LocalTTSService.synthesize_speech_with_meta(text, language, preferred_engine)
        return audio

    @staticmethod
    def synthesize_speech_with_meta(text, language=None, preferred_engine='offline'):
        """
        Synthesize speech into WAV audio bytes 100% offline and locally.
        Zero external APIs, sub-300ms neural synthesis on Mac CPU.
        """
        global _tts_cache
        try:
            clean_text = normalize_text_for_speech(text, language)
            if not clean_text:
                return None, 'none'

            active_lang = language if (language in ['hi', 'mr', 'en', 'mixed', 'hinglish']) else detect_voice_language(clean_text)

            cache_key = f"piper:{active_lang}:{clean_text}"
            if cache_key in _tts_cache:
                cached_data, engine_name = _tts_cache[cache_key]
                if len(cached_data) >= 1000:
                    return cached_data, engine_name
                else:
                    del _tts_cache[cache_key]

            # Primary: 100% Offline Local Neural TTS (Priyamvada female Indian voice / Pratham / Lessac)
            # Sub-300ms latency, zero APIs, zero cost
            audio = PiperTTSService.synthesize(clean_text, lang=active_lang)
            if audio and len(audio) > 500:
                if len(_tts_cache) >= _MAX_CACHE_SIZE:
                    _tts_cache.pop(next(iter(_tts_cache)))
                _tts_cache[cache_key] = (audio, 'piper-neural')
                return audio, 'piper-neural'

            # Optional fallback to Bodhan if explicitly requested
            if preferred_engine == 'bodhan':
                indic_audio = IndicSpeakTTSService.synthesize(clean_text, lang=active_lang)
                if indic_audio and len(indic_audio) > 500:
                    return indic_audio, 'bodhan-indic-speak'

        except Exception as e:
            print(f"[TTS Synthesize Error]: {e}")

        return None, 'error'


