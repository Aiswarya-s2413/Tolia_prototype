import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tolia_backend.settings')
django.setup()

from chat_rag.models import Document, DocumentChunk, Department, DocumentCategory

def seed_factory_sops():
    # Documents to ensure exist
    sops = [
        {
            "title": "Blast Furnace Operations & Emergency Shutdown SOP",
            "category": DocumentCategory.BLAST_FURNACE,
            "required_department": Department.QC,
            "is_confidential": False,
            "content": """Standard Operating Procedure: Blast Furnace Operations (SOP-BF-01)
1. Operating Temperatures:
   - Hearth temperature: 1450°C to 1550°C.
   - Tuyere flame temperature: 2000°C to 2200°C.
   - Top gas temperature: 150°C to 250°C.
   - All personnel must wear full heat-resistant aluminized proximity suits, safety helmets with gold-coated face shields, and thermal gloves.

2. Emergency Shutdown Procedure (CRITICAL):
   - Step 1: If gas pressure exceeds 2.5 bar or sudden temperature anomaly occurs, immediately close Main Blast Control Valve (Valve B-4).
   - Step 2: Press the Red Emergency Stop Button located on Control Console #1 or at Tuyere Platform Exit #3.
   - Step 3: Snort valve opens automatically to vent blast air to atmosphere.
   - Step 4: Initiate Nitrogen purge into the furnace top to prevent explosive gas backdraft.
   - Step 5: Sound the Plant Siren (3 short blasts) and evacuate all floor staff to Assembly Point 2 immediately.

3. Hot Metal Tapping Protocol:
   - Maintain minimum 5 meters clearance during liquid iron tapping.
   - Verify mud gun hydraulic pressure is at 180 bar before plugging taphole."""
        },
        {
            "title": "Heavy Rolling Mill Machinery Maintenance SOP",
            "category": DocumentCategory.MAINTENANCE,
            "required_department": Department.QC,
            "is_confidential": False,
            "content": """Standard Operating Procedure: Rolling Mill Maintenance (SOP-RM-04)
1. Gearbox Lubrication:
   - Check gearbox oil levels every 100 operating hours.
   - Lubricant specification: ISO VG 320 synthetic heavy-duty industrial gear oil only.
   - Oil replacement interval: Every 2,000 hours or when viscosity degrades beyond ±10%.

2. Hydraulic Pressure & Calibration:
   - Roller bearing hydraulic clamping pressure must remain steady at 210 bar ± 5 bar.
   - Vibration sensor threshold: Maximum allowable vibration is 4.5 mm/s RMS. If vibration exceeds 5.0 mm/s, immediately halt the line for bearing alignment.
   - Roll gap calibration must be checked using digital micrometers at start of every shift."""
        },
        {
            "title": "Plant General Safety & PPE Guidelines",
            "category": DocumentCategory.GENERAL_SAFETY,
            "required_department": Department.QC,
            "is_confidential": False,
            "content": """Plant General Safety & PPE Mandatory Guidelines (SOP-SAF-02)
1. Personal Protective Equipment (PPE):
   - Level 1 Mandatory Floor PPE: ANSI Z89.1 certified Hard Hat, Steel-Toe Safety Boots with puncture-resistant soles, High-Visibility Reflective Vest, and UV400 Safety Goggles.
   - Ear protection (ear muffs / plugs rated NRR 28dB+) required in Rolling Mill and Blower areas.

2. General Prohibitions:
   - Strict Zero-Tolerance No-Smoking policy across all plant zones.
   - Mandatory breathalyzer alcohol test and biometric verification before shift entry.
   - Never stand under overhead crane paths or active ladle transport tracks."""
        },
        {
            "title": "Steel Quality & Hardness Testing SOP",
            "category": DocumentCategory.QUALITY_CONTROL,
            "required_department": Department.QC,
            "is_confidential": False,
            "content": """Quality Control & Steel Testing Guidelines (SOP-QC-09)
1. Hardness Testing:
   - High Carbon Steel Grinding Balls: Rockwell Hardness C (HRC) must be between 58 and 65 HRC across the surface and minimum 55 HRC at volumetric center.
   - Testing method: ASTM E18 standard using diamond spheroconical indenter with 150 kgf load.

2. Microstructure & Surface Integrity:
   - Martensitic grain structure required with less than 5% retained austenite.
   - Surface defect limits: No cracks deeper than 0.2 mm allowed."""
        },
        {
            "title": "Confidential Q1-Q4 Sales, Client Pricing & Revenue Strategy",
            "category": DocumentCategory.MARKETING_SALES,
            "required_department": Department.CEO,
            "is_confidential": True,
            "content": """CONFIDENTIAL EXECUTIVE REPORT: Commercial Sales & Pricing Targets (FIN-2026-CONF)
RESTRICTED ACCESS: CEO / Executive Leadership Only.

1. Revenue & Sales Targets:
   - Q1 Revenue Target: ₹125 Crore ($15M USD) with an operating profit margin target of 18.5%.
   - Q2 Revenue Target: ₹140 Crore with focus on export shipments to Southeast Asia.
   - Annual Target: ₹550 Crore total sales revenue.

2. Client Contract Pricing:
   - Tier 1 Mining Clients (Forged Steel Balls): ₹72,500 per metric ton (ex-works).
   - Commercial Rebate: 3.5% discount applicable on orders exceeding 5,000 metric tons per quarter.
   - Raw Material Procurement Hedge: Iron ore pegged at ₹4,800/ton."""
        }
    ]

    for item in sops:
        doc, created = Document.objects.update_or_create(
            title=item["title"],
            defaults={
                "category": item["category"],
                "required_department": item["required_department"],
                "content": item["content"],
                "is_confidential": item["is_confidential"]
            }
        )
        # Clear existing chunks for this doc and regenerate
        doc.chunks.all().delete()
        
        words = item["content"].split()
        chunk_size = 120
        for i in range(0, len(words), chunk_size):
            chunk_text = " ".join(words[i:i+chunk_size])
            DocumentChunk.objects.create(
                document=doc,
                chunk_index=i // chunk_size,
                text=chunk_text,
                required_department=item["required_department"]
            )
        print(f"Seeded: {doc.title} ({'Created' if created else 'Updated'})")

if __name__ == "__main__":
    seed_factory_sops()
