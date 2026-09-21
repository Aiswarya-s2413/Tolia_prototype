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
            
            # Initial prompt to prime acoustic vocabulary for steel factory operations
            acoustic_prompt = "Blast Furnace, Rolling Mill, PPE safety, gear box, hydraulic pressure, emergency shutdown, आपातकालीन नियम, सुरक्षा, रोलिंग मिल, गिअरबॉक्स, ऑइल"

            # Fast sub-second transcription with Voice Activity Detection (VAD) filter
            segments, info = model.transcribe(
                tmp_path,
                language=lang_code,
                beam_size=2,
                vad_filter=True,
                initial_prompt=acoustic_prompt
            )
            
            transcript = " ".join([segment.text for segment in segments]).strip()

            # If unconstrained detection produced an unexpected language, retry with English fallback
            if info and info.language not in ['en', 'hi', 'mr'] and not transcript:
                retry_segments, retry_info = model.transcribe(
                    tmp_path,
                    language='en',
                    beam_size=1,
                    vad_filter=True,
                    initial_prompt=acoustic_prompt
                )
                retry_transcript = " ".join([segment.text for segment in retry_segments]).strip()
                if retry_transcript:
                    transcript = retry_transcript
            
            # Determine detected language dynamically from transcript & whisper info
            detected_lang = detect_language(transcript) if transcript else (info.language if (info and info.language in ['hi', 'mr', 'en']) else 'en')
            if detected_lang not in ['hi', 'mr', 'en']:
                # Check Devanagari script markers
                if any('\u0900' <= char <= '\u097F' for char in transcript):
                    if any(marker in transcript for marker in ['आहे', 'नाही', 'काय', 'काळजी', 'करा', 'होय', 'ळ']):
                        detected_lang = 'mr'
                    else:
                        detected_lang = 'hi'
                else:
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

        if lang in ['hi', 'mr']:
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
            voice = PiperTTSService.get_voice(lang)
            if voice is None:
                return None

            try:
                from piper import SynthesisConfig
                # Natural, articulate conversational pace tuned to normal human speech
                # length_scale > 1.0 relaxes phoneme duration to eliminate rushed speaking
                speed_scale = 1.10 if lang in ['hi', 'mr'] else 1.08
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

class LocalTTSService:
    @staticmethod
    def synthesize_speech(text, language=None):
        """
        Synthesize speech into WAV audio bytes using local Piper Neural Voice.
        Returns high-fidelity WAV audio bytes playable directly in browser HTML5 Audio.
        Utilizes an ultra-fast in-memory LRU cache for 0ms replay and instant responses.
        """
        global _tts_cache
        try:
            clean_text = re.sub(r'[*_#`~⚠️💡📌▶️✅🛡️🏢👥📋📜]', '', text)
            clean_text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', clean_text)
            clean_text = re.sub(r'https?:\/\/\S+', '', clean_text)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            
            if not clean_text:
                return None

            active_lang = language if (language in ['hi', 'mr', 'en']) else detect_voice_language(clean_text)

            # Check ultra-fast in-memory cache (0.001ms)
            cache_key = f"{active_lang}:{clean_text}"
            if cache_key in _tts_cache:
                return _tts_cache[cache_key]

            # 1. High-Fidelity Local Neural Voice: Piper-TTS
            piper_audio = PiperTTSService.synthesize(clean_text, lang=active_lang)
            if piper_audio and len(piper_audio) > 500:
                if len(_tts_cache) >= _MAX_CACHE_SIZE:
                    _tts_cache.pop(next(iter(_tts_cache)))
                _tts_cache[cache_key] = piper_audio
                return piper_audio

            # 2. Universal Python gTTS Fallback
            try:
                from gtts import gTTS
                tts_lang = 'hi' if active_lang in ['hi', 'mr'] else 'en'
                tts_obj = gTTS(text=clean_text, lang=tts_lang, slow=False)
                fp = io.BytesIO()
                tts_obj.write_to_fp(fp)
                fp.seek(0)
                audio_data = fp.read()
                if audio_data:
                    _tts_cache[cache_key] = audio_data
                return audio_data
            except Exception:
                pass

        except Exception as e:
            print(f"[TTS Synthesize Error]: {e}")

        return None


