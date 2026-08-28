import os
import io
import re
import asyncio
import tempfile
import subprocess
import edge_tts
from faster_whisper import WhisperModel

_stt_model = None

def get_stt_model():
    """Lazy load faster-whisper STT model locally."""
    global _stt_model
    if _stt_model is None:
        device = "cpu"
        compute_type = "int8"
        model_size = os.getenv("WHISPER_MODEL_SIZE", "base")
        _stt_model = WhisperModel(model_size, device=device, compute_type=compute_type)
    return _stt_model

import requests
from django.conf import settings

class VexylSTTService:
    """
    VEXYL-STT Speech-to-Text Client.
    Connects to self-hosted VEXYL-STT server wrapping AI4Bharat Indic-Conformer 600M Multilingual model
    for state-of-the-art Hindi, Marathi, and Indian language speech recognition.
    """
    @staticmethod
    def transcribe(audio_bytes, language='en'):
        vexyl_url = getattr(settings, 'VEXYL_STT_URL', 'http://localhost:8001').rstrip('/')
        api_key = getattr(settings, 'VEXYL_STT_API_KEY', '')
        
        headers = {}
        if api_key:
            headers['x-api-key'] = api_key
            headers['Authorization'] = f"Bearer {api_key}"

        endpoints = [
            f"{vexyl_url}/transcribe",
            f"{vexyl_url}/api/v1/transcribe",
            f"{vexyl_url}/v1/audio/transcriptions"
        ]

        files = {'audio': ('audio.webm', audio_bytes, 'audio/webm')}
        data = {'language': language}

        for endpoint in endpoints:
            try:
                res = requests.post(endpoint, files=files, data=data, headers=headers, timeout=5.0)
                if res.status_code == 200:
                    json_data = res.json()
                    transcript = json_data.get('text') or json_data.get('transcript') or json_data.get('result', '')
                    if transcript:
                        return {
                            'success': True,
                            'text': transcript.strip(),
                            'language': json_data.get('language', language),
                            'engine': 'vexyl-indic-conformer'
                        }
            except Exception:
                continue

        return None

class LocalSTTService:
    @staticmethod
    def transcribe_audio(audio_bytes, language=None):
        """
        Transcribe raw audio bytes (wav/webm/ogg/mp3).
        Primary Engine: VEXYL-STT (AI4Bharat Indic-Conformer 600M)
        Fallback Engine: Local faster-whisper
        Supports Hindi ('hi'), Marathi ('mr'), English ('en') and auto-detection.
        """
        # 1. Primary Engine: VEXYL-STT Server
        vexyl_res = VexylSTTService.transcribe(audio_bytes, language=language or 'en')
        if vexyl_res and vexyl_res.get('success'):
            return vexyl_res

        # 2. Local Fallback Engine: faster-whisper
        try:
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            model = get_stt_model()
            lang_code = language if language in ['hi', 'mr', 'en'] else None
            segments, info = model.transcribe(tmp_path, language=lang_code, beam_size=3)
            
            transcript = " ".join([segment.text for segment in segments]).strip()
            detected_lang = info.language if info else (language or 'en')
            
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

class LocalTTSService:
    @staticmethod
    def speak_out_loud(text, language='en'):
        """
        Direct hardware speaker playback via speech synthesis.
        """
        try:
            clean_text = re.sub(r'[*_#`~⚠️💡📌▶️✅🛡️🏢👥📋📜]', '', text)
            clean_text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', clean_text)
            clean_text = re.sub(r'https?:\/\/\S+', '', clean_text)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            if not clean_text:
                return
            voice = "Lekha" if language in ['hi', 'mr'] else "Samantha"
            subprocess.Popen(["/usr/bin/say", "-v", voice, clean_text])
        except Exception as e:
            print(f"Direct speak error: {e}")

    @staticmethod
    def synthesize_speech(text, language='en'):
        """
        Synthesize speech using state-of-the-art Neural Indian Voice models.
        Returns high-fidelity audio bytes with sub-second response time.
        """
        try:
            clean_text = re.sub(r'[*_#`~⚠️💡📌▶️✅🛡️🏢👥📋📜]', '', text)
            clean_text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', clean_text)
            clean_text = re.sub(r'https?:\/\/\S+', '', clean_text)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            
            if not clean_text:
                return None

            # Select Indian Neural voice based on language
            voice_map = {
                'hi': 'hi-IN-SwaraNeural',   # Natural Hindi Female voice
                'mr': 'mr-IN-AarohiNeural',  # Natural Marathi Female voice
                'en': 'en-IN-NeerjaNeural'   # Natural Indian English Female voice
            }
            voice = voice_map.get(language, 'en-IN-NeerjaNeural')

            async def _synthesize():
                communicate = edge_tts.Communicate(clean_text, voice)
                audio_data = b""
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_data += chunk["data"]
                return audio_data

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        audio_bytes = pool.submit(asyncio.run, _synthesize()).result(timeout=10)
                else:
                    audio_bytes = loop.run_until_complete(_synthesize())
            except Exception:
                audio_bytes = asyncio.run(_synthesize())

            if audio_bytes and len(audio_bytes) > 0:
                return audio_bytes

        except Exception as e:
            print(f"[Neural TTS] Edge synthesis error, falling back to system audio: {e}")

        # Fallback to system say command if offline
        try:
            voice = "Lekha" if language in ['hi', 'mr'] else "Samantha"
            with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as tmp_aiff:
                aiff_path = tmp_aiff.name
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
                wav_path = tmp_wav.name

            cmd_say = ["/usr/bin/say", "-v", voice, clean_text, "-o", aiff_path]
            subprocess.run(cmd_say, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=8.0)

            cmd_convert = ["/usr/bin/afconvert", "-f", "WAVE", "-d", "LEI16", aiff_path, wav_path]
            subprocess.run(cmd_convert, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5.0)

            with open(wav_path, "rb") as f:
                wav_bytes = f.read()

            if os.path.exists(aiff_path): os.remove(aiff_path)
            if os.path.exists(wav_path): os.remove(wav_path)
            return wav_bytes
        except Exception as err:
            print(f"[Fallback TTS Error]: {err}")
            return None


