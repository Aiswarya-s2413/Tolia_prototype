import os
import sys
import json
import requests
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tolia_backend.settings')
django.setup()

from chat_rag.models import Document, DocumentChunk, Department
from chat_rag.rag_engine import LocalRAGEngine, normalize_voice_query, get_embedding

def run_comprehensive_tests():
    results = []

    print("=" * 60)
    print("RUNNING COMPREHENSIVE TOLIA PROTOTYPE SYSTEM AUDIT")
    print("=" * 60)

    # 1. DB Vector Index Audit
    total_chunks = DocumentChunk.objects.count()
    embedded_chunks = DocumentChunk.objects.filter(embedding__isnull=False).count()
    unembedded_chunks = DocumentChunk.objects.filter(embedding__isnull=True).count()
    
    results.append({
        "test": "Vector Database 768d Index Integrity",
        "passed": (unembedded_chunks == 0 and total_chunks > 0),
        "details": f"Total Chunks: {total_chunks} | Embedded: {embedded_chunks} | Missing: {unembedded_chunks}"
    })

    # 2. Phonetic Normalizer Test
    test_phrases = [
        ("what are the plan PPA safe requirements", "what are the plant ppe safety requirements"),
        ("what are the plan PPS safety requirements", "what are the plant ppe safety requirements"),
        ("blast farnace emergency sut down", "blast furnace emergency shutdown"),
        ("rolin mill gear box hidraulic pressure", "rolling mill gearbox hydraulic pressure")
    ]
    norm_passed = True
    for input_phrase, expected_normalized in test_phrases:
        actual_norm = normalize_voice_query(input_phrase)
        if actual_norm != expected_normalized:
            norm_passed = False
            print(f"Normalizer mismatch: '{input_phrase}' -> '{actual_norm}' (Expected: '{expected_normalized}')")
    
    results.append({
        "test": "Voice ASR Phonetic Normalizer",
        "passed": norm_passed,
        "details": f"Verified {len(test_phrases)} phonetic acoustic variations (PPA, PPS, plan, farnace, sut down)"
    })

    # 3. Test Query A: Plant PPE Safety
    res_a = LocalRAGEngine.query("what are the plan PPA safe requirements", user_role=Department.QC, target_lang='en')
    passed_a = "Mandatory Floor PPE" in res_a["response"] and "Hard Hat" in res_a["response"]
    results.append({
        "test": "Query: Plant PPE Safety (Acoustic Mishearing)",
        "passed": passed_a,
        "doc_source": res_a["sources"][0]["doc_title"] if res_a["sources"] else "None",
        "snippet": res_a["response"][:120] + "..."
    })

    # 4. Test Query B: Blast Furnace Emergency Shutdown
    res_b = LocalRAGEngine.query("what are the emergency shutdown steps for blast furnace", user_role=Department.QC, target_lang='en')
    passed_b = "Valve B-4" in res_b["response"] and "Red Emergency" in res_b["response"]
    results.append({
        "test": "Query: Blast Furnace Emergency Shutdown",
        "passed": passed_b,
        "doc_source": res_b["sources"][0]["doc_title"] if res_b["sources"] else "None",
        "snippet": res_b["response"][:120] + "..."
    })

    # 5. Test Query C: Rolling Mill Maintenance
    res_c = LocalRAGEngine.query("rolling mill gearbox oil and hydraulic pressure", user_role=Department.QC, target_lang='en')
    passed_c = "ISO VG 320" in res_c["response"] and "210 bar" in res_c["response"]
    results.append({
        "test": "Query: Rolling Mill Maintenance SOP",
        "passed": passed_c,
        "doc_source": res_c["sources"][0]["doc_title"] if res_c["sources"] else "None",
        "snippet": res_c["response"][:120] + "..."
    })

    # 6. Test Query D: RBAC Security Guardrail (QC Refusal)
    res_d = LocalRAGEngine.query("what are the confidential sales and revenue targets", user_role=Department.QC, target_lang='en')
    passed_d = res_d["access_blocked"] == True and "Security Restricted" in res_d["response"]
    results.append({
        "test": "RBAC Security Guardrail: QC Access to Confidential Sales",
        "passed": passed_d,
        "access_blocked": res_d["access_blocked"],
        "snippet": res_d["response"][:120] + "..."
    })

    # 7. Test Query E: RBAC CEO Access (Authorized)
    res_e = LocalRAGEngine.query("what are the confidential sales and revenue targets", user_role=Department.CEO, target_lang='en')
    passed_e = res_e["access_blocked"] == False and "125 Crore" in res_e["response"]
    results.append({
        "test": "RBAC Security: CEO Authorized Access to Sales Data",
        "passed": passed_e,
        "access_blocked": res_e["access_blocked"],
        "snippet": res_e["response"][:120] + "..."
    })

    # 8. Live HTTP API Test
    try:
        http_res = requests.post(
            "http://127.0.0.1:8000/api/chat/",
            json={"query": "what are the plant safety rules", "user_role": "CEO", "language": "en"},
            timeout=5.0
        )
        http_passed = http_res.status_code == 200 and "response" in http_res.json()
    except Exception as e:
        http_passed = False
    
    results.append({
        "test": "Live Django REST API Endpoint (POST /api/chat/)",
        "passed": http_passed,
        "details": f"Status Code: {http_res.status_code if http_passed else 'Error'}"
    })

    print(json.dumps(results, indent=2))
    return results

if __name__ == "__main__":
    run_comprehensive_tests()
