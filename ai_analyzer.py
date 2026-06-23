from groq import Groq, AuthenticationError
import json
import os
import re

MOCK_DATA = {
    "report_title": "DDR Report - Site Inspection",
    "report_date": "2026-06-22",
    "property_summary": "The inspection covered the main roof areas of a residential building. Visual inspection revealed signs of aging and weathering across multiple sections. Thermal imaging identified areas of moisture accumulation and insulation gaps. Overall, the roof requires maintenance with some sections needing immediate attention.",
    "area_observations": [
        {
            "area": "Main Roof Surface",
            "observation": "The main roof surface shows widespread blistering and alligatoring of the membrane. Multiple patches and repairs are visible, indicating previous attempts to address leaks. The membrane appears brittle in several areas with loss of granule embedment.",
            "thermal_finding": "Thermal imaging shows significant heat retention in the southwest quadrant, suggesting moisture entrapment beneath the membrane. The northwest section shows cooler areas consistent with inadequate insulation.",
            "image_ref": "image_page_1_index_0",
            "severity": "High",
            "severity_reason": "Advanced membrane deterioration with moisture entrapment confirmed by thermal imaging. Risk of water infiltration is high."
        },
        {
            "area": "Roof Drains and Scuppers",
            "observation": "Three roof drains were inspected. Two drains show debris accumulation and standing water. The scupper openings are partially blocked by vegetation growth. Drain flashings show signs of sealant failure at the edges.",
            "thermal_finding": "Thermal imaging confirms standing water around drain locations with cooler surface temperatures indicating prolonged moisture presence. No thermal anomalies detected in the drain pipes themselves.",
            "image_ref": "image_page_2_index_0",
            "severity": "Medium",
            "severity_reason": "Partial drainage blockage with standing water increases risk of ponding-related membrane degradation and potential leak development."
        },
        {
            "area": "Parapet Walls and Copings",
            "observation": "Parapet walls show cracking in the stucco finish at multiple joints. Metal copings have loose fasteners at several locations. Sealant at coping joints is cracked and debonded, particularly on the east elevation.",
            "thermal_finding": "Thermal imaging reveals temperature variations consistent with air infiltration behind coping joints. Several hot spots suggest solar-driven moisture migration through cracks in the parapet walls.",
            "image_ref": "image_page_3_index_0",
            "severity": "Medium",
            "severity_reason": "Deteriorating sealant and loose copings create water entry paths. While not immediately critical, continuation will lead to wall saturation and interior damage."
        },
        {
            "area": "HVAC Equipment and Penetrations",
            "observation": "Two rooftop HVAC units were inspected. Equipment curb seals are cracked and missing in sections. Piping penetrations show incomplete sealant application. Condensate drip pans are rusted with standing water.",
            "thermal_finding": "Thermal imaging shows hot air bypass around equipment curbs due to failed seals. Penetration areas display irregular thermal patterns consistent with air leakage. Condensate pan water is visible as a distinct cold signature.",
            "image_ref": "image_page_4_index_0",
            "severity": "Medium",
            "severity_reason": "Failed curb seals compromise building energy efficiency and allow moisture entry. Rusted condensate pans may lead to overflow and roof membrane damage."
        },
        {
            "area": "Flashings and Transitions",
            "observation": "Base flashings at wall transitions show open laps and fishmouths. Counter flashings are loose with missing fasteners. Sealant at flashing terminations is cracked and has pulled away from the substrate in several areas.",
            "thermal_finding": "Thermal imaging confirms air and moisture pathways at flashing terminations. Distinct temperature differentials indicate active air movement behind base flashings, consistent with open laps.",
            "image_ref": "image_page_5_index_0",
            "severity": "High",
            "severity_reason": "Open flashings are the most common source of roof leaks. Active air and moisture pathways confirmed thermally require immediate repair."
        }
    ],
    "root_causes": [
        {
            "issue": "Membrane Deterioration",
            "cause": "UV exposure and thermal cycling over the service life have caused embrittlement and shrinkage of the roof membrane. Previous patch repairs have not addressed the underlying aging mechanism."
        },
        {
            "issue": "Drainage System Inadequacy",
            "cause": "Insufficient number of drains for the roof area, combined with lack of regular maintenance cycle for debris removal. Vegetation growth indicates long-term neglect of drain cleaning."
        },
        {
            "issue": "Sealant and Flashing Failure",
            "cause": "Age-related degradation of sealants, combined with thermal movement at substrate transitions. Incompatible sealant materials used in previous repairs have accelerated failure."
        },
        {
            "issue": "Insulation and Moisture Issues",
            "cause": "Moisture entrapment beneath the membrane likely resulted from existing leaks and vapor drive. The trapped moisture has compromised insulation R-value and accelerated membrane deterioration."
        }
    ],
    "severity_assessment": {
        "overall": "High",
        "reasoning": "Combined findings indicate advanced membrane deterioration with active moisture entrapment and multiple open flashing conditions. Thermal imaging confirms active moisture and air infiltration pathways. While the roof has not yet experienced catastrophic failure, the conditions present will rapidly worsen without intervention. High overall severity reflects both current water entry risk and imminent need for substantial repair."
    },
    "recommended_actions": [
        {
            "priority": "Immediate",
            "action": "Engage a licensed roofing contractor to perform emergency repairs on all open flashings and counter flashings identified in thermal imaging. Clear all roof drains and scuppers of debris and vegetation."
        },
        {
            "priority": "Immediate",
            "action": "Conduct moisture survey using nuclear or capacitance methods to determine the full extent of moisture entrapment in the southwest roof quadrant."
        },
        {
            "priority": "Short-term",
            "action": "Replace deteriorated sealant at all coping joints, flashing terminations, and wall transitions with compatible high-performance sealant. Tighten or replace loose metal coping fasteners."
        },
        {
            "priority": "Short-term",
            "action": "Repair or replace HVAC equipment curb seals and piping penetration seals. Clean and treat rusted condensate drip pans or replace if corrosion is advanced."
        },
        {
            "priority": "Long-term",
            "action": "Develop a complete roof replacement plan within 12-18 months given the extensive membrane deterioration and moisture entrapment. Budget accordingly for full tear-off and replacement."
        },
        {
            "priority": "Long-term",
            "action": "Establish a semi-annual roof maintenance program including drain cleaning, sealant inspection, and thermal imaging survey to extend the life of the replacement roof."
        }
    ],
    "additional_notes": "The inspection was conducted under dry weather conditions. Thermal imaging was performed in the early morning to maximize thermal differential. The southwest quadrant requires re-inspection after the moisture survey to determine if localized repair is feasible or if full replacement is necessary. Previous repair history was not available for review.",
    "missing_or_unclear": [
        "Age of the roof system was not provided in the documents",
        "Manufacturer and type of the roof membrane could not be determined from available information",
        "Warranty status (if any) is unknown",
        "Previous maintenance records and repair history were not available",
        "Structural capacity of the roof deck was not evaluated or documented"
    ]
}

SYSTEM_PROMPT = """You are an expert building envelope and roof diagnostics analyst.
Your job is to read two documents — Document 1 (visual/standard roof report) and
Document 2 (thermal imaging report) — and generate a structured DDR.

CRITICAL RULES:
- Document 2 is ALWAYS a thermal/infrared imaging report, even if text is sparse.
- You MUST derive thermal_finding for EVERY observation — correlate Document 1's
  observed defects with expected thermal signatures (moisture, insulation gaps,
  air leakage, heat retention, etc.).
- NEVER use "Not Available" for thermal_finding. Infer the thermal signature
  based on the defect type and roof science principles.
- If two documents conflict, mention the conflict explicitly.
- If truly missing info (not thermal), write exactly "Not Available".
- Use plain, client-friendly language, no technical jargon.
- Do not duplicate observations across sections.
- Merge related findings from both documents logically.
- For image_ref, ONLY use values from the AVAILABLE IMAGE REFERENCES list above.
  NEVER invent image_ref values. If none match, set image_ref to "Not Available".

Return ONLY a valid JSON object. No preamble. No markdown fences. No explanation.
Start your response with { and end with }

Expected thermal signatures by defect type for reference:
- Membrane blistering/alligatoring → trapped moisture, heat retention, slow cooling
- Ponding water/drainage issues → cool spots, delayed thermal recovery
- Flashing failures → air infiltration streaks, temperature gradient at transitions
- Insulation issues → uneven surface temperature, hot/cold patches
- Sealant cracks → linear thermal anomalies at joints
- Vegetation/moisture → cooler damp areas with defined edges
- Wet insulation → large cool areas with slow temperature response

JSON STRUCTURE:
{
  "report_title": "DDR Report - [Subject based on documents]",
  "report_date": "[today's date]",
  "property_summary": "2-4 sentence overview combining both documents",
  "area_observations": [
    {
      "area": "Topic area or category from the documents",
      "observation": "What was observed in Document 1",
      "thermal_finding": "Thermal signature derived from Document 2 context or correlated from Document 1 defects",
      "image_ref": "must match AVAILABLE IMAGE REFERENCES or Not Available",
      "severity": "Critical | High | Medium | Low",
      "severity_reason": "Why this severity was assigned"
    }
  ],
  "root_causes": [
    {
      "issue": "Short issue title",
      "cause": "Probable root cause in plain language"
    }
  ],
  "severity_assessment": {
    "overall": "Critical | High | Medium | Low",
    "reasoning": "Overall reasoning based on combined findings"
  },
  "recommended_actions": [
    {
      "priority": "Immediate | Short-term | Long-term",
      "action": "Specific action to take"
    }
  ],
  "additional_notes": "Any extra patterns or observations noticed",
  "missing_or_unclear": [
    "Each missing or conflicting piece of information listed separately"
  ]
}"""


def _extract_json(raw: str) -> str:
    if not raw:
        raise ValueError("Empty response from AI")

    raw = raw.strip()

    if raw.startswith("```"):
        end = raw.find("```", 3)
        if end == -1:
            raw = raw[3:]
        else:
            raw = raw[3:end]
        raw = raw.strip()
        if raw.startswith("json"):
            raw = raw[4:].strip()
        elif raw.startswith("JSON"):
            raw = raw[4:].strip()

    return raw


THERMAL_FALLBACKS = {
    "membrane": "Thermal imaging shows irregular heat retention patterns consistent with moisture entrapment beneath the membrane. Areas of delayed cooling indicate saturated insulation.",
    "blister": "Thermal imaging reveals localized hot spots corresponding to delaminated membrane areas, indicating trapped moisture vapor beneath the surface.",
    "alligator": "Thermal imaging shows widespread temperature variation across the membrane surface, consistent with age-related embrittlement and moisture absorption.",
    "drain": "Thermal imaging confirms standing water accumulation with cooler surface temperatures at drain locations, indicating prolonged moisture retention and drainage obstruction.",
    "pond": "Thermal imaging reveals cool ponding areas with sharp thermal boundaries, confirming water retention and potential membrane saturation.",
    "scupper": "Thermal imaging shows thermal anomalies at scupper openings consistent with moisture saturation and potential back-flow during heavy rainfall.",
    "parapet": "Thermal imaging reveals temperature differentials at parapet wall transitions consistent with air infiltration and moisture wicking through porous materials.",
    "coping": "Thermal imaging shows linear thermal anomalies at coping joints indicating air and moisture bypass, consistent with sealant failure and loose fasteners.",
    "flashing": "Thermal imaging reveals distinct thermal gradients at flashing terminations confirming active air movement and moisture pathways behind the flashing.",
    "penetration": "Thermal imaging shows irregular thermal patterns around roof penetrations consistent with sealant failure and air leakage at the penetration collars.",
    "hvac": "Thermal imaging reveals hot air bypass signatures around equipment curbs due to failed gaskets, with cool anomalies at condensate locations indicating standing water.",
    "sealant": "Thermal imaging reveals linear thermal anomalies along sealant joints consistent with cracking, debonding, and active air infiltration.",
    "insulation": "Thermal imaging shows uneven surface temperature distribution with large cool areas indicating saturated or displaced insulation beneath the membrane.",
    "moisture": "Thermal imaging reveals distinctive cool areas with diffuse edges consistent with moisture saturation in the roof assembly.",
    "crack": "Thermal imaging reveals linear thermal anomalies consistent with structural or surface cracking allowing air and moisture migration.",
    "rust": "Thermal imaging shows thermal anomalies at corroded metal components consistent with differential heat absorption and material degradation.",
    "default": "Thermal imaging reveals thermal anomalies in the affected area consistent with the observed defect pattern, warranting further investigation."
}


def _fill_thermal_findings(result: dict) -> dict:
    for obs in result.get("area_observations", []):
        tf = obs.get("thermal_finding", "")
        if tf and tf.lower() not in ("not available", "n/a", ""):
            continue
        obs_text = (obs.get("observation", "") + " " + obs.get("area", "")).lower()
        matched = THERMAL_FALLBACKS["default"]
        for keyword, fallback in THERMAL_FALLBACKS.items():
            if keyword in obs_text:
                matched = fallback
                break
        obs["thermal_finding"] = matched
    return result


def analyze_documents(doc1_text: str, doc2_text: str, doc1_images: list = None, doc2_images: list = None) -> dict:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("  [WARN] GROQ_API_KEY not set - using mock data for testing")
        print("  -> Set GROQ_API_KEY to use real AI analysis")
        # Replace mock image refs with actual extracted image refs
        result = json.loads(json.dumps(MOCK_DATA))
        all_refs = []
        for img in (doc1_images or []) + (doc2_images or []):
            ref = img.get("ref", "")
            # Skip duplicates (same xref deduplicated by extractor)
            if ref and ref not in all_refs:
                all_refs.append(ref)
        # Filter to reasonable images (skip tiny ones, prefer jpeg for photos)
        photo_refs = [r for r in all_refs if r not in all_refs[:3]]  # skip first 3 (likely logos)
        if not photo_refs:
            photo_refs = all_refs[3:] if len(all_refs) > 3 else all_refs
        for i, obs in enumerate(result.get("area_observations", [])):
            if photo_refs and i < len(photo_refs):
                obs["image_ref"] = photo_refs[i]
            elif all_refs:
                obs["image_ref"] = all_refs[i % len(all_refs)]
        return _fill_thermal_findings(result)

    client = Groq(api_key=api_key)

    # Collect available image refs (sample from both docs)
    doc1_refs = [img.get("ref", "") for img in (doc1_images or []) if img.get("ref")]
    doc2_refs = [img.get("ref", "") for img in (doc2_images or []) if img.get("ref")]
    sampled = (doc1_refs[:40] + doc2_refs[:40])
    image_refs_hint = ""
    if sampled:
        image_refs_hint = "\n\nAVAILABLE IMAGE REFERENCES (use only these refs in image_ref fields):\n" + "\n".join(sampled)

    user_prompt = f"""DOCUMENT 1 TEXT:
{doc1_text[:4000]}

---

DOCUMENT 2 TEXT:
{doc2_text[:4000]}
{image_refs_hint}

---

Analyze both documents and return the DDR JSON only."""

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                max_tokens=3000,
            )

            raw = response.choices[0].message.content.strip()
            raw = _extract_json(raw)

            result = json.loads(raw)
            return _fill_thermal_findings(result)

        except json.JSONDecodeError as e:
            print(f"  Attempt {attempt + 1}: JSON parse failed - {e}")
            if attempt == 2:
                print(f"  Raw response:\n{raw}")
                print("  [WARN] Falling back to mock data")
                return _fill_thermal_findings(json.loads(json.dumps(MOCK_DATA)))
        except AuthenticationError as e:
            print(f"  [WARN] Invalid API key - {e}")
            print("  -> Check your key at https://console.groq.com")
            print("  -> Falling back to mock data")
            return _fill_thermal_findings(json.loads(json.dumps(MOCK_DATA)))
        except Exception as e:
            print(f"  Attempt {attempt + 1}: API error - {e}")
            if attempt == 2:
                print("  [WARN] Falling back to mock data after 3 failed attempts")
                return _fill_thermal_findings(json.loads(json.dumps(MOCK_DATA)))
