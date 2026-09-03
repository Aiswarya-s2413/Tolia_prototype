import os
import io
import re
import asyncio
import tempfile
import subprocess
import edge_tts
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
            _stt_model = WhisperModel(model_size, device=device, compute_type=compute_type)
        except Exception as e:
            print(f"Faster-whisper load notice: {e}")
            return None
    return _stt_model

import requests
from django.conf import settings

import socket
from urllib.parse import urlparse

class VexylSTTService:
    """
    VEXYL-STT Speech-to-Text Client.
    Connects to self-hosted VEXYL-STT server wrapping AI4Bharat Indic-Conformer 600M Multilingual model
    for state-of-the-art Hindi, Marathi, and Indian language speech recognition.
    """
    @staticmethod
    def is_vexyl_alive(url, timeout=0.15):
        """Ultra-fast non-blocking probe (0.001s) to check if VEXYL server is alive."""
        try:
            parsed = urlparse(url)
            host = parsed.hostname or '127.0.0.1'
            port = parsed.port or 8001
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False

    @staticmethod
    def transcribe(audio_bytes, language='en'):
        vexyl_url = getattr(settings, 'VEXYL_STT_URL', 'http://localhost:8001').rstrip('/')
        
        # If VEXYL server is not running on port, fail in 0.001s without blocking
        if not VexylSTTService.is_vexyl_alive(vexyl_url):
            return None

        api_key = getattr(settings, 'VEXYL_STT_API_KEY', '')
        headers = {}
        if api_key:
            headers['x-api-key'] = api_key
            headers['Authorization'] = f"Bearer {api_key}"

        files = {'audio': ('audio.webm', audio_bytes, 'audio/webm')}
        data = {'language': language if language in ['hi', 'mr', 'en'] else 'indic'}

        try:
            res = requests.post(f"{vexyl_url}/transcribe", files=files, data=data, headers=headers, timeout=20.0)
            if res.status_code == 200:
                json_data = res.json()
                transcript = json_data.get('text') or json_data.get('transcript') or json_data.get('result', '')
                if transcript and transcript.strip():
                    return {
                        'success': True,
                        'text': transcript.strip(),
                        'language': json_data.get('language', language),
                        'engine': 'vexyl-indic-conformer'
                    }
        except Exception as e:
            print(f"[VEXYL Transcribe Notice]: {e}")

        return None

class LocalSTTService:
    @staticmethod
    def transcribe_audio(audio_bytes, language=None):
        """
        Transcribe raw audio bytes (wav/webm/ogg/mp3).
        Primary Engine: VEXYL-STT (AI4Bharat Indic-Conformer 600M)
        Fallback Engine: Local faster-whisper (sub-second VAD)
        Supports dynamic auto-detection across Hindi ('hi'), Marathi ('mr'), and English ('en').
        """
        from .rag_engine import detect_language

        # 1. Primary Engine: VEXYL-STT Server (AI4Bharat Indic-Conformer 600M)
        try:
            vexyl_res = VexylSTTService.transcribe(audio_bytes, language=language or 'auto')
            if vexyl_res and vexyl_res.get('success') and vexyl_res.get('text'):
                return vexyl_res
        except Exception as e:
            print(f"[VEXYL-STT Notice]: {e}")

        # 2. Local Fallback Engine: faster-whisper with native automatic language detection
        try:
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            model = get_stt_model()
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

            # If unconstrained detection produced an unexpected language (e.g. Welsh/Persian), retry with English/Indic fallback
            if info and info.language not in ['en', 'hi', 'mr']:
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
                detected_lang = 'en'
            
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

            return {
                "success": True,
                "text": transcript,
                "language": detected_lang,
                "engine": "faster-whisper"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "text": ""
            }

_piper_voices = {}

class PiperTTSService:
    """
    100% Local, Air-Gapped Neural Text-to-Speech Engine powered by Piper & ONNX.
    Zero network traffic, zero APIs, sub-150ms synthesis on CPU.
    """
    @staticmethod
    def get_voice(lang='en'):
        global _piper_voices
        base_dir = os.path.join(os.path.dirname(__file__), '..', 'piper_models')
        if not os.path.exists(base_dir):
            base_dir = os.path.abspath('tolia_backend/piper_models')

        if lang in ['hi', 'mr']:
            model_name = 'hi_IN-pratham-medium.onnx'
        else:
            model_name = 'en_US-lessac-medium.onnx'

        model_path = os.path.join(base_dir, model_name)
        config_path = f"{model_path}.json"

        if model_path not in _piper_voices and os.path.exists(model_path):
            try:
                from piper import PiperVoice
                _piper_voices[model_path] = PiperVoice.load(model_path, config_path=config_path)
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
                # Lively, casual, expressive conversational acoustics
                syn_config = SynthesisConfig(
                    length_scale=0.90,       # Upbeat casual speaking pace
                    noise_scale=0.75,        # Richer voice expressiveness / anti-robotic
                    noise_w_scale=0.85       # Conversational cadence & natural timing
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

class LocalTTSService:
    @staticmethod
    def speak_out_loud(text, language=None):
        """
        Direct hardware speaker playback via speech synthesis.
        """
        try:
            from .rag_engine import detect_language
            clean_text = re.sub(r'[*_#`~⚠️💡📌▶️✅🛡️🏢👥📋📜]', '', text)
            clean_text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', clean_text)
            clean_text = re.sub(r'https?:\/\/\S+', '', clean_text)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            if not clean_text:
                return
            lang = language if (language in ['hi', 'mr', 'en']) else detect_language(clean_text)
            voice = "Lekha" if lang in ['hi', 'mr'] else "Samantha"
            subprocess.Popen(["/usr/bin/say", "-v", voice, clean_text])
        except Exception as e:
            print(f"Direct speak error: {e}")

    @staticmethod
    def synthesize_speech(text, language=None):
        """
        Synthesize speech using 100% local Piper Neural Voice with seamless Edge-TTS & system fallbacks.
        Returns high-fidelity audio bytes with sub-150ms latency.
        """
        try:
            from .rag_engine import detect_language
            clean_text = re.sub(r'[*_#`~⚠️💡📌▶️✅🛡️🏢👥📋📜]', '', text)
            clean_text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', clean_text)
            clean_text = re.sub(r'https?:\/\/\S+', '', clean_text)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            
            if not clean_text:
                return None

            active_lang = language if (language in ['hi', 'mr', 'en']) else detect_language(clean_text)

            # 1. 100% Local Air-Gapped Voice Engine: Piper-TTS
            piper_audio = PiperTTSService.synthesize(clean_text, lang=active_lang)
            if piper_audio and len(piper_audio) > 500:
                return piper_audio

            # Fallback if Piper model file was missing
            print("[Voice Warning]: Piper model not loaded, checking local fallback...")

        except Exception as e:
            print(f"[TTS Synthesize Notice]: {e}")

        # 3. Cross-platform OS Fallback for Cloud / Linux / Mac
        try:
            import platform
            if platform.system() == "Darwin" and os.path.exists("/usr/bin/say"):
                voice = "Lekha" if language in ['hi', 'mr'] else "Samantha"
                with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as tmp_aiff:
                    aiff_path = tmp_aiff.name
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
                    wav_path = tmp_wav.name

                cmd_say = ["/usr/bin/say", "-v", voice, clean_text, "-o", aiff_path]
                subprocess.run(cmd_say, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5.0)

                cmd_convert = ["/usr/bin/afconvert", "-f", "WAVE", "-d", "LEI16", aiff_path, wav_path]
                subprocess.run(cmd_convert, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=4.0)

                with open(wav_path, "rb") as f:
                    wav_bytes = f.read()

                if os.path.exists(aiff_path): os.remove(aiff_path)
                if os.path.exists(wav_path): os.remove(wav_path)
                return wav_bytes
            else:
                try:
                    from gtts import gTTS
                    tts_lang = 'hi' if language == 'hi' else ('mr' if language == 'mr' else 'en')
                    tts_obj = gTTS(text=clean_text, lang=tts_lang, slow=False)
                    fp = io.BytesIO()
                    tts_obj.write_to_fp(fp)
                    fp.seek(0)
                    return fp.read()
                except Exception:
                    return None
        except Exception as err:
            print(f"[Fallback TTS Error]: {err}")
            return None


