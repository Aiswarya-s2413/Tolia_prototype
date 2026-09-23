import re
import socket
import requests
import json
import math
import time
from urllib.parse import urlparse
from collections import Counter
from django.conf import settings
from .models import Document, DocumentChunk, Department, DocumentCategory

def is_ollama_alive(url, timeout=0.015):
    """Fast non-blocking check to verify if Ollama daemon is active in < 15ms without hanging on timeout."""
    try:
        parsed = urlparse(url)
        host = parsed.hostname or '127.0.0.1'
        port = parsed.port or 11434
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False

def _get_ollama_base_url():
    """Detect active Ollama endpoint (Local Mac Tunnel 11435 first with qwen3.8, then local 11434)."""
    if is_ollama_alive("http://127.0.0.1:11435", timeout=0.05):
        return "http://127.0.0.1:11435"
    default_url = getattr(settings, 'OLLAMA_BASE_URL', 'http://127.0.0.1:11434')
    return default_url

def _get_active_ollama_model():
    """Discover the best active model in Ollama (e.g., qwen3.8:latest, qwen3.8, qwen2.5:7b)."""
    try:
        base_url = _get_ollama_base_url()
        res = requests.get(f"{base_url}/api/tags", timeout=0.3)
        if res.status_code == 200:
            available = [m.get("name", "") for m in res.json().get("models", [])]
            preferred_order = [
                getattr(settings, 'OLLAMA_MODEL', 'qwen3.8:latest'),
                'qwen3.8:latest',
                'qwen3.8',
                'qwen2.5:7b',
                'qwen2.5:1.5b',
                'qwen2.5',
                'llama3'
            ]
            for pref in preferred_order:
                for avail in available:
                    if avail == pref or avail.startswith(pref):
                        return avail
            if available:
                return available[0]
    except Exception:
        pass
    return getattr(settings, 'OLLAMA_MODEL', 'qwen3.8:latest')

def detect_language(text):
    """
    Dynamically detect language ('en', 'hi', 'mr', or 'mixed' for Hindi+English / Hinglish)
    from user query or speech transcript.
    """
    if not text or not text.strip():
        return 'en'
    
    text_lower = text.lower().strip()

    # 1. Distinct Marathi markers & vocabulary (Devanagari script + Latin transliterations)
    marathi_unique_chars = re.findall(r'[\u0933\u0950]', text) # ळ
    marathi_devanagari_words = [
        'काय', 'कसे', 'कशी', 'कशा', 'कधी', 'कुठे', 'कोण', 'आहे', 'आहेत', 'आहोत', 'नाही', 'नाहीत',
        'सांगा', 'सांग', 'माहिती', 'करावे', 'करावा', 'करावी', 'द्या', 'द्यावे', 'होते',
        'झाले', 'झाली', 'झाला', 'पाहिजे', 'तुम्ही', 'तुम्हाला', 'माझा', 'माझी', 'माझे',
        'तुझा', 'तुझी', 'तुझे', 'आपला', 'आपली', 'आपले', 'कारखाना', 'कारखान्यातील', 'धोरण',
        'आपत्कालीन', 'दाब', 'तपासा', 'वापरा', 'विक्री', 'वैशिष्ट्ये', 'टोलिया काय'
    ]
    marathi_latin_words = [
        'kay', 'aahe', 'ahe', 'aahet', 'ahet', 'sanga', 'sang', 'mahiti', 'kase', 'kashi', 'kasha',
        'kadhi', 'kuthe', 'tuzi', 'tujha', 'tujhe', 'majha', 'majhi', 'majhe', 'amhi', 'tumhi', 'tumhala',
        'karu', 'shakto', 'shakta', 'shaktat', 'karto', 'kartos', 'kartay', 'pahije',
        'ahes', 'aahat', 'astat', 'baddal', 'sathi', 'karkhana', 'dhoran'
    ]

    if marathi_unique_chars:
        return 'mr'

    for kw in marathi_devanagari_words:
        if re.search(rf'(^|\s|[^\w\u0900-\u097F]){re.escape(kw)}($|\s|[^\w\u0900-\u097F])', text):
            return 'mr'

    for kw in marathi_latin_words:
        if re.search(rf'\b{re.escape(kw)}\b', text_lower):
            return 'mr'

    # 2. Check for Mixed Language (Hindi + English / Hinglish) & Hindi
    hindi_devanagari_words = [
        'क्या', 'कैसे', 'कैसा', 'कैसी', 'कब', 'कहाँ', 'कहा', 'है', 'हैं', 'हो', 'हूँ', 'हू',
        'बताओ', 'बताइए', 'बताएं', 'बतायें', 'सुरक्षा', 'करो', 'कीजिए', 'करें', 'चाहिए', 'सकते',
        'सकता', 'सकती', 'तुम्हारा', 'तुम्हारी', 'तुम्हारे', 'आपका', 'आपकी', 'आपके', 'मेरा', 'मेरी',
        'मेरे', 'नमस्ते', 'बारे', 'में', 'लिए', 'करना', 'करता', 'करती', 'होगी', 'होगा', 'होंगे',
        'संयंत्र', 'उद्देश्य', 'बिक्री', 'कीमत', 'आपातकालीन', 'टोलिया क्या', 'कितना', 'कितने', 'कितनी'
    ]
    hindi_latin_words = [
        'kya', 'kaise', 'kaisa', 'kaisi', 'kab', 'kaha', 'kahan', 'hai', 'hain', 'batao', 'bataiye',
        'karo', 'kijiye', 'chahiye', 'sakte', 'sakta', 'sakti', 'tumhara', 'tumhari', 'tumhare',
        'aapka', 'aapki', 'aapke', 'mera', 'meri', 'mere', 'namaste', 'liye', 'karna', 'karta',
        'kare', 'karein', 'hoga', 'hogi', 'hota', 'hote', 'hoti', 'kitna', 'kitni', 'kitne',
        'ka', 'ki', 'ke', 'ko', 'se', 'me', 'mein', 'par', 'aur', 'agar', 'toh', 'nahi'
    ]

    devanagari_chars = re.findall(r'[\u0900-\u097F]', text)
    english_words = re.findall(r'\b[a-zA-Z]{3,}\b', text)

    has_hindi_latin = any(re.search(rf'\b{re.escape(kw)}\b', text_lower) for kw in hindi_latin_words)
    has_devanagari_word = any(re.search(rf'(^|\s|[^\w\u0900-\u097F]){re.escape(kw)}($|\s|[^\w\u0900-\u097F])', text) for kw in hindi_devanagari_words)

    # Technical or English vocabulary commonly used in plant queries
    english_technical_terms = [
        'blast', 'furnace', 'emergency', 'shutdown', 'pressure', 'temperature', 'hydraulic', 'oil',
        'rolling', 'mill', 'gearbox', 'safety', 'ppe', 'helmet', 'shoes', 'rules', 'sop', 'sops',
        'plant', 'factory', 'check', 'standard', 'testing', 'hardness', 'help', 'role', 'access',
        'valve', 'bar', 'vibration', 'limit', 'step', 'steps', 'guidelines', 'alarm', 'gas', 'water',
        'what', 'how', 'tell', 'show', 'status', 'level', 'flow', 'bearing', 'system'
    ]
    has_english_terms = any(re.search(rf'\b{re.escape(w)}\b', text_lower) for w in english_technical_terms)

    # If Hindi words are written in Latin script with English keywords -> Mixed / Hinglish
    if has_hindi_latin:
        if has_english_terms or len(english_words) >= 2:
            return 'mixed'
        return 'hi'

    # If Devanagari is mixed with English words -> Mixed / Hinglish
    if len(devanagari_chars) > 0:
        if len(english_words) >= 1 or has_english_terms:
            return 'mixed'
        return 'hi'

    if has_devanagari_word:
        return 'hi'

    # Default to English
    return 'en'

def is_hindi(text):
    """Detect if input text is Hindi or Marathi."""
    return detect_language(text) in ['hi', 'mr']

def is_sales_marketing_query(query_text):
    """Check if query is targeting sales/marketing/pricing data."""
    sales_terms = [
        'sales', 'marketing', 'revenue', 'price', 'pricing', 'target', 'client',
        'customer', 'profit', 'margin', 'q1', 'q2', 'q3', 'q4', 'bikri', 'kimat', 'munafa'
    ]
    query_lower = query_text.lower()
    return any(term in query_lower for term in sales_terms)

def is_general_or_meta_query(query_text):
    """Check if query is asking about assistant capabilities, functionalities, purpose, identity, or general help/greetings."""
    q_norm = normalize_voice_query(query_text).lower().strip()
    q_clean = re.sub(r'[^\w\s\u0900-\u097F]', ' ', q_norm)
    words = [w for w in q_clean.split() if w]
    words_set = set(words)

    # 1. Direct Regex Patterns
    patterns = [
        r'\b(what\s+(all\s+)?(things\s+)?can\s+you\s+do)\b',
        r'\b(what\s+are\s+you)\b',
        r'\b(who\s+are\s+you)\b',
        r'\b(what\s+is\s+your\s+name)\b',
        r'\b(who\s+is\s+tolia(\s+ai)?)\b',
        r'\b(what\s+is\s+tolia(\s+ai)?)\b',
        r'\b(who\s+(created|built|made|developed)\s+you)\b',
        r'\b(tell\s+me\s+about\s+yourself)\b',
        r'\b(introduce\s+yourself)\b',
        r'\b(what\s+are\s+your\s+(functionalities|functionality|functions|features|capabilities|capability|services|tasks|roles|skills|uses))\b',
        r'\b(what\s+is\s+your\s+(functionality|function|purpose|feature|capability|role|job|task))\b',
        r'\b(what\s+is\s+(its|this)\s+(purpose|functionality|feature|role))\b',
        r'\b(what\s+(functionalities|capabilities|features)\s+do\s+you\s+have)\b',
        r'\b(what\s+can\s+you\s+do(\s+for\s+me)?)\b',
        r'\b(what\s+do\s+you\s+do)\b',
        r'\b(how\s+can\s+you\s+(help|assist)(\s+me)?)\b',
        r'\b(what\s+(help|assistance)\s+can\s+you\s+provide)\b',
        r'\b((explain|describe|list)\s+your\s+(features|capabilities|functionalities|functions))\b',
        r'\b(what\s+is\s+this\s+(system|bot|assistant|app|ai))\b',
        r'\b(how\s+does\s+this\s+(system|bot|assistant|app|ai)\s+work)\b',
        r'\b(how\s+do\s+you\s+work)\b',
        r'\b(kya\s+kar\s+sakte\s+ho)\b',
        r'\b(tum\s+kya\s+karte\s+ho)\b',
        r'\b(tum\s+kaun\s+ho)\b',
        r'\b(aap\s+kaun\s+hain)\b',
        r'\b(tumhara\s+naam\s+kya\s+hai)\b',
        r'\b(tumhara\s+(kya\s+)?(uddeshya|kam|kaam)\s+hai)\b',
        r'\b(aap\s+kya\s+kar\s+sakte\s+hain)\b',
        r'\b(tolia\s+kya\s+hai)\b',
        r'\b(kay\s+karu\s+shakta)\b',
        r'\b(tu\s+kon\s+aahes)\b',
        r'\b(tumhi\s+kon\s+aahat)\b',
        r'\b(tuzi\s+mahiti)\b',
        r'\b(tujha\s+uddesh)\b',
        r'(क्या\s+कर\s+सकते)',
        r'(तुम\s+कौन\s+हो)',
        r'(आप\s+कौन\s+हैं)',
        r'(तुम्हारा\s+नाम)',
        r'(तुम्हारा\s+उद्देश्य)',
        r'(टोलिया\s+क्या\s+है)',
        r'(आप\s+क्या\s+कर\s+सकते)',
        r'(काय\s+करू\s+शकता)',
        r'(तू\s+कोण\s+आहेस)',
        r'(तुम्ही\s+कोण\s+आहात)',
        r'(काय\s+करतोस)',
        r'(तुझे\s+काम\s+काय)',
        r'(तुझा\s+उद्देश)',
        r'(टोलिया\s+काय\s+आहे)'
    ]

    for pat in patterns:
        if re.search(pat, q_clean):
            return True

    # 2. Semantic Token / Stem Matching
    meta_triggers = {'what', 'who', 'how', 'tell', 'explain', 'describe', 'list', 'show', 'kya', 'kaise', 'kay', 'kon', 'क्या', 'कैसे', 'कौन', 'काय', 'कसे'}
    target_tokens = {'you', 'your', 'yourself', 'tolia', 'bot', 'assistant', 'system', 'app', 'ai', 'tum', 'aap', 'tumhara', 'apka', 'tu', 'tuzi', 'tujha', 'तुम', 'आप', 'तुम्हारा', 'आपका', 'तुम्ही', 'तू', 'तुझे', 'तुझा', 'टोलिया'}
    
    capability_stems = (
        'functio', 'capabilit', 'featur', 'purpos', 'abilit', 'skill', 'task', 'servic',
        'assist', 'help', 'role', 'work', 'use', 'usage', 'name', 'identity',
        'kar', 'kam', 'kaam', 'uddeshya', 'shakto', 'shakta', 'madat', 'upayog',
        'कर', 'काम', 'उद्देश्य', 'मदद', 'करू', 'शकता', 'कार्य', 'वैशिष्ट्ये', 'क्षमता', 'नाव', 'नाम'
    )

    has_meta = any(w in meta_triggers for w in words_set)
    has_target = any(w in target_tokens for w in words_set)
    has_capability = any(any(w.startswith(stem) for stem in capability_stems) for w in words_set)

    if has_target and (has_meta or has_capability):
        return True

    if has_target and any(w in {'help', 'features', 'capabilities', 'functionalities', 'purpose', 'skills', 'name'} for w in words_set):
        return True

    # 3. Simple Greetings
    greetings = {'hello', 'hi', 'hey', 'namaste', 'namaskar', 'help', 'halo', 'pranam', 'good morning', 'good afternoon', 'good evening', 'नमस्ते', 'नमस्कार', 'प्रणाम'}
    if q_clean.strip() in greetings or (len(words_set) <= 2 and any(w in greetings for w in words_set)):
        return True

    return False

def get_general_assistant_response(query_text, target_lang='en', user_role=Department.QC):
    """Generate strictly accurate, precise explanation of Tolia AI purpose and capabilities in simple words."""
    if target_lang in ['mixed', 'hinglish']:
        return (
            "**Main Tolia AI hoon** — steel plant operations ke liye aapka voice assistant.\n\n"
            "• **Main aapki kaise help kar sakta hoon:**\n"
            "  1. Blast Furnace aur Rolling Mill ke emergency SOPs aur shutdown steps batana.\n"
            "  2. Machinery maintenance, hydraulic limits aur PPE safety rules explain karna.\n"
            "  3. Hindi, English aur Marathi mein bolkar instant answer dena."
        )
    elif target_lang == 'hi':
        return (
            "**मैं Tolia AI हूँ** — स्टील प्लांट संचालन के लिए आपका वॉयस असिस्टेंट।\n\n"
            "• **मैं आपकी क्या मदद कर सकता हूँ:**\n"
            "  1. ब्लास्ट फर्नेस और रोलिंग मिल के आपातकालीन नियम एवं SOP बताना।\n"
            "  2. मशीन रखरखाव, हाइड्रोलिक प्रेशर, और सुरक्षा गाइडलाइन्स समझाना।\n"
            "  3. हिंदी, मराठी और अंग्रेजी में बोलकर तुरंत जवाब देना।"
        )
    elif target_lang == 'mr':
        return (
            "**मी Tolia AI आहे** — स्टील कारखान्यासाठी तुमचा व्हॉइस असिस्टंट.\n\n"
            "• **मी कशी मदत करू शकतो:**\n"
            "  १. ब्लास्ट फर्नेस व रोलिंग मिलचे आपत्कालीन नियम आणि SOP सांगणे.\n"
            "  २. मशिन मेंटेनन्स, हायड्रोलिक प्रेशर आणि सुरक्षेची माहिती देणे.\n"
            "  ३. मराठी, हिंदी आणि इंग्रजीमध्ये बोलून तत्काळ उत्तर देणे."
        )
    else:
        return (
            "**I am Tolia AI** — your voice assistant for steel plant operations.\n\n"
            "• **How I can help you:**\n"
            "  1. Provide instant SOPs and emergency shutdown steps (Blast Furnace, Rolling Mill).\n"
            "  2. Explain machinery maintenance, hydraulic limits, and PPE safety rules.\n"
            "  3. Answer queries by voice in English, Hindi (हिंदी), and Marathi (मराठी)."
        )

def get_allowed_departments_for_role(user_role):
    """Return list of required_department tags a user role is permitted to see."""
    if user_role == Department.CEO:
        return [Department.QC, Department.CEO]
    else: # QC
        return [Department.QC]

def get_embedding(text):
    """Call local Ollama server (nomic-embed-text) to generate vector embedding."""
    try:
        base_url = _get_ollama_base_url()
        url = f"{base_url}/api/embed"
        payload = {"model": "nomic-embed-text", "input": text}
        res = requests.post(url, json=payload, timeout=3.0)
        if res.status_code == 200:
            data = res.json()
            embeddings = data.get("embeddings", [])
            if embeddings and len(embeddings) > 0:
                return embeddings[0]
    except Exception:
        pass
    return None

def clean_doc_title(title, target_lang):
    """Clean document title."""
    if target_lang == 'en':
        cleaned = re.sub(r'\s*\([\u0900-\u097F\s]+\)', '', title)
        return cleaned.strip()
    return title

def normalize_voice_query(query_text):
    """Normalize common voice STT phonetic mis-recognitions for industrial plant terms."""
    normalized = query_text.lower()
    
    # Common speech-to-text misrecognitions for plant terms
    replacements = [
        (r'\b(pps|ppa|ppe|pp is|pp\b|p\.p\.e|p p e|pee pee ee|pp e|pepe)\b', 'ppe'),
        (r'\b(plan|plnt|pln)\b', 'plant'),
        (r'\b(farnace|furnas|furness|firnace)\b', 'furnace'),
        (r'\b(blast farnace|blast furnas)\b', 'blast furnace'),
        (r'\b(sut down|shut down|shuting down|shutting down)\b', 'shutdown'),
        (r'\b(emergeny|emergancy|emegency)\b', 'emergency'),
        (r'\b(rolin|rooling|roling)\b', 'rolling'),
        (r'\b(gear box)\b', 'gearbox'),
        (r'\b(hidraulic|hydralic|hydroulic)\b', 'hydraulic'),
        (r'\b(safty|saftey|safe|safe req|safeties|safety)\b', 'safety'),
        (r'\b(temprature|temperatue|temp)\b', 'temperature'),
        (r'\b(helmit|halmet)\b', 'helmet'),
        (r'\b(corosion|corrosive)\b', 'corrosion'),
        (r'\b(hardnes|rockwel|rokwell)\b', 'hardness')
    ]
    
    for pattern, repl in replacements:
        normalized = re.sub(pattern, repl, normalized)
        
    return normalized

def score_chunk_relevance(query, chunk):
    """Calculate relevance score between query and document chunk using term matching, technical codes, and title weighting."""
    norm_query = normalize_voice_query(query)
    query_words = set(re.findall(r'\w+', norm_query.lower()))
    
    # Stop words
    stop_words = {'what', 'is', 'are', 'the', 'for', 'and', 'in', 'of', 'to', 'a', 'an', 'how', 'tell', 'give', 'me', 'kya', 'hai', 'ka', 'ke', 'ki', 'ko', 'me', 'batao', 'sanga'}
    keywords = [w for w in query_words if w not in stop_words and len(w) > 1]
    
    if not keywords:
        return 0.1

    doc_title_lower = chunk.document.title.lower()
    chunk_text_lower = chunk.text.lower()
    category_lower = chunk.document.category.lower()

    score = 0.0
    for kw in keywords:
        if kw in doc_title_lower:
            score += 8.0
        if kw in category_lower:
            score += 5.0
        count = chunk_text_lower.count(kw)
        score += count * 2.0

    # Technical codes & standards exact matching boost
    technical_codes = ['sop-bf-01', 'sop-rm-04', 'sop-saf-02', 'sop-qc-09', 'fin-2026', 'astm', 'e18', 'hrc', 'rockwell', 'iso vg 320', 'vg 320', '210 bar', '1450', '1550', '2.5 bar', 'valve b-4', 'snort valve', 'nitrogen', 'mud gun', '72,500', '125 crore', '550 crore']
    for code in technical_codes:
        if code in norm_query and code in chunk_text_lower:
            score += 35.0

    # Specific steel plant synonym boost
    q_norm_lower = norm_query.lower()
    if ('blast' in q_norm_lower or 'furnace' in q_norm_lower or 'फर्नेस' in query or 'ब्लास्ट' in query or 'tuyere' in q_norm_lower or 'taphole' in q_norm_lower) and 'blast furnace' in doc_title_lower:
        score += 25.0
    if ('shutdown' in q_norm_lower or 'emergency' in q_norm_lower or 'आपातकालीन' in query or 'आपत्कालीन' in query or 'siren' in q_norm_lower) and 'emergency' in chunk_text_lower:
        score += 20.0
    if ('rolling' in q_norm_lower or 'gearbox' in q_norm_lower or 'hydraulic' in q_norm_lower or 'रोलिंग' in query or 'vibration' in q_norm_lower or 'lubricant' in q_norm_lower) and 'rolling mill' in doc_title_lower:
        score += 25.0
    if ('ppe' in q_norm_lower or 'safety' in q_norm_lower or 'helmet' in q_norm_lower or 'सुरक्षा' in query or 'goggles' in q_norm_lower or 'ear' in q_norm_lower or 'smoking' in q_norm_lower) and 'safety' in doc_title_lower:
        score += 25.0
    if ('hardness' in q_norm_lower or 'testing' in q_norm_lower or 'hrc' in q_norm_lower or 'rockwell' in q_norm_lower or 'हार्डनेस' in query or 'crack' in q_norm_lower or 'austenite' in q_norm_lower) and 'quality' in doc_title_lower:
        score += 25.0
    if ('sales' in q_norm_lower or 'revenue' in q_norm_lower or 'target' in q_norm_lower or 'pricing' in q_norm_lower or 'बिक्री' in query or 'विक्री' in query or 'profit' in q_norm_lower or 'crore' in q_norm_lower) and 'sales' in doc_title_lower:
        score += 25.0

    return score

def is_plant_document_query(query_text, top_chunks=None):
    """
    Check whether a query specifically targets steel plant SOPs, machinery specifications,
    safety regulations, maintenance schedules, or uploaded plant documents.
    """
    if not query_text:
        return False
    q_lower = normalize_voice_query(query_text).lower()
    
    # Specific plant operations, machinery & SOP keywords
    plant_keywords = [
        'blast furnace', 'blast', 'furnace', 'ब्लास्ट', 'फर्नेस', 'rolling mill', 'rolling', 'mill', 'रोलिंग', 'मिल',
        'gearbox', 'गियरबॉक्स', 'गिअरबॉक्स', 'hydraulic', 'clamping', 'vibration', 'कंपन',
        'ppe', 'helmet', 'हेलमेट', 'safety shoes', 'ear plug', 'goggles', 'सुरक्षा नियम', 'safety rules',
        'grinding ball', 'grinding balls', 'hardness', 'rockwell', 'astm e18', 'हार्डनेस', 'hrc', 'cracks',
        'snort valve', 'nitrogen purge', 'valve b-4', 'main control valve', 'assembly point',
        'siren', 'hot metal tapping', 'mud gun', 'tuyere', 'taphole', 'iso vg 320', 'synthetic oil',
        '210 bar', '2.5 bar', '1450°c', '1550°c', 'sop-bf-01', 'sop-rm-04', 'sop-saf-02', 'sop-qc-09',
        'sales target', 'revenue report', 'operating profit margin', 'q1 revenue', 'q2 revenue', 'annual revenue',
        '72,500', '125 crore', '550 crore', 'mining clients', 'pricing data', 'plant sop', 'factory sop'
    ]
    
    if any(kw in q_lower for kw in plant_keywords):
        return True
        
    if top_chunks and len(top_chunks) > 0:
        top_score = score_chunk_relevance(query_text, top_chunks[0])
        if top_score >= 12.0:
            return True
            
    return False

class LocalRAGEngine:
    @staticmethod
    def get_embedding(text):
        return get_embedding(text)

    @staticmethod
    def retrieve_top_chunks(user_query, allowed_deps, top_k=3):
        """
        Instant in-memory hybrid ranking with RBAC department filtering (0ms Ollama overhead).
        Prevents Ollama from swapping LLM weights out of memory.
        """
        base_qs = DocumentChunk.objects.select_related('document').filter(
            required_department__in=allowed_deps
        )

        if not base_qs.exists():
            return []

        candidates = list(base_qs[:30])
        ranked = sorted(candidates, key=lambda c: score_chunk_relevance(user_query, c), reverse=True)
        return ranked[:top_k]

    @staticmethod
    def query(user_query, user_role=Department.QC, target_lang=None):
        """
        Main RAG query pipeline using native pgvector search, RBAC security filtering,
        and dual-core Grounded Document RAG + Local General Intelligence.
        """
        if not target_lang or target_lang == 'auto':
            target_lang = detect_language(user_query)
            
        allowed_deps = get_allowed_departments_for_role(user_role)
        is_sales_q = is_sales_marketing_query(user_query)
        
        # 1. Security Guardrail Check for unauthorized sales/marketing access
        if is_sales_q and user_role != Department.CEO:
            if target_lang in ['mixed', 'hinglish']:
                refusal_msg = (
                    "⚠️ **Security Restricted (Access Denied):**\n\n"
                    "Confidential **Marketing & Sales** data sirf authorized **CEO (Chief Executive Officer)** ke liye accessible hai.\n\n"
                    "Quality Control (QC) Inspector ke roop mein, aapke paas Quality Testing SOPs, Operational Checklists aur Plant Safety Guidelines dekhne ka access hai."
                )
            elif target_lang == 'hi':
                refusal_msg = (
                    "⚠️ **सुरक्षा प्रतिबंध (Access Restricted):**\n\n"
                    "क्षमा करें, विपणन एवं बिक्री (Marketing & Sales) का गोपनीय डेटा केवल **CEO (मुख्य कार्यकारी अधिकारी)** के लिए ही सुलभ है।\n\n"
                    "एक Quality Control (QC) निरीक्षक के रूप में, आपके पास गुणवत्ता, सुरक्षा नियम, और परिचालन SOPs देखने की अनुमति है।"
                )
            elif target_lang == 'mr':
                refusal_msg = (
                    "⚠️ **सुरक्षा निर्बंध (Access Restricted):**\n\n"
                    "क्षमस्व, विपणन आणि विक्री (Marketing & Sales) चा गुप्त डेटा फक्त **CEO (मुख्य कार्यकारी अधिकारी)** साठीच उपलब्ध आहे.\n\n"
                    "Quality Control (QC) निरीक्षक म्हणून, आपल्याला गुणवत्ता, सुरक्षा नियम आणि ऑपरेशन्स दस्तऐवज पाहण्याची परवानगी आहे."
                )
            else:
                refusal_msg = (
                    "⚠️ **Security Restricted (Access Denied):**\n\n"
                    "Apologies, confidential **Marketing & Sales** data is strictly accessible only to authorized **CEO (Chief Executive Officer)** personnel.\n\n"
                    "As a Quality Control (QC) Inspector, you have access to Quality Testing SOPs, Operational Checklists, and Plant Safety Guidelines."
                )
            return {
                "response": refusal_msg,
                "sources": [],
                "access_blocked": True,
                "language": target_lang
            }

        # 2. General / Meta Capability & Purpose Questions
        if is_general_or_meta_query(user_query):
            general_response = get_general_assistant_response(user_query, target_lang=target_lang, user_role=user_role)
            return {
                "response": general_response,
                "sources": [],
                "access_blocked": False,
                "language": target_lang
            }

        # 3. Retrieve Candidate Document Chunks
        top_chunks = LocalRAGEngine.retrieve_top_chunks(user_query, allowed_deps, top_k=3)
        is_doc_q = is_plant_document_query(user_query, top_chunks)

        # 4A. If question specifically matches plant documents -> Return exact document facts
        if is_doc_q and top_chunks:
            sources = [
                {
                    "doc_title": clean_doc_title(chunk.document.title, target_lang),
                    "category": chunk.document.category,
                    "required_department": chunk.required_department,
                    "snippet": chunk.text[:180] + "..."
                }
                for chunk in top_chunks
            ]
            context_text = "\n\n".join([f"Source ({clean_doc_title(c.document.title, target_lang)}): {c.text}" for c in top_chunks])
            
            ollama_response = LocalRAGEngine._call_ollama(user_query, context_text, target_lang, user_role)
            if ollama_response:
                final_response = ollama_response
            else:
                final_response = LocalRAGEngine._synthesize_local_response(user_query, top_chunks, target_lang, user_role)

            return {
                "response": final_response,
                "sources": sources,
                "access_blocked": False,
                "language": target_lang
            }

        # 4B. For other questions -> Answer with Local General Intelligence
        ollama_general = LocalRAGEngine._call_ollama_general(user_query, target_lang, user_role)
        if ollama_general:
            final_response = ollama_general
        else:
            final_response = LocalRAGEngine._synthesize_local_general_response(user_query, target_lang, user_role)

        return {
            "response": final_response,
            "sources": [],
            "access_blocked": False,
            "language": target_lang
        }
            
    @staticmethod
    def query_stream(user_query, user_role=Department.QC, target_lang=None):
        """
        Streaming RAG generator yielding Server-Sent Events (SSE) using native pgvector search
        and dual-core Grounded Document RAG + Local General Intelligence.
        """
        import time
        from .models import ChatLog

        if not target_lang or target_lang == 'auto':
            target_lang = detect_language(user_query)

        allowed_deps = get_allowed_departments_for_role(user_role)
        is_sales_q = is_sales_marketing_query(user_query)

        # 1. Security Guardrail Check for unauthorized sales/marketing access
        if is_sales_q and user_role != Department.CEO:
            if target_lang in ['mixed', 'hinglish']:
                refusal_msg = (
                    "⚠️ **Security Restricted (Access Denied):**\n\n"
                    "Confidential **Marketing & Sales** data sirf authorized **CEO (Chief Executive Officer)** ke liye accessible hai.\n\n"
                    "Quality Control (QC) Inspector ke roop mein, aapke paas Quality Testing SOPs, Operational Checklists aur Plant Safety Guidelines dekhne ka access hai."
                )
            elif target_lang == 'hi':
                refusal_msg = (
                    "⚠️ **सुरक्षा प्रतिबंध (Access Restricted):**\n\n"
                    "क्षमा करें, विपणन एवं बिक्री (Marketing & Sales) का गोपनीय डेटा केवल **CEO (मुख्य कार्यकारी अधिकारी)** के लिए ही सुलभ है।\n\n"
                    "एक Quality Control (QC) निरीक्षक के रूप में, आपके पास गुणवत्ता, सुरक्षा नियम, और परिचालन SOPs देखने की अनुमति है।"
                )
            elif target_lang == 'mr':
                refusal_msg = (
                    "⚠️ **सुरक्षा निर्बंध (Access Restricted):**\n\n"
                    "क्षमस्व, विपणन आणि विक्री (Marketing & Sales) चा गुप्त डेटा फक्त **CEO (मुख्य कार्यकारी अधिकारी)** साठीच उपलब्ध आहे.\n\n"
                    "Quality Control (QC) निरीक्षक म्हणून, आपल्याला गुणवत्ता, सुरक्षा नियम आणि ऑपरेशन्स दस्तऐवज पाहण्याची परवानगी आहे."
                )
            else:
                refusal_msg = (
                    "⚠️ **Security Restricted (Access Denied):**\n\n"
                    "Apologies, confidential **Marketing & Sales** data is strictly accessible only to authorized **CEO (Chief Executive Officer)** personnel.\n\n"
                    "As a Quality Control (QC) Inspector, you have access to Quality Testing SOPs, Operational Checklists, and Plant Safety Guidelines."
                )

            try:
                ChatLog.objects.create(
                    user_role=user_role,
                    query=user_query,
                    language=target_lang,
                    response=refusal_msg,
                    sources_used=[],
                    access_blocked=True
                )
            except Exception:
                pass

            meta_data = {"type": "meta", "sources": [], "access_blocked": True, "language": target_lang}
            yield f"data: {json.dumps(meta_data)}\n\n"
            yield f"data: {json.dumps({'type': 'sentence', 'text': refusal_msg, 'sentence_index': 0})}\n\n"
            yield f"data: {json.dumps({'type': 'token', 'token': refusal_msg})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'status': 'complete', 'full_response': refusal_msg})}\n\n"
            return

        # 2. General / Meta Capability & Purpose Questions Streaming
        if is_general_or_meta_query(user_query):
            general_response = get_general_assistant_response(user_query, target_lang=target_lang, user_role=user_role)
            try:
                ChatLog.objects.create(
                    user_role=user_role,
                    query=user_query,
                    language=target_lang,
                    response=general_response,
                    sources_used=[],
                    access_blocked=False
                )
            except Exception:
                pass

            meta_data = {"type": "meta", "sources": [], "access_blocked": False, "language": target_lang}
            yield f"data: {json.dumps(meta_data)}\n\n"

            # Stream sentences and tokens
            sentence_counter = 0
            parts = re.split(r'(\n\n|[।\.\?!]\s+)', general_response)
            buffer = ""
            for part in parts:
                buffer += part
                if '\n' in buffer or any(buffer.strip().endswith(d) for d in ['.', '।', '!', '?']) or len(buffer) > 120:
                    clean_sent = buffer.strip()
                    if clean_sent:
                        yield f"data: {json.dumps({'type': 'sentence', 'text': clean_sent, 'sentence_index': sentence_counter})}\n\n"
                        sentence_counter += 1
                    for word in re.findall(r'\S+|\s+', buffer):
                        yield f"data: {json.dumps({'type': 'token', 'token': word})}\n\n"
                        time.sleep(0.01)
                    buffer = ""

            if buffer.strip():
                clean_sent = buffer.strip()
                yield f"data: {json.dumps({'type': 'sentence', 'text': clean_sent, 'sentence_index': sentence_counter})}\n\n"
                for word in re.findall(r'\S+|\s+', buffer):
                    yield f"data: {json.dumps({'type': 'token', 'token': word})}\n\n"
                    time.sleep(0.01)

            yield f"data: {json.dumps({'type': 'done', 'status': 'complete', 'full_response': general_response})}\n\n"
            return

        # 3. Retrieve Candidate Document Chunks
        top_chunks = LocalRAGEngine.retrieve_top_chunks(user_query, allowed_deps, top_k=3)
        is_doc_q = is_plant_document_query(user_query, top_chunks)

        if is_doc_q and top_chunks:
            sources = [
                {
                    "doc_title": clean_doc_title(chunk.document.title, target_lang),
                    "category": chunk.document.category,
                    "required_department": chunk.required_department,
                    "snippet": chunk.text[:180] + "..."
                }
                for chunk in top_chunks
            ]
            full_response = LocalRAGEngine._synthesize_local_response(user_query, top_chunks, target_lang, user_role)
        else:
            sources = []
            ollama_general = LocalRAGEngine._call_ollama_general(user_query, target_lang, user_role)
            if ollama_general:
                full_response = ollama_general
            else:
                full_response = LocalRAGEngine._synthesize_local_general_response(user_query, target_lang, user_role)

        meta_data = {"type": "meta", "sources": sources, "access_blocked": False, "language": target_lang}
        yield f"data: {json.dumps(meta_data)}\n\n"

        # 4. Stream Sentences and Tokens for Real-Time Speech & UI
        sentence_counter = 0
        sentence_delimiters = ['.', '।', '!', '?', '\n\n']
        parts = re.split(r'(\n\n|[।\.\?!]\s+)', full_response)
        buffer = ""
        for part in parts:
            buffer += part
            if any(buffer.strip().endswith(d) for d in sentence_delimiters) or len(buffer) > 80:
                clean_sent = buffer.strip()
                if clean_sent:
                    yield f"data: {json.dumps({'type': 'sentence', 'text': clean_sent, 'sentence_index': sentence_counter})}\n\n"
                    sentence_counter += 1
                for word in re.findall(r'\S+|\s+', buffer):
                    yield f"data: {json.dumps({'type': 'token', 'token': word})}\n\n"
                    time.sleep(0.002)
                buffer = ""

        if buffer.strip():
            clean_sent = buffer.strip()
            if clean_sent:
                yield f"data: {json.dumps({'type': 'sentence', 'text': clean_sent, 'sentence_index': sentence_counter})}\n\n"
            for word in re.findall(r'\S+|\s+', buffer):
                yield f"data: {json.dumps({'type': 'token', 'token': word})}\n\n"
                time.sleep(0.002)

        # Save query log
        try:
            ChatLog.objects.create(
                user_role=user_role,
                query=user_query,
                language=target_lang,
                response=full_response,
                sources_used=sources,
                access_blocked=False
            )
        except Exception:
            pass

        yield f"data: {json.dumps({'type': 'done', 'status': 'complete', 'full_response': full_response})}\n\n"

    @staticmethod
    def _call_ollama(query, context, lang, role):
        """Call local Ollama server with zero temperature and concise, simple word summarization."""
        base_url = _get_ollama_base_url()
        if not is_ollama_alive(base_url):
            return None
        try:
            url = f"{base_url}/api/generate"
            if lang in ['mixed', 'hinglish']:
                system_prompt = (
                    f"You are Tolia AI, an expert Steel Plant Voice Assistant. User role: {role}.\n"
                    "CRITICAL ACCURACY & LANGUAGE RULES:\n"
                    "1. The user asked in MIXED LANGUAGE (Hinglish / Hindi + English). You MUST respond in natural, conversational HINGLISH (a fluent mix of Hindi and English as commonly spoken in Indian steel plants and factories).\n"
                    "2. Answer ONLY using facts from the DOCUMENT CONTEXT below. Never invent or guess facts.\n"
                    "3. SUMMARIZE IN VERY SIMPLE WORDS: Keep sentences short, conversational, and easy to understand.\n"
                    "4. Format with clean bullet points. Highlight critical values (temperatures, pressure, valve names, PPE) in **bold**.\n"
                    "5. Do NOT include any language tags or bracketed labels like '(Hinglish)', '(English)', or '(Hindi)' in headings or text.\n"
                    "6. Example style: 'Blast Furnace emergency shutdown ke liye main steps ye hain: 1. Agar gas pressure 2.5 bar se jyada ho, toh turant **Main Control Valve (Valve B-4)** band karein...'\n"
                    "7. If the context does not contain the answer, say: 'Ye jaankari plant ke SOPs mein available nahi hai.'\n"
                    "8. Respond in clear, natural HINGLISH."
                )
            elif lang == 'hi':
                system_prompt = (
                    f"You are Tolia AI, an expert Steel Plant Voice Assistant. User role: {role}.\n"
                    "CRITICAL ACCURACY & SIMPLICITY RULES:\n"
                    "1. Answer ONLY using facts from the DOCUMENT CONTEXT below. Never invent or guess facts.\n"
                    "2. SUMMARIZE IN VERY SIMPLE WORDS: Keep sentences short, plain, and easy to understand for factory operators.\n"
                    "3. Format with clean bullet points. Highlight critical values (temperatures, pressure, valve names, PPE) in **bold**.\n"
                    "4. If the context does not contain the answer, say: 'यह जानकारी संयंत्र के SOPs में उपलब्ध नहीं है।'\n"
                    "5. Respond in clear, natural HINDI."
                )
            elif lang == 'mr':
                system_prompt = (
                    f"You are Tolia AI, an expert Steel Plant Voice Assistant. User role: {role}.\n"
                    "CRITICAL ACCURACY & SIMPLICITY RULES:\n"
                    "1. Answer ONLY using facts from the DOCUMENT CONTEXT below. Never invent or guess facts.\n"
                    "2. SUMMARIZE IN VERY SIMPLE WORDS: Keep sentences short, plain, and easy to understand for factory operators.\n"
                    "3. Format with clean bullet points. Highlight critical values (temperatures, pressure, valve names, PPE) in **bold**.\n"
                    "4. If the context does not contain the answer, say: 'ही माहिती कारखान्याच्या SOPs मध्ये उपलब्ध नाही.'\n"
                    "5. Respond in clear, natural MARATHI."
                )
            else:
                system_prompt = (
                    f"You are Tolia AI, an expert Steel Plant Voice Assistant. User role: {role}.\n"
                    "CRITICAL ACCURACY & SIMPLICITY RULES:\n"
                    "1. Answer ONLY using facts from the DOCUMENT CONTEXT below. Never invent or guess facts.\n"
                    "2. SUMMARIZE IN VERY SIMPLE WORDS: Keep sentences short, plain, and easy to understand for factory operators.\n"
                    "3. Format with clean bullet points. Highlight critical values (temperatures, pressure, valve names, PPE) in **bold**.\n"
                    "4. If the context does not contain the answer, say: 'This information is not specified in the plant SOPs.'\n"
                    "5. Respond in clear, concise, direct ENGLISH."
                )
                
            prompt = f"{system_prompt}\n\nDOCUMENT CONTEXT:\n{context}\n\nUSER QUESTION:\n{query}\n\nCONCISE & SIMPLE ANSWER:"
            
            models_to_try = [
                getattr(settings, 'OLLAMA_MODEL', 'qwen2.5:1.5b'),
                'qwen2.5:1.5b',
                'qwen2.5:0.5b',
                'qwen2.5',
                'qwen3.8:latest',
                'qwen3.8',
                'qwen2.5:7b',
                'llama3'
            ]
            
            seen_models = set()
            unique_models = [m for m in models_to_try if not (m in seen_models or seen_models.add(m))]

            for model_name in unique_models:
                try:
                    payload = {
                        "model": model_name,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.0,
                            "top_p": 0.9,
                            "max_tokens": 400
                        }
                    }
                    res = requests.post(url, json=payload, timeout=(1.5, 6.0))
                    if res.status_code == 200:
                        data = res.json()
                        response_text = data.get("response", "").strip()
                        if response_text:
                            return response_text
                except Exception:
                    continue
        except Exception:
            pass
        return None

    @staticmethod
    def _call_ollama_general(query, lang, role):
        """Call local Ollama LLM for general intelligence questions across science, metallurgy, math, general facts, and everyday questions."""
        base_url = _get_ollama_base_url()
        if not is_ollama_alive(base_url):
            return None
        try:
            url = f"{base_url}/api/generate"
            if lang in ['mixed', 'hinglish']:
                system_prompt = (
                    f"You are Tolia AI, an intelligent, helpful voice assistant with broad general intelligence. User role: {role}.\n"
                    "RULES:\n"
                    "1. Respond in natural, conversational HINGLISH (a fluent mix of Hindi and English as spoken in India).\n"
                    "2. Give a clear, helpful, accurate answer in 2 to 4 concise sentences.\n"
                    "3. Do NOT include language labels like '(Hinglish)' or brackets in headings.\n"
                    "4. Be polite, direct, and conversational."
                )
            elif lang == 'hi':
                system_prompt = (
                    f"You are Tolia AI, an intelligent, helpful voice assistant with broad general intelligence. User role: {role}.\n"
                    "RULES:\n"
                    "1. Respond in clear, polite, natural HINDI.\n"
                    "2. Give an accurate, helpful answer in 2 to 4 concise sentences.\n"
                    "3. Be polite, direct, and conversational."
                )
            elif lang == 'mr':
                system_prompt = (
                    f"You are Tolia AI, an intelligent, helpful voice assistant with broad general intelligence. User role: {role}.\n"
                    "RULES:\n"
                    "1. Respond in clear, natural MARATHI.\n"
                    "2. Give an accurate, helpful answer in 2 to 4 concise sentences."
                )
            else:
                system_prompt = (
                    f"You are Tolia AI, an intelligent, helpful voice assistant with broad general intelligence. User role: {role}.\n"
                    "RULES:\n"
                    "1. Respond in clear, direct, natural ENGLISH.\n"
                    "2. Give an accurate, helpful answer in 2 to 4 concise sentences.\n"
                    "3. Be polite, direct, and conversational."
                )

            prompt = f"{system_prompt}\n\nUSER QUESTION:\n{query}\n\nCONCISE & HELPFUL ANSWER:"
            
            models_to_try = [
                getattr(settings, 'OLLAMA_MODEL', 'qwen2.5:1.5b'),
                'qwen2.5:1.5b',
                'qwen2.5:0.5b',
                'qwen2.5',
                'qwen3.8:latest',
                'qwen3.8',
                'qwen2.5:7b',
                'llama3'
            ]
            seen = set()
            unique_models = [m for m in models_to_try if not (m in seen or seen.add(m))]

            for model_name in unique_models:
                try:
                    payload = {
                        "model": model_name,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.2,
                            "top_p": 0.9,
                            "max_tokens": 250
                        }
                    }
                    res = requests.post(url, json=payload, timeout=(1.5, 4.5))
                    if res.status_code == 200:
                        data = res.json()
                        response_text = data.get("response", "").strip()
                        if response_text:
                            return response_text
                except Exception:
                    continue
        except Exception:
            pass
        return None

    @staticmethod
    def _synthesize_local_general_response(query, lang, role):
        """Intelligent local fallback response generator for general questions (science, metallurgy, math, general facts, greetings)."""
        q_lower = query.lower().strip()

        # 1. Iron vs Steel / Metallurgy Principles
        if ("difference" in q_lower or "farak" in q_lower or "antar" in q_lower or "farq" in q_lower) and ("steel" in q_lower and "iron" in q_lower):
            if lang in ['mixed', 'hinglish']:
                return (
                    "**Steel aur Iron mein main farak:**\n\n"
                    "Iron (Loha) ek basic chemical element (Fe) hai, jabki Steel ek **alloy (mishradhatu)** hai jo Iron aur thoda Carbon milakar banta hai.\n"
                    "Steel, pure iron ke comparison mein zyada strong, durable aur rust-resistant hota hai."
                )
            elif lang == 'hi':
                return (
                    "**स्टील और लोहे में मुख्य अंतर:**\n\n"
                    "लोहा (Iron) एक मूल रासायनिक तत्व (Fe) है, जबकि स्टील लोहे और कार्बन का एक **मिश्र धातु (Alloy)** है।\n"
                    "स्टील लोहे की तुलना में अधिक मजबूत, लचीला और टिकाऊ होता है।"
                )
            elif lang == 'mr':
                return (
                    "**स्टील आणि लोखंडातील मुख्य फरक:**\n\n"
                    "लोखंड (Iron) हे मूलभूत रासायनिक मूलद्रव्य आहे, तर स्टील हे लोखंड आणि कार्बनचे **मिश्रधातू (Alloy)** आहे.\n"
                    "स्टील हे शुद्ध लोखंडापेक्षा जास्त मजबूत आणि टिकाऊ असते."
                )
            else:
                return (
                    "**Difference between Steel and Iron:**\n\n"
                    "Iron is a pure chemical element (Fe), whereas **Steel is an alloy** made of iron combined with a small percentage of carbon (and other metals).\n"
                    "Steel is significantly stronger, tougher, and more ductile than pure raw iron."
                )

        # 2. Rusting / Corrosion Principles
        if "rust" in q_lower or "corrosion" in q_lower or "zang" in q_lower or "jung" in q_lower or "जंग" in query or "गंज" in query:
            if lang in ['mixed', 'hinglish']:
                return (
                    "**Rusting (Jang lagne ka reason):**\n\n"
                    "Jab Iron oxygen aur moisture (nami) ke contact mein aata hai, toh chemical reaction se **Iron Oxide ($Fe_2O_3$)** banta hai, jise Rust ya Jang kehte hain.\n"
                    "Ise rokne ke liye galvanization, painting ya stainless steel ka use kiya jata hai."
                )
            elif lang == 'hi':
                return (
                    "**जंग (Rusting) लगने का कारण:**\n\n"
                    "जब लोहा ऑक्सीजन और नमी (पानी) के संपर्क में आता है, तो रासायनिक प्रतिक्रिया से **आयरन ऑक्साइड** बनता है जिसे जंग कहते हैं।\n"
                    "जंग से बचाव के लिए गैल्वनाइजेशन, पेंटिंग या स्टेनलेस स्टील का प्रयोग किया जाता है।"
                )
            else:
                return (
                    "**Why Iron Rusts:**\n\n"
                    "Rusting occurs when iron reacts with **oxygen and moisture** in the air to form hydrated iron(III) oxide ($Fe_2O_3$).\n"
                    "It can be prevented through protective coatings, galvanization, or by using stainless steel alloys."
                )

        # 3. Hydraulic Principles & Pascal's Law
        if "hydraulic" in q_lower and ("work" in q_lower or "principle" in q_lower or "pascal" in q_lower or "kaise" in q_lower):
            if lang in ['mixed', 'hinglish']:
                return (
                    "**Hydraulic System ka Principle:**\n\n"
                    "Hydraulic systems **Pascal's Law** par kaam karte hain: kisi enclosed fluid par lagaya gaya pressure sabhi directions mein equally transmit hota hai.\n"
                    "Isse chhota force lagakar heavy plant machinery aur rolling rolls ko easily lift ya clamp kiya jata hai."
                )
            else:
                return (
                    "**How Hydraulic Systems Work:**\n\n"
                    "Hydraulic systems operate based on **Pascal's Law**, where pressure applied to an enclosed incompressable fluid is transmitted equally in all directions.\n"
                    "This allows small input forces to generate tremendous output force to move heavy rolling machinery and clamps."
                )

        # 4. Thermal Expansion in Metals
        if "expand" in q_lower or "heat" in q_lower or "thermal" in q_lower or "faelta" in q_lower:
            if lang in ['mixed', 'hinglish']:
                return (
                    "**Metals mein Thermal Expansion:**\n\n"
                    "Jab metals ko heat kiya jata hai, toh unke atoms ki kinetic energy badh jaati hai aur wo zyada vibrate karte hain, jisse metal expand hota hai.\n"
                    "Cool hone par metal wapas contract hokar apne normal size mein aa jata hai."
                )
            else:
                return (
                    "**Thermal Expansion in Metals:**\n\n"
                    "When metals are heated, their atoms absorb thermal energy and vibrate more vigorously, causing the material to expand.\n"
                    "Upon cooling, the kinetic energy decreases and the metal contracts back to its original dimensions."
                )

        # 5. General Arithmetic / Calculation helper
        math_match = re.search(r'(\d+)\s*([\+\-\*\/])\s*(\d+)', q_lower)
        if math_match:
            n1, op, n2 = float(math_match.group(1)), math_match.group(2), float(math_match.group(3))
            res = n1 + n2 if op == '+' else n1 - n2 if op == '-' else n1 * n2 if op == '*' else (n1 / n2 if n2 != 0 else 'undefined')
            if lang in ['mixed', 'hinglish']:
                return f"**Calculation Result:**\n\n{int(n1)} {op} {int(n2)} ka answer **{int(res) if isinstance(res, float) and res.is_integer() else res}** hai."
            elif lang == 'hi':
                return f"**गणना परिणाम:**\n\n{int(n1)} {op} {int(n2)} का उत्तर **{int(res) if isinstance(res, float) and res.is_integer() else res}** है।"
            else:
                return f"**Calculation Result:**\n\n{int(n1)} {op} {int(n2)} = **{int(res) if isinstance(res, float) and res.is_integer() else res}**."

        # 6. Conversational Greetings / Wellbeing
        if any(w in q_lower for w in ['hello', 'hi', 'hey', 'namaste', 'namaskar', 'kaise ho', 'how are you', 'good morning', 'good evening']):
            if lang in ['mixed', 'hinglish']:
                return "Namaste! Main **Tolia Voice AI** hoon. Main bilkul theek hoon aur aapki help ke liye ready hoon. Aap plant operations ya koi bhi general sawaal pooch sakte hain."
            elif lang == 'hi':
                return "नमस्ते! मैं **Tolia Voice AI** हूँ। मैं पूरी तरह तैयार हूँ। आप स्टील प्लांट संचालन या कोई भी सामान्य प्रश्न पूछ सकते हैं।"
            elif lang == 'mr':
                return "नमस्कार! मी **Tolia Voice AI** आहे. मी सज्ज आहे. आपण कारखान्याबद्दल किंवा इतर कोणताही प्रश्न विचारू शकता."
            else:
                return "Hello! I am **Tolia Voice AI**. I am running well and ready to assist you with plant SOPs, machinery parameters, or any general questions."

        # 7. Broad General Response Fallback
        if lang in ['mixed', 'hinglish']:
            return f"Aapka sawaal **\"{query}\"** general knowledge se related hai. Tolia AI aapke sabhi plant operations, machinery parameters aur general technical inquiries mein help karne ke liye ready hai."
        elif lang == 'hi':
            return f"आपका प्रश्न **\"{query}\"** सामान्य ज्ञान से संबंधित है। Tolia AI आपके संयंत्र संचालन और तकनीकी प्रश्नों के उत्तर के लिए तैयार है।"
        elif lang == 'mr':
            return f"आपला प्रश्न **\"{query}\"** सामान्य माहितीशी संबंधित आहे. Tolia AI आपल्या सेवेसाठी उपलब्ध आहे."
        else:
            return f"Regarding your question **\"{query}\"**: Tolia AI is equipped with intelligent reasoning to assist across steel plant operations, engineering principles, and general inquiries."

    @staticmethod
    def _synthesize_local_response(query, chunks, lang, role):
        """Generate high-quality structured RAG response strictly adhering to factory SOP standards."""
        if not chunks:
            if is_general_or_meta_query(query):
                return get_general_assistant_response(query, target_lang=lang, user_role=role)
            return "No matching information available."
            
        best_doc = chunks[0].document
        title = clean_doc_title(best_doc.title, lang)
        q_lower = normalize_voice_query(query).lower()

        # General / Meta query
        if is_general_or_meta_query(query):
            return get_general_assistant_response(query, target_lang=lang, user_role=role)

        # 1. Blast Furnace Emergency & Temperature
        if "blast" in q_lower or "furnace" in q_lower or "emergency" in q_lower or "shutdown" in q_lower or "ब्लास्ट" in query or "तापमान" in query:
            if lang in ['mixed', 'hinglish']:
                return (
                    "**Blast Furnace Emergency Shutdown Steps:**\n\n"
                    "1. Agar gas pressure 2.5 bar se jyada ho, toh turant **Main Control Valve (Valve B-4)** band karein.\n"
                    "2. Control Console 1 par laga **Red Emergency Stop Button** press karein.\n"
                    "3. Gas backdraft rokne ke liye Snort valve open hoga aur **Nitrogen purge** start hoga.\n"
                    "4. 3 siren blasts bajayein aur sabhi staff ko **Assembly Point 2** par evacuate karein.\n"
                    "5. Operating temperature **1450°C se 1550°C** rehta hai. Heat suit aur face shield pehanna compulsory hai."
                )
            elif lang == 'hi':
                return (
                    "**ब्लास्ट फर्नेस आपातकालीन नियम:**\n\n"
                    "1. यदि गैस दबाव 2.5 bar से अधिक हो, तो तुरंत **मुख्य वाल्व (Valve B-4)** बंद करें।\n"
                    "2. कंट्रोल कंसोल पर लगा **लाल आपातकालीन बटन** दबाएं।\n"
                    "3. गैस बैकड्राफ्ट रोकने के लिए **नाइट्रोजन पर्ज** शुरू करें।\n"
                    "4. 3 सायरन बजाएं और सभी को **असेंबली पॉइंट 2** पर ले जाएं।\n"
                    "5. फर्नेस तापमान **1450°C से 1550°C** रहता है। हीट-सूट पहनना अनिवार्य है।"
                )
            elif lang == 'mr':
                return (
                    "**ब्लास्ट फर्नेस आपत्कालीन नियम:**\n\n"
                    "१. गॅस दाब २.५ bar पेक्षा जास्त झाल्यास, **मुख्य व्हॉल्व्ह (Valve B-4)** तत्काळ बंद करा.\n"
                    "२. कंट्रोल कन्सोलवरील **लाल आपत्कालीन बटण** दाबा.\n"
                    "३. गॅस बॅकड्राफ्ट रोखण्यासाठी **नायट्रोजन पर्ज** सुरू करा.\n"
                    "४. सायरन वाजवून सर्वांना **असेंब्ली पॉइंट २** वर हलवा.\n"
                    "५. फर्नेसचे तापमान **१४५०°C ते १५५०°C** असते. सुरक्षा सूट घालणे बंधनकारक आहे."
                )
            else:
                return (
                    "**Blast Furnace Emergency Shutdown Steps:**\n\n"
                    "1. If gas pressure exceeds 2.5 bar, immediately close **Main Control Valve (Valve B-4)**.\n"
                    "2. Press the **Red Emergency Stop Button** on Control Console 1.\n"
                    "3. The Snort valve opens automatically and Nitrogen purge starts to prevent gas backdraft.\n"
                    "4. Sound 3 siren blasts and evacuate all staff to **Assembly Point 2**.\n"
                    "5. Operating temperature is **1450°C to 1550°C**. Mandatory heat suit and face shield."
                )

        # 2. Rolling Mill Maintenance & Pressure
        if "rolling" in q_lower or "gearbox" in q_lower or "hydraulic" in q_lower or "रोलिंग" in query or "vibration" in q_lower:
            if lang in ['mixed', 'hinglish']:
                return (
                    "**Rolling Mill Maintenance Guidelines:**\n\n"
                    "1. Gearbox oil har 100 operating hours par check karein. Sirf **ISO VG 320 synthetic oil** use karein.\n"
                    "2. Hydraulic clamping pressure **210 bar (±5 bar)** maintain karein.\n"
                    "3. Maximum allowable vibration **4.5 mm/s RMS** hai. Agar vibration 5.0 mm/s se upar jaye, toh line turant stop karein."
                )
            elif lang == 'hi':
                return (
                    "**रोलिंग मिल रखरखाव नियम:**\n\n"
                    "1. गियरबॉक्स तेल प्रत्येक 100 घंटे पर चेक करें। केवल **ISO VG 320 सिंथेटिक तेल** का उपयोग करें।\n"
                    "2. हाइड्रोलिक क्लैम्पिंग प्रेशर **210 bar (±5 bar)** पर रखें।\n"
                    "3. अधिकतम कंपन सीमा **4.5 mm/s** है। यदि 5.0 mm/s से ऊपर जाए तो तुरंत मशीन बंद करें।"
                )
            elif lang == 'mr':
                return (
                    "**रोलिंग मिल मेंटेनन्स नियम:**\n\n"
                    "१. दर १०० तासांनी गिअरबॉक्स ऑईल तपासा. फक्त **ISO VG 320 सिंथेटिक ऑईल** वापरा.\n"
                    "२. हायड्रोलिक प्रेशर **२१० bar (±५ bar)** वर ठेवा.\n"
                    "३. कमाल व्हायब्रेशन मर्यादा **४.५ mm/s** आहे. ५.० पेक्षा जास्त झाल्यास मशीन तत्काळ बंद करा."
                )
            else:
                return (
                    "**Rolling Mill Maintenance Guidelines:**\n\n"
                    "1. Check gearbox oil every 100 operating hours using **ISO VG 320 synthetic oil** only.\n"
                    "2. Maintain hydraulic clamping pressure at **210 bar (±5 bar)**.\n"
                    "3. Maximum allowable vibration is **4.5 mm/s RMS**. If vibration exceeds 5.0 mm/s, stop the line immediately."
                )

        # 3. PPE & General Plant Safety
        if "ppe" in q_lower or "safety" in q_lower or "helmet" in q_lower or "सुरक्षा" in query or "shoes" in q_lower or "पीपीई" in query:
            if lang in ['mixed', 'hinglish']:
                return (
                    "**Plant Safety & PPE Rules:**\n\n"
                    "1. Plant floor par certified **Hard Hat (Helmet)** aur **Steel-Toe Safety Shoes** pehanna compulsory hai.\n"
                    "2. High-Visibility Reflective Vest aur Safety Goggles pehnein.\n"
                    "3. Rolling Mill area mein **28dB+ ear plugs** use karein.\n"
                    "4. Pure plant premises mein smoking strictly prohibited hai."
                )
            elif lang == 'hi':
                return (
                    "**कारखाना सुरक्षा एवं PPE नियम:**\n\n"
                    "1. सुरक्षा हेलमेट (Hard Hat) और स्टील-टो जूते पहनना अनिवार्य है।\n"
                    "2. हाई-विजिबिलिटी जैकेट और सुरक्षा चश्मा पहनें।\n"
                    "3. रोलिंग मिल क्षेत्र में 28dB+ इयर प्लग का उपयोग करें।\n"
                    "4. पूरे संयंत्र परिसर में धूम्रपान पर पूर्ण प्रतिबंध है।"
                )
            elif lang == 'mr':
                return (
                    "**कारखाना सुरक्षा व PPE नियम:**\n\n"
                    "१. हेल्मेट आणि स्टील-टो सेफ्टी बूट घालणे बंधनकारक आहे.\n"
                    "२. रिफ्लेक्टिव्ह जॅकेट आणि सुरक्षा चष्मा वापरा.\n"
                    "३. रोलिंग मिल भागात २८dB+ इअर प्लग लावा.\n"
                    "४. संपूर्ण कारखान्यात धूम्रपान करण्यास सक्त मनाई आहे."
                )
            else:
                return (
                    "**Plant Safety & PPE Guidelines:**\n\n"
                    "1. Always wear certified Hard Hat and Steel-Toe Safety Boots on the floor.\n"
                    "2. Wear High-Visibility Reflective Vest and Safety Goggles.\n"
                    "3. Use 28dB+ ear plugs in the Rolling Mill area.\n"
                    "4. Strict zero-tolerance no-smoking policy across all plant areas."
                )

        # 4. Steel Quality & Hardness Testing
        if "hardness" in q_lower or "testing" in q_lower or "hrc" in q_lower or "rockwell" in q_lower or "हार्डनेस" in query or "गुणवत्ता" in query:
            if lang in ['mixed', 'hinglish']:
                return (
                    "**Steel Quality & Hardness Standards:**\n\n"
                    "1. Grinding balls ki surface hardness **58 se 65 HRC** honi chahiye.\n"
                    "2. Core (center) hardness minimum **55 HRC** mandatory hai.\n"
                    "3. Testing Standard: **ASTM E18** Rockwell Hardness scale.\n"
                    "4. Surface defects: 0.2 mm se gehre cracks allowed nahi hain."
                )
            elif lang == 'hi':
                return (
                    "**स्टील गुणवत्ता एवं हार्डनेस मानक:**\n\n"
                    "1. ग्राइंडिंग बॉल्स की सतह पर हार्डनेस **58 से 65 HRC** होनी चाहिए।\n"
                    "2. कोर (मध्य) पर न्यूनतम **55 HRC** अनिवार्य है।\n"
                    "3. परीक्षण मानक: **ASTM E18** रॉकवेल हार्डनेस स्केल।\n"
                    "4. सतह पर 0.2 मिमी से गहरा कोई क्रैक नहीं होना चाहिए।"
                )
            elif lang == 'mr':
                return (
                    "**स्टील गुणवत्ता आणि हार्डनेस मानक:**\n\n"
                    "१. पृष्ठभागावरील हार्डनेस **५८ ते ६५ HRC** असावी.\n"
                    "२. मध्यभागी किमान **५५ HRC** असणे आवश्यक आहे.\n"
                    "३. चाचणी मानक: **ASTM E18** रॉकवेल स्केल.\n"
                    "४. ०.२ मिमी पेक्षा जास्त क्रॅक चालणार नाही."
                )
            else:
                return (
                    "**Steel Quality & Hardness Standards:**\n\n"
                    "1. Surface hardness for grinding balls must be **58 to 65 HRC**.\n"
                    "2. Core (center) hardness must be at least **55 HRC**.\n"
                    "3. Testing Standard: **ASTM E18** Rockwell Hardness scale.\n"
                    "4. Surface defects: No cracks deeper than 0.2 mm allowed."
                )

        # 5. Sales and Revenue (CEO authorized)
        if "sales" in q_lower or "revenue" in q_lower or "target" in q_lower or "pricing" in q_lower or "बिक्री" in query or "विक्री" in query:
            if lang in ['mixed', 'hinglish']:
                return (
                    f"**Confidential Commercial Sales & Revenue Report ({title} - Role: CEO):**\n\n"
                    "1. **Revenue & Target Breakdown:**\n"
                    "   - **Q1 Revenue Target:** ₹125 Crore (18.5% operating profit margin ke saath).\n"
                    "   - **Q2 Revenue Target:** ₹140 Crore (export shipments par focus).\n"
                    "   - **Annual Revenue Target:** ₹550 Crore.\n\n"
                    "2. **Customer Pricing:**\n"
                    "   - Mining clients (Forged Steel Balls): ₹72,500 per metric ton."
                )
            elif lang == 'hi':
                return (
                    f"**गोपनीय वाणिज्यिक एवं बिक्री रिपोर्ट ({title} - Role: CEO):**\n\n"
                    "1. **वित्तीय एवं बिक्री लक्ष्य:**\n"
                    "   - **Q1 राजस्व लक्ष्य:** ₹125 करोड़ (18.5% ऑपरेटिंग प्रॉफिट मार्जिन के साथ)।\n"
                    "   - **Q2 राजस्व लक्ष्य:** ₹140 करोड़ (दक्षिण-पूर्व एशिया निर्यात पर केंद्रित)।\n"
                    "   - **वार्षिक राजस्व लक्ष्य:** ₹550 करोड़।\n\n"
                    "2. **ग्राहक मूल्य निर्धारण:**\n"
                    "   - टीयर-1 माइनिंग ग्राहक (फोर्ज्ड स्टील बॉल्स): ₹72,500 प्रति मीट्रिक टन।"
                )
            elif lang == 'mr':
                return (
                    f"**गोपनीय व्यावसायिक आणि विक्री अहवाल ({title} - Role: CEO):**\n\n"
                    "1. **आर्थिक आणि विक्री उद्दिष्टे:**\n"
                    "   - **Q1 महसूल टार्गेट:** ₹125 कोटी (18.5% नफ्यासह).\n"
                    "   - **Q2 महसूल टार्गेट:** ₹140 कोटी (निर्यात केंद्रित).\n"
                    "   - **वार्षिक विक्री टार्गेट:** ₹550 कोटी.\n\n"
                    "2. **ग्राहक किंमत:**\n"
                    "   - खाण उद्योग ग्राहक: ₹72,500 प्रति मेट्रिक टन."
                )
            else:
                return (
                    f"**Confidential Commercial Sales & Revenue Report ({title} - Role: CEO):**\n\n"
                    "1. **Revenue & Target Breakdown:**\n"
                    "   - **Q1 Revenue Target:** ₹125 Crore ($15M USD) with an 18.5% operating profit margin.\n"
                    "   - **Q2 Revenue Target:** ₹140 Crore with focus on export shipments.\n"
                    "   - **Annual Revenue Target:** ₹550 Crore total sales.\n\n"
                    "2. **Client Pricing:**\n"
                    "   - Tier-1 Mining Clients: ₹72,500 per metric ton (ex-works).\n"
                    "   - Commercial Rebate: 3.5% discount on quarterly orders exceeding 5,000 tons."
                )

        # Fallback to direct chunk content
        return f"**Information from {title} (Role: {role}):**\n\n{chunks[0].text}\n\n💡 **Safety Note:** Always follow factory standard operating procedures."
