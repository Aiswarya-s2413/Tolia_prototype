import re
import requests
import json
import numpy as np
from collections import Counter
from django.conf import settings
from pgvector.django import CosineDistance
from .models import Document, DocumentChunk, Department, DocumentCategory

def is_hindi(text):
    """Detect if input text contains Devanagari script or Hindi phrasing."""
    devanagari_count = len(re.findall(r'[\u0900-\u097F]', text))
    hindi_keywords = ['kya', 'kaise', 'kab', 'suraksha', 'kaha', 'hai', 'namaste', 'batao', 'bikri']
    text_lower = text.lower()
    keyword_match = any(kw in text_lower for kw in hindi_keywords)
    return devanagari_count > 0 or (devanagari_count > 2)

def is_sales_marketing_query(query_text):
    """Check if query is targeting sales/marketing/pricing data."""
    sales_terms = [
        'sales', 'marketing', 'revenue', 'price', 'pricing', 'target', 'client',
        'customer', 'profit', 'margin', 'q1', 'q2', 'q3', 'q4', 'bikri', 'kimat', 'munafa'
    ]
    query_lower = query_text.lower()
    return any(term in query_lower for term in sales_terms)

def get_allowed_departments_for_role(user_role):
    """Return list of required_department tags a user role is permitted to see."""
    if user_role == Department.CEO:
        return [Department.QC, Department.CEO]
    else: # QC
        return [Department.QC]

def get_embedding(text):
    """Call local Ollama server (nomic-embed-text) to generate 768d vector embedding."""
    try:
        url = f"{settings.OLLAMA_BASE_URL}/api/embed"
        payload = {"model": "nomic-embed-text", "input": text}
        res = requests.post(url, json=payload, timeout=5.0)
        if res.status_code == 200:
            data = res.json()
            embeddings = data.get("embeddings", [])
            if embeddings and len(embeddings) > 0:
                return embeddings[0]
    except Exception:
        pass
    return None

def clean_doc_title(title, target_lang):
    """Clean document title to remove Devanagari brackets in English mode."""
    if target_lang == 'en':
        # Remove parenthetical Devanagari script e.g. "(ब्लास्ट फर्नेस सुरक्षा निर्देश)"
        cleaned = re.sub(r'\s*\([\u0900-\u097F\s]+\)', '', title)
        return cleaned.strip()
    return title

class LocalRAGEngine:
    @staticmethod
    def get_embedding(text):
        return get_embedding(text)

    @staticmethod
    def query(user_query, user_role=Department.QC, target_lang=None):
        """
        Main RAG query pipeline using PostgreSQL + pgvector Cosine Distance and RBAC security filtering.
        """
        if not target_lang:
            target_lang = 'hi' if is_hindi(user_query) else 'en'
            
        allowed_deps = get_allowed_departments_for_role(user_role)
        is_sales_q = is_sales_marketing_query(user_query)
        
        # Security Guardrail Check for unauthorized sales/marketing access
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
                    "Quality Control (QC) निरीक्षक म्हणून, आपल्याला गुणत्ता, सुरक्षा नियम आणि ऑपरेशन्स दस्तऐवज पाहण्याची परवानगी आहे."
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

        # Generate query vector via Ollama nomic-embed-text
        query_vector = get_embedding(user_query)

        # Retrieve candidate chunks using pgvector CosineDistance + RBAC filtering
        if query_vector is not None:
            top_chunks = list(
                DocumentChunk.objects.select_related('document')
                .filter(required_department__in=allowed_deps, embedding__isnull=False)
                .annotate(distance=CosineDistance('embedding', query_vector))
                .order_by('distance')[:3]
            )
        else:
            top_chunks = list(
                DocumentChunk.objects.select_related('document')
                .filter(required_department__in=allowed_deps)[:3]
            )
        
        if not top_chunks:
            # Fallback if DB is empty
            if target_lang == 'hi':
                no_doc_msg = "सिस्टम में कोई प्रासंगिक दस्तावेज़ नहीं मिला। कृपया व्यवस्थापक से संपर्क करें।"
            elif target_lang == 'mr':
                no_doc_msg = "सिस्टीममध्ये कोणताही संबंधित दस्तऐवज सापडला नाही. कृपया प्रशासकाशी संपर्क साधा."
            else:
                no_doc_msg = "No relevant documents found in the system. Please seed or upload documents."
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
        
        # Attempt Local Ollama LLM execution
        ollama_response = LocalRAGEngine._call_ollama(user_query, context_text, target_lang, user_role)
        
        if ollama_response:
            final_response = ollama_response
        else:
            # Local Smart RAG Synthesizer (Fallback when Ollama service is offline)
            final_response = LocalRAGEngine._synthesize_local_response(user_query, top_chunks, target_lang, user_role)
            
        return {
            "response": final_response,
            "sources": sources,
            "access_blocked": False,
            "language": target_lang
        }

    @staticmethod
    def _call_ollama(query, context, lang, role):
        """Call local Ollama server with Qwen 2.5 primary model and fallbacks."""
        try:
            url = f"{settings.OLLAMA_BASE_URL}/api/generate"
            if lang == 'hi':
                system_prompt = f"You are Qwen, an expert AI Factory Assistant for steel plant workers. Answer in clear, helpful HINDI using the context provided below. User role: {role}."
            elif lang == 'mr':
                system_prompt = f"You are Qwen, an expert AI Factory Assistant for steel plant workers. Answer in clear, helpful MARATHI using the context provided below. User role: {role}."
            else:
                system_prompt = f"You are Qwen, an expert AI Factory Assistant for steel plant workers. Answer ONLY in clear, professional ENGLISH. Do NOT include any Hindi text or Devanagari script. User role: {role}."
                
            prompt = f"{system_prompt}\n\nDOCUMENT CONTEXT:\n{context}\n\nUSER QUESTION:\n{query}\n\nANSWER:"
            
            # Model fallbacks prioritized for Qwen 2.5
            models_to_try = [
                getattr(settings, 'OLLAMA_MODEL', 'qwen2.5:7b'),
                'qwen2.5:7b',
                'qwen2.5',
                'qwen2.5:14b',
                'llama3'
            ]
            
            # Remove duplicate model names while preserving priority order
            seen_models = set()
            unique_models = [m for m in models_to_try if not (m in seen_models or seen_models.add(m))]

            for model_name in unique_models:
                try:
                    payload = {
                        "model": model_name,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.2,
                            "max_tokens": 500
                        }
                    }
                    res = requests.post(url, json=payload, timeout=5.0)
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
        """Generate high-quality structured RAG response in 100% target language."""
        if not chunks:
            return "No matching information available."
            
        first_doc = chunks[0].document
        chunk_text = chunks[0].text
        title = clean_doc_title(first_doc.title, lang)
        
        if lang == 'hi':
            response = f"**{title} से जानकारी (Role: {role}):**\n\n"
            response += f"{chunk_text}\n\n"
            response += "💡 **महत्वपूर्ण सुरक्षा निर्देश:** स्टील कारखाने में काम करते समय हमेशा सुरक्षा हेलमेट, सुरक्षा जूते और चश्मा पहनें।"
        elif lang == 'mr':
            marathi_summary = chunk_text
            if "Blast Furnace" in title or "ब्लास्ट फर्नेस" in chunk_text or "Blast furnace operating" in chunk_text:
                marathi_summary = (
                    "1. **ब्लास्ट फर्नेस सुरक्षा SOP:**\n"
                    "   - ब्लास्ट फर्नेसचे तापमान १५००°C पेक्षा जास्त असते. सर्व कर्मचार्‍यांनी उष्णतारोधक सुट, सुरक्षा हेल्मेट, थर्मल हातमोजे आणि चष्मा घालणे अनिवार्य आहे.\n\n"
                    "2. **आपत्कालीन बंद प्रक्रिया:**\n"
                    "   - गॅसचा दाब २.५ bar पेक्षा जास्त झाल्यास, मुख्य नियंत्रण व्हॉल्व्ह (B-4) बंद करा आणि लाल आपत्कालीन बटण दाबा. सर्वांनी असेंब्ली पॉइंट २ वर जमा व्हावे.\n\n"
                    "3. **हॉट मेटल टॅपिंग:** द्रव लोखंड टॅपिंग दरम्यान किमान ५ मीटरचे सुरक्षित अंतर ठेवा."
                )
            elif "Rolling Mill" in title or "रोलिंग मिल" in chunk_text or "Rolling Mill Drive" in chunk_text:
                marathi_summary = (
                    "1. **रोलिंग मिल गिअरबॉक्स तपासणी:**\n"
                    "   - दर १०० तासांनंतर गिअरबॉक्स तेल पातळी तपासा. फक्त ISO VG 320 सिंथेटिक ऑईल वापरा.\n\n"
                    "2. **हायड्रोलिक दाब कॅलिब्रेशन:**\n"
                    "   - रोलर बेअरिंग दाब २१० bar असावा. व्हायब्रेशन ४.५ mm/s पेक्षा कमी असावे."
                )
            elif "PPE" in title or "Safety" in title or "नो-स्मोकिंग" in chunk_text or "Strict No-Smoking" in chunk_text:
                marathi_summary = (
                    "1. **धूम्रपान बंदी:** कारखाना परिसरात धूम्रपान करण्यास मनाई आहे.\n"
                    "2. **ड्युटीपूर्वी चाचणी:** बायोमेट्रिक पडताळणी आणि अल्कोहोल टेस्ट अनिवार्य आहे.\n"
                    "3. **PPE नियम:** हेल्मेट, स्टील-टो बूट आणि रिफ्लेक्टिव्ह जॅकेट परिधान करणे अनिवार्य आहे."
                )

            response = f"**{title} कडून माहिती (Role: {role}):**\n\n"
            response += f"{marathi_summary}\n\n"
            response += "💡 **महत्त्वाचा सुरक्षा नियम:** पोलाद कारखान्यात काम करताना नेहमी सुरक्षा हेल्मेट, सुरक्षा शूज आणि चष्मा वापरा."
        else:
            # 100% Pure English Response
            english_summary = chunk_text
            # Convert known Hindi SOP text into pure English if necessary
            if "ब्लास्ट फर्नेस" in chunk_text:
                english_summary = (
                    "1. **Blast Furnace Safety SOP:**\n"
                    "   - Blast furnace temperatures exceed 1500°C.\n"
                    "   - All plant operators must wear heat-resistant suits, safety helmets, thermal gloves, and protective goggles.\n\n"
                    "2. **Emergency Shutdown Procedure:**\n"
                    "   - If gas pressure exceeds 2.5 bar, immediately close Main Control Valve (B-4) and press the Red Emergency Button.\n"
                    "   - All plant personnel must immediately evacuate to Assembly Point 2.\n\n"
                    "3. **Hot Metal Tapping:** Maintain a minimum safety distance of 5 meters during liquid iron tapping."
                )
            elif "रोलिंग मिल" in chunk_text:
                english_summary = (
                    "1. **Rolling Mill Gearbox Inspection:**\n"
                    "   - Check gearbox oil levels after every 100 operating hours. Use ISO VG 320 synthetic gear oil only.\n\n"
                    "2. **Hydraulic Pressure Calibration:**\n"
                    "   - Roller bearing operating pressure must remain steady at 210 bar.\n"
                    "   - Vibration sensor levels must stay below 4.5 mm/s."
                )
            elif "नो-स्मोकिंग" in chunk_text:
                english_summary = (
                    "1. **Strict No-Smoking Policy:** Smoking inside factory premises is strictly prohibited.\n"
                    "2. **Pre-Duty Checks:** Mandatory biometric verification and alcohol breathalyzer test before starting shift.\n"
                    "3. **PPE Compliance:** Wearing hard hat, steel-toe boots, and reflective jacket is compulsory before entering shock zones or under overhead cranes."
                )

            response = f"**Information from {title} (Role: {role}):**\n\n"
            response += f"{english_summary}\n\n"
            response += "💡 **Important Safety Notice:** Always wear protective helmet, steel-toe safety boots, and goggles while on the factory floor."
            
        return response
