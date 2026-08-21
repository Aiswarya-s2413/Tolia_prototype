import os
import io
import re
import tempfile
import subprocess
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

class LocalSTTService:
    @staticmethod
    def transcribe_audio(audio_bytes, language=None):
        """
        Transcribe raw audio bytes (wav/webm/ogg/mp3) locally.
        Supports Hindi ('hi'), Marathi ('mr'), English ('en') and auto-detection.
        """
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
                "language": detected_lang
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
        Direct hardware speaker playback via macOS speech synthesis.
        Bypasses browser audio sandbox and tab muting completely.
        """
        try:
            clean_text = re.sub(r'[*_#`~⚠️💡📌▶️✅🛡️🏢👥📋📜]', '', text)
            clean_text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', clean_text)
            clean_text = re.sub(r'https?:\/\/\S+', '', clean_text)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            if not clean_text:
                return
            voice = "Lekha" if language in ['hi', 'mr'] else "Rishi"
            subprocess.Popen(["/usr/bin/say", "-v", voice, clean_text])
        except Exception as e:
            print(f"Direct speak error: {e}")

    @staticmethod
    def synthesize_speech(text, language='en'):
        """
        Synthesize speech locally using native high-fidelity neural voice engine.
        Returns standard uncompressed 16-bit PCM WAV audio bytes.
        """
        try:
            # Clean markup tags, urls, bullet formatting
            clean_text = re.sub(r'[*_#`~⚠️💡📌▶️✅🛡️🏢👥📋📜]', '', text)
            clean_text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', clean_text)
            clean_text = re.sub(r'https?:\/\/\S+', '', clean_text)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            
            if not clean_text:
                return None

            # Also trigger hardware audio output directly
            LocalTTSService.speak_out_loud(clean_text, language)

            # Choose best installed voice for requested language
            voice = "Rishi" # Default Indian English
            if language in ['hi', 'mr']:
                voice = "Lekha" # Native Hindi / Devanagari voice
            elif language == 'en':
                voice = "Rishi" # Indian English voice

            # Create temporary files
            with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as tmp_aiff:
                aiff_path = tmp_aiff.name
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
                wav_path = tmp_wav.name

            # Run say command to generate high-fidelity AIFF
            cmd_say = ["/usr/bin/say", "-v", voice, clean_text, "-o", aiff_path]
            res_say = subprocess.run(cmd_say, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=8.0)

            # Fallback if specific voice is not installed
            if res_say.returncode != 0 or not os.path.exists(aiff_path) or os.path.getsize(aiff_path) == 0:
                cmd_say_fallback = ["/usr/bin/say", clean_text, "-o", aiff_path]
                subprocess.run(cmd_say_fallback, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=8.0)

            # Convert AIFF to standard browser-compatible WAV via afconvert (0.001s)
            cmd_convert = ["/usr/bin/afconvert", "-f", "WAVE", "-d", "LEI16", aiff_path, wav_path]
            subprocess.run(cmd_convert, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5.0)

            with open(wav_path, "rb") as f:
                wav_bytes = f.read()

            # Clean temp files
            if os.path.exists(aiff_path):
                os.remove(aiff_path)
            if os.path.exists(wav_path):
                os.remove(wav_path)

            return wav_bytes
        except Exception as e:
            print(f"LocalTTSService Error: {e}")
            return None
