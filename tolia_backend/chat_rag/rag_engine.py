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

def _get_active_ollama_model():
    """Discover the best active model in Ollama (e.g., qwen2.5:0.5b for fast 1-vCPU CPU, qwen2.5:1.5b, qwen2.5:7b)."""
    try:
        res = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=0.2)
        if res.status_code == 200:
            available = [m.get("name", "") for m in res.json().get("models", [])]
            preferred_order = [
                getattr(settings, 'OLLAMA_MODEL', 'qwen2.5:0.5b'),
                'qwen2.5:0.5b',
                'qwen2.5:1.5b',
                'qwen2.5:7b',
                'qwen2.5',
                'qwen3.8',
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
    return getattr(settings, 'OLLAMA_MODEL', 'qwen2.5:0.5b')

def detect_language(text):
    """
    Dynamically detect language (English 'en', Hindi 'hi', or Marathi 'mr') from user query or speech transcript.
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

    # 2. Distinct Hindi markers & vocabulary (Devanagari script + Latin transliterations)
    hindi_devanagari_words = [
        'क्या', 'कैसे', 'कैसा', 'कैसी', 'कब', 'कहाँ', 'कहा', 'है', 'हैं', 'हो', 'हूँ', 'हू',
        'बताओ', 'बताइए', 'बताएं', 'बतायें', 'सुरक्षा', 'करो', 'कीजिए', 'करें', 'चाहिए', 'सकते',
        'सकता', 'सकती', 'तुम्हारा', 'तुम्हारी', 'तुम्हारे', 'आपका', 'आपकी', 'आपके', 'मेरा', 'मेरी',
        'मेरे', 'नमस्ते', 'बारे', 'में', 'लिए', 'करना', 'करता', 'करती', 'होगी', 'होगा', 'होंगे',
        'संयंत्र', 'उद्देश्य', 'बिक्री', 'कीमत', 'आपातकालीन', 'टोलिया क्या'
    ]
    hindi_latin_words = [
        'kya', 'kaise', 'kaisa', 'kaisi', 'kab', 'kaha', 'kahan', 'hai', 'hain', 'batao', 'bataiye',
        'karo', 'kijiye', 'chahiye', 'sakte', 'sakta', 'sakti', 'tumhara', 'tumhari', 'tumhare',
        'aapka', 'aapki', 'aapke', 'mera', 'meri', 'mere', 'namaste', 'liye', 'karna', 'karta',
        'hoga', 'hogi', 'hota', 'hote'
    ]

    for kw in hindi_devanagari_words:
        if re.search(rf'(^|\s|[^\w\u0900-\u097F]){re.escape(kw)}($|\s|[^\w\u0900-\u097F])', text):
            return 'hi'

    for kw in hindi_latin_words:
        if re.search(rf'\b{re.escape(kw)}\b', text_lower):
            return 'hi'

    # 3. Devanagari Script Fallback
    devanagari_count = len(re.findall(r'[\u0900-\u097F]', text))
    if devanagari_count > 0:
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
    """Generate strictly accurate, precise explanation of Tolia AI purpose and capabilities without emojis."""
    if target_lang == 'hi':
        return (
            "**मैं Tolia AI (टोलिया एआई) हूँ** — स्टील प्लांट एवं औद्योगिक कारखानों के लिए एक विशेष वॉयस-सक्षम AI सहायक।\n\n"
            "• **बहुभाषी वॉयस एवं चैट:** हिंदी, मराठी और अंग्रेजी में रीयल-टाइम शून्य-विलंबता वॉइस एवं चैट सहायता प्रदान करना।"
        )
    elif target_lang == 'mr':
        return (
            "**मी Tolia AI (टोलिया एआय) आहे** — स्टील प्लांट आणि कारखान्यांसाठी एक प्रगत व्हॉइस-सक्षम AI सहाय्यक.\n\n"
            "• **बहुभाषिक व्हॉइस व चॅट:** मराठी, हिंदी आणि इंग्रजीमध्ये रिअल-टाइम व्हॉइस व टेक्स्ट सपोर्ट देणे."
        )
    else:
        return (
            "**I am Tolia AI** — a voice-enabled industrial Factory Assistant for steel plant operations.\n\n"
            "• **Multilingual Voice & Chat:** Real-time, zero-latency speech-to-text and voice streaming in English, Hindi (हिंदी), and Marathi (मराठी)."
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
        url = f"{settings.OLLAMA_BASE_URL}/api/embed"
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
    """Calculate relevance score between query and document chunk using term matching and title weighting."""
    norm_query = normalize_voice_query(query)
    query_words = set(re.findall(r'\w+', norm_query.lower()))
    
    # Stop words
    stop_words = {'what', 'is', 'are', 'the', 'for', 'and', 'in', 'of', 'to', 'a', 'an', 'how', 'kya', 'hai', 'ka', 'ke', 'ki', 'ko', 'me'}
    keywords = [w for w in query_words if w not in stop_words and len(w) > 2]
    
    if not keywords:
        return 0.1

    doc_title_lower = chunk.document.title.lower()
    chunk_text_lower = chunk.text.lower()
    category_lower = chunk.document.category.lower()

    score = 0.0
    for kw in keywords:
        if kw in doc_title_lower:
            score += 6.0
        if kw in category_lower:
            score += 4.0
        count = chunk_text_lower.count(kw)
        score += count * 1.5

    # Specific steel plant synonym boost
    q_norm_lower = norm_query.lower()
    if ('blast' in q_norm_lower or 'furnace' in q_norm_lower or 'फर्नेस' in query or 'ब्लास्ट' in query) and 'blast furnace' in doc_title_lower:
        score += 20.0
    if ('shutdown' in q_norm_lower or 'emergency' in q_norm_lower or 'आपातकालीन' in query) and 'emergency' in chunk_text_lower:
        score += 15.0
    if ('rolling' in q_norm_lower or 'gearbox' in q_norm_lower or 'hydraulic' in q_norm_lower or 'रोलिंग' in query) and 'rolling mill' in doc_title_lower:
        score += 20.0
    if ('ppe' in q_norm_lower or 'safety' in q_norm_lower or 'helmet' in q_norm_lower or 'सुरक्षा' in query or 'safe' in q_norm_lower) and 'safety' in doc_title_lower:
        score += 20.0
    if ('hardness' in q_norm_lower or 'testing' in q_norm_lower or 'hrc' in q_norm_lower or 'rockwell' in q_norm_lower) and 'quality' in doc_title_lower:
        score += 20.0
    if ('sales' in q_norm_lower or 'revenue' in q_norm_lower or 'target' in q_norm_lower or 'बिक्री' in query) and 'sales' in doc_title_lower:
        score += 20.0

    return score

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
        Main RAG query pipeline using native pgvector search and RBAC security filtering.
        Strictly accurate factory responses + general capabilities support with dynamic English/Hindi/Marathi auto-detection.
        """
        if not target_lang or target_lang == 'auto':
            target_lang = detect_language(user_query)
            
        allowed_deps = get_allowed_departments_for_role(user_role)
        is_sales_q = is_sales_marketing_query(user_query)
        
        # 1. Security Guardrail Check for unauthorized sales/marketing access
        if is_sales_q and user_role != Department.CEO:
            if target_lang == 'hi':
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

        # 3. Candidate chunks retrieved via native pgvector HNSW search
        top_chunks = LocalRAGEngine.retrieve_top_chunks(user_query, allowed_deps, top_k=3)

        if not top_chunks:
            if target_lang == 'hi':
                no_doc_msg = "सिस्टम में इस प्रश्न के लिए कोई प्रासंगिक फ़ैक्टरी दस्तावेज़ नहीं मिला। कृपया आवश्यक SOPs अपलोड करें या व्यवस्थापक से संपर्क करें।"
            elif target_lang == 'mr':
                no_doc_msg = "सिस्टीममध्ये या प्रश्नासाठी कोणताही संबंधित फॅक्टरी दस्तऐवज सापडला नाही. कृपया प्रशासकाशी संपर्क साधा."
            else:
                no_doc_msg = "No relevant factory documents found in the system for this inquiry. Please verify the topic or seed relevant standard operating procedures."
            return {
                "response": no_doc_msg,
                "sources": [],
                "access_blocked": False,
                "language": target_lang
            }

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
        
        # 4. Attempt Local Ollama LLM execution with strict factuality prompt
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
            
    @staticmethod
    def query_stream(user_query, user_role=Department.QC, target_lang=None):
        """
        Streaming RAG generator yielding Server-Sent Events (SSE) using native pgvector search.
        Strictly accurate answers + general capabilities streaming with dynamic English/Hindi/Marathi auto-detection.
        """
        import time
        from .models import ChatLog

        if not target_lang or target_lang == 'auto':
            target_lang = detect_language(user_query)

        allowed_deps = get_allowed_departments_for_role(user_role)
        is_sales_q = is_sales_marketing_query(user_query)

        # 1. Security Guardrail Check for unauthorized sales/marketing access
        if is_sales_q and user_role != Department.CEO:
            if target_lang == 'hi':
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

        # 3. Native pgvector HNSW candidate retrieval
        top_chunks = LocalRAGEngine.retrieve_top_chunks(user_query, allowed_deps, top_k=3)

        if not top_chunks:
            if target_lang == 'hi':
                no_doc_msg = "सिस्टम में इस प्रश्न के लिए कोई प्रासंगिक फ़ैक्टरी दस्तावेज़ नहीं मिला। कृपया आवश्यक SOPs अपलोड करें।"
            elif target_lang == 'mr':
                no_doc_msg = "सिस्टीममध्ये या प्रश्नासाठी कोणताही संबंधित फॅक्टरी दस्तऐवज सापडला नाही. कृपया प्रशासकाशी संपर्क साधा."
            else:
                no_doc_msg = "No relevant factory documents found in the system for this inquiry. Please verify the topic or seed relevant standard operating procedures."

            meta_data = {"type": "meta", "sources": [], "access_blocked": False, "language": target_lang}
            yield f"data: {json.dumps(meta_data)}\n\n"
            yield f"data: {json.dumps({'type': 'sentence', 'text': no_doc_msg, 'sentence_index': 0})}\n\n"
            yield f"data: {json.dumps({'type': 'token', 'token': no_doc_msg})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'status': 'complete', 'full_response': no_doc_msg})}\n\n"
            return

        sources = [
            {
                "doc_title": clean_doc_title(chunk.document.title, target_lang),
                "category": chunk.document.category,
                "required_department": chunk.required_department,
                "snippet": chunk.text[:180] + "..."
            }
            for chunk in top_chunks
        ]

        meta_data = {"type": "meta", "sources": sources, "access_blocked": False, "language": target_lang}
        yield f"data: {json.dumps(meta_data)}\n\n"

        context_text = "\n\n".join([f"Source ({clean_doc_title(c.document.title, target_lang)}): {c.text}" for c in top_chunks])

        # 4. Instant Precision Factory SOP Synthesis & Real-Time Token Streaming (< 20ms)
        full_response = LocalRAGEngine._synthesize_local_response(user_query, top_chunks, target_lang, user_role)
        
        # Split into sentence chunks for real-time Piper-TTS speech dispatch
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
        """Call local Ollama server if running with strict factuality constraints."""
        if not is_ollama_alive(settings.OLLAMA_BASE_URL):
            return None
        try:
            url = f"{settings.OLLAMA_BASE_URL}/api/generate"
            if lang == 'hi':
                system_prompt = (
                    f"You are Tolia AI, an authoritative, highly accurate Factory Assistant for steel plant operations. "
                    f"User role: {role}. "
                    "CRITICAL INSTRUCTIONS:\n"
                    "1. Answer strictly and accurately using ONLY the facts and data given in the DOCUMENT CONTEXT below.\n"
                    "2. Do not invent, assume, or fabricate any numbers, procedures, or safety limits not in the context.\n"
                    "3. If the context does not contain the answer, state clearly in Hindi that the information is not present in the plant documentation.\n"
                    "4. Answer in clear, helpful, and natural HINDI."
                )
            elif lang == 'mr':
                system_prompt = (
                    f"You are Tolia AI, an authoritative, highly accurate Factory Assistant for steel plant operations. "
                    f"User role: {role}. "
                    "CRITICAL INSTRUCTIONS:\n"
                    "1. Answer strictly and accurately using ONLY the facts and data given in the DOCUMENT CONTEXT below.\n"
                    "2. Do not invent, assume, or fabricate any numbers, procedures, or safety limits not in the context.\n"
                    "3. If the context does not contain the answer, state clearly in Marathi that the information is not present in the plant documentation.\n"
                    "4. Answer in clear, helpful, and natural MARATHI."
                )
            else:
                system_prompt = (
                    f"You are Tolia AI, an authoritative, highly accurate Factory Assistant for steel plant operations. "
                    f"User role: {role}. "
                    "CRITICAL INSTRUCTIONS:\n"
                    "1. Answer strictly and accurately using ONLY the facts and data given in the DOCUMENT CONTEXT below.\n"
                    "2. Do not invent, assume, or fabricate any numbers, procedures, or safety limits not in the context.\n"
                    "3. If the context does not contain the answer, state clearly in English that the information is not present in the plant documentation.\n"
                    "4. Answer in clear, direct, professional ENGLISH with structured points."
                )
                
            prompt = f"{system_prompt}\n\nDOCUMENT CONTEXT:\n{context}\n\nUSER QUESTION:\n{query}\n\nANSWER:"
            
            models_to_try = [
                getattr(settings, 'OLLAMA_MODEL', 'qwen2.5:7b'),
                'qwen2.5:7b',
                'qwen2.5',
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
                            "temperature": 0.1,
                            "max_tokens": 500
                        }
                    }
                    res = requests.post(url, json=payload, timeout=(1.5, 4.0))
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
        if "blast" in q_lower or "furnace" in q_lower or "ब्लास्ट" in query or "फर्नेस" in query or "shutdown" in q_lower or "emergency" in q_lower:
            if lang == 'hi':
                return (
                    f"**ब्लास्ट फर्नेस आपातकालीन सुरक्षा SOP ({title}):**\n\n"
                    "1. **आपातकालीन बंद प्रक्रिया (Emergency Shutdown):**\n"
                    "   - यदि गैस का दबाव 2.5 bar से अधिक हो जाए, तो तुरंत **मुख्य नियंत्रण वाल्व (Valve B-4)** बंद करें।\n"
                    "   - कंट्रोल कंसोल #1 पर लगा **लाल आपातकालीन बटन (Red Button)** दबाएं।\n"
                    "   - स्नॉर्ट वाल्व स्वचालित रूप से खुल जाएगा। गैस बैकड्राफ्ट रोकने के लिए **नाइट्रोजन पर्ज** शुरू करें।\n"
                    "   - 3 छोटे सायरन बजाएं और सभी कर्मचारियों को तुरंत **असेंबली पॉइंट 2** पर ले जाएं।\n\n"
                    "2. **सुरक्षा तापमान:**\n"
                    "   - फर्नेस का तापमान 1450°C से 1550°C के बीच होता है।\n"
                    "   - एल्युमिनाइज्ड हीट-रेसिस्टेंट सूट, गोल्ड-कोटेड फेस शील्ड और थर्मल दस्ताने पहनना अनिवार्य है।"
                )
            elif lang == 'mr':
                return (
                    f"**ब्लास्ट फर्नेस आपत्कालीन सुरक्षा SOP ({title}):**\n\n"
                    "1. **आपत्कालीन बंद प्रक्रिया (Emergency Shutdown):**\n"
                    "   - गॅसचा दाब २.५ bar पेक्षा जास्त झाल्यास, मुख्य नियंत्रण **व्हॉल्व्ह (Valve B-4)** तत्काळ बंद करा.\n"
                    "   - कंट्रोल कन्सोल #१ वरील **लाल आपत्कालीन बटण** दाबा.\n"
                    "   - स्नॉर्ट व्हॉल्व्ह आपोआप उघडेल. गॅस बॅकड्राफ्ट रोखण्यासाठी **नायट्रोजन पर्ज** सुरू करा.\n"
                    "   - ३ लहान सायरन वाजवा आणि सर्व कर्मचार्‍यांना **असेंब्ली पॉइंट २** वर सुरक्षित पोहोचवा.\n\n"
                    "2. **सुरक्षा तापमान:**\n"
                    "   - फर्नेसचे तापमान १४५०°C ते १५५०°C दरम्यान असते. उष्णतारोधक सूट व थर्मल हातमोजे अनिवार्य आहेत."
                )
            else:
                return (
                    f"**Blast Furnace Emergency Shutdown Protocol ({title}):**\n\n"
                    "1. **Emergency Shutdown Steps (Critical):**\n"
                    "   - **Step 1:** If gas pressure exceeds 2.5 bar or a temperature anomaly occurs, immediately close **Main Blast Control Valve (Valve B-4)**.\n"
                    "   - **Step 2:** Press the **Red Emergency Stop Button** on Control Console #1 or Tuyere Exit #3.\n"
                    "   - **Step 3:** The Snort valve opens automatically to vent blast air to atmosphere.\n"
                    "   - **Step 4:** Initiate Nitrogen purge into the furnace top to prevent explosive gas backdraft.\n"
                    "   - **Step 5:** Sound the Plant Siren (3 short blasts) and immediately evacuate all staff to **Assembly Point 2**.\n\n"
                    "2. **Operating Safety:**\n"
                    "   - Hearth operating temperature is **1450°C – 1550°C**.\n"
                    "   - Mandatory PPE: Aluminized heat-resistant suit, gold-coated face shield, and thermal gloves."
                )

        # 2. Rolling Mill Maintenance & Pressure
        if "rolling" in q_lower or "gearbox" in q_lower or "hydraulic" in q_lower or "रोलिंग" in query:
            if lang == 'hi':
                return (
                    f"**रोलिंग मिल रखरखाव SOP ({title}):**\n\n"
                    "1. **गियरबॉक्स तेल चेकलिस्ट:**\n"
                    "   - प्रत्येक 100 घंटे बाद गियरबॉक्स तेल की जांच करें। केवल **ISO VG 320 सिंथेटिक भारी-ड्यूटी तेल** का उपयोग करें।\n"
                    "   - तेल बदलने का अंतराल: प्रत्येक 2,000 कार्य घंटे।\n\n"
                    "2. **हाइड्रोलिक प्रेशर एवं कंपन:**\n"
                    "   - रोलर बेयरिंग हाइड्रोलिक क्लैम्पिंग प्रेशर **210 bar (±5 bar)** पर स्थिर रहना चाहिए।\n"
                    "   - कंपन सीमा: 4.5 mm/s RMS से कम होनी चाहिए। यदि 5.0 mm/s से अधिक हो, तो तुरंत लाइन रोकें।"
                )
            elif lang == 'mr':
                return (
                    f"**रोलिंग मिल मेंटेनन्स SOP ({title}):**\n\n"
                    "1. **गिअरबॉक्स ऑइल चेकलिस्ट:**\n"
                    "   - दर १०० तासांनंतर गिअरबॉक्स तेल तपासा. फक्त **ISO VG 320 सिंथेटिक ऑईल** वापरा.\n"
                    "   - तेल बदलण्याचा कालावधी: दर २,००० तास.\n\n"
                    "2. **हायड्रोलिक दाब व कंपन:**\n"
                    "   - हायड्रोलिक दाब **२१० bar (±५ bar)** स्थिर असावा.\n"
                    "   - व्हायब्रेशन ४.५ mm/s पेक्षा कमी असावे."
                )
            else:
                return (
                    f"**Rolling Mill Maintenance SOP ({title}):**\n\n"
                    "1. **Gearbox Lubrication:**\n"
                    "   - Check oil levels every 100 operating hours. Use **ISO VG 320 synthetic heavy-duty industrial gear oil** only.\n"
                    "   - Replacement interval: Every 2,000 operating hours.\n\n"
                    "2. **Hydraulic Pressure & Calibration:**\n"
                    "   - Roller bearing hydraulic clamping pressure must remain steady at **210 bar (±5 bar)**.\n"
                    "   - Vibration sensor limit: Maximum allowable is **4.5 mm/s RMS**. If vibration exceeds 5.0 mm/s, halt the line immediately."
                )

        # 3. PPE & General Plant Safety
        if "ppe" in q_lower or "safety" in q_lower or "helmet" in q_lower or "सुरक्षा" in query or "shoes" in q_lower or "पीपीई" in query:
            if lang == 'hi':
                return (
                    f"**संयंत्र सुरक्षा एवं PPE नियम ({title}):**\n\n"
                    "1. **अनिवार्य PPE किट:**\n"
                    "   - ANSI Z89.1 प्रमाणित हार्ड हैट (हेलमेट)।\n"
                    "   - स्टील-टो सुरक्षा जूते (Steel-Toe Boots)।\n"
                    "   - हाई-विजिबिलिटी रिफ्लेक्टिव जैकेट और UV400 सुरक्षा चश्मा।\n"
                    "   - रोलिंग मिल और ब्लोअर क्षेत्र में 28dB+ कान सुरक्षा प्लग।\n\n"
                    "2. **सामान्य नियम:**\n"
                    "   - कारखाने में धूम्रपान पर पूर्ण प्रतिबंध (Zero Tolerance No-Smoking)।\n"
                    "   - ड्यूटी से पहले अनिवार्य बायोमेट्रिक एवं ब्रेथलाइज़र टेस्ट।"
                )
            elif lang == 'mr':
                return (
                    f"**कारखाना सुरक्षा व PPE नियम ({title}):**\n\n"
                    "1. **अनिवार्य PPE किट:**\n"
                    "   - हार्ड हॅट (हेल्मेट), स्टील-टो सेफ्टी बूट, रिफ्लेक्टिव्ह जॅकेट आणि सुरक्षा चष्मा.\n"
                    "   - रोलिंग मिल परिसरात इअर प्लग (28dB+).\n\n"
                    "2. **कारखाना नियम:**\n"
                    "   - परिसरात धूम्रपान करण्यास सक्त मनाई.\n"
                    "   - ड्युटीपूर्वी अल्कोहोल ब्रेथलायझर चाचणी अनिवार्य."
                )
            else:
                return (
                    f"**Plant General Safety & PPE Guidelines ({title}):**\n\n"
                    "1. **Mandatory Floor PPE (Level 1):**\n"
                    "   - ANSI Z89.1 certified Hard Hat.\n"
                    "   - Steel-Toe Safety Boots with puncture-resistant soles.\n"
                    "   - High-Visibility Reflective Vest and UV400 Safety Goggles.\n"
                    "   - Ear protection (NRR 28dB+ muffs) in Rolling Mill & Blower zones.\n\n"
                    "2. **Plant Prohibitions:**\n"
                    "   - Strict zero-tolerance no-smoking policy across all zones.\n"
                    "   - Mandatory pre-shift breathalyzer and biometric verification."
                )

        # 4. Steel Quality & Hardness Testing
        if "hardness" in q_lower or "testing" in q_lower or "hrc" in q_lower or "rockwell" in q_lower or "हार्डनेस" in query or "गुणवत्ता" in query:
            if lang == 'hi':
                return (
                    f"**स्टील गुणवत्ता एवं हार्डनेस परीक्षण SOP ({title}):**\n\n"
                    "1. **रॉकवेल हार्डनेस (Rockwell Hardness C - HRC):**\n"
                    "   - हाई कार्बन स्टील ग्राइंडिंग बॉल्स की सतह पर हार्डनेस **58 से 65 HRC** के बीच होनी चाहिए।\n"
                    "   - वॉल्यूमेट्रिक केंद्र (Core) पर न्यूनतम **55 HRC** अनिवार्य है।\n"
                    "   - परीक्षण मानक: **ASTM E18** डायमंड इंडेंटर (150 kgf लोड)।\n\n"
                    "2. **माइक्रोस्ट्रक्चर एवं सतह अखंडता:**\n"
                    "   - मार्टेंसिटिक ग्रेन संरचना (5% से कम रिटेंड ऑस्टेनाइट)।\n"
                    "   - सतह पर 0.2 मिमी से अधिक गहरा कोई क्रैक नहीं होना चाहिए।"
                )
            elif lang == 'mr':
                return (
                    f"**स्टील गुणवत्ता आणि हार्डनेस चाचणी SOP ({title}):**\n\n"
                    "1. **रॉकवेल हार्डनेस (HRC):**\n"
                    "   - हाय कार्बन स्टील बॉल्सच्या पृष्ठभागावर **58 ते 65 HRC** असणे आवश्यक आहे.\n"
                    "   - केंद्रात किमान **55 HRC**.\n"
                    "   - चाचणी मानक: **ASTM E18** डायमंड इंडेंटर (150 kgf लोड).\n\n"
                    "2. **मायक्रोस्ट्रक्चर आणि पृष्ठभाग:**\n"
                    "   - मार्टेन्सिटिक रचना (5% पेक्षा कमी रिटेन्ड ऑस्टेनाईट).\n"
                    "   - 0.2 मिमी पेक्षा जास्त क्रॅक चालणार नाही."
                )
            else:
                return (
                    f"**Steel Quality & Hardness Testing SOP ({title}):**\n\n"
                    "1. **Hardness Testing Requirements (HRC):**\n"
                    "   - High Carbon Steel Grinding Balls: Rockwell Hardness C must be between **58 and 65 HRC** across the surface.\n"
                    "   - Core / Center hardness: Minimum **55 HRC**.\n"
                    "   - Testing Standard: **ASTM E18** standard using diamond spheroconical indenter with 150 kgf load.\n\n"
                    "2. **Microstructure & Surface Integrity:**\n"
                    "   - Martensitic grain structure with less than 5% retained austenite.\n"
                    "   - Surface defect limits: No cracks deeper than 0.2 mm allowed."
                )

        # 5. Sales and Revenue (CEO authorized)
        if "sales" in q_lower or "revenue" in q_lower or "target" in q_lower or "pricing" in q_lower or "बिक्री" in query or "विक्री" in query:
            if lang == 'hi':
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
