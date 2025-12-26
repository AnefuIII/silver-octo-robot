"""
LLM Reasoning Layer (Step 1 + Step 2)

Responsibilities:
- Explain results
- Ask clarifying questions
- Re-rank vendors using judgment
"""

from typing import List, Dict, Optional

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from config import Config


class LLMReasoner:
    """Reasoning and judgment layer for vendor discovery."""

    def __init__(self):
        self.client = None
        if OpenAI and Config.OPENAI_API_KEY:
            self.client = OpenAI(api_key=Config.OPENAI_API_KEY)

    # ==============================================================
    # STEP 1 — ANALYSIS & EXPLANATION
    # ==============================================================

    def analyze_results(
        self,
        service: str,
        location: str,
        vendors: List[Dict]
    ) -> Dict:
        if not self.client or not vendors:
            return self._fallback_analysis(service, location, vendors)

        prompt = self._build_analysis_prompt(service, location, vendors)

        try:
            response = self.client.chat.completions.create(
                model="gpt-4.1-mini",
                temperature=0.2,
                messages=[
                    {"role": "system", "content": self._system_prompt()},
                    {"role": "user", "content": prompt}
                ]
            )
            return self._safe_json(response.choices[0].message.content)

        except Exception as e:
            return self._fallback_analysis(service, location, vendors, error=str(e))

    # ==============================================================
    # STEP 2 — LLM RE-RANKING
    # ==============================================================

    def rerank_vendors(
        self,
        service: str,
        vendors: List[Dict],
        max_vendors: int = 10
    ) -> Dict:
        """
        Re-rank vendors using qualitative judgment.

        Returns:
        {
            "ordered_vendor_ids": [0, 2, 1],
            "reasoning": "..."
        }
        """

        if not self.client or len(vendors) < 2:
            return {
                "ordered_vendor_ids": list(range(len(vendors))),
                "reasoning": "Deterministic ranking retained."
            }

        vendor_snapshot = []
        for idx, v in enumerate(vendors[:max_vendors]):
            vendor_snapshot.append({
                "id": idx,
                "name": v["identity"]["name"],
                "confidence": v["confidence_score"],
                "has_whatsapp": bool(v["contacts"]["whatsapp"]),
                "has_instagram": bool(v["social"]["instagram"]),
                "location": v["location"].get("resolved"),
                "has_maps": bool(v["location"].get("google_maps"))
            })

        prompt = f"""
You are helping rank vendors for the service "{service}".

Here are vendor candidates (JSON):
{vendor_snapshot}

Instructions:
- Reorder vendors by overall usefulness to the user.
- Prefer vendors that appear professional, reachable, and relevant.
- Do NOT invent data.
- Return ONLY JSON.

Required JSON format:
{{
  "ordered_vendor_ids": [list of vendor ids in best-to-worst order],
  "reasoning": "brief explanation"
}}
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4.1-mini",
                temperature=0.1,
                messages=[
                    {"role": "system", "content": self._system_prompt()},
                    {"role": "user", "content": prompt}
                ]
            )
            return self._safe_json(response.choices[0].message.content)

        except Exception as e:
            return {
                "ordered_vendor_ids": list(range(len(vendors))),
                "reasoning": f"LLM re-ranking failed: {e}"
            }

    # ==============================================================
    # PROMPTS & UTILITIES
    # ==============================================================

    def _system_prompt(self) -> str:
        return (
            "You are a careful assistant that reasons over provided data only. "
            "You never fabricate facts and you keep explanations concise."
        )

    def _build_analysis_prompt(self, service: str, location: str, vendors: List[Dict]) -> str:
        summary = [
            {
                "name": v["identity"]["name"],
                "confidence": v["confidence_score"],
                "location": v["location"].get("resolved"),
                "has_whatsapp": bool(v["contacts"]["whatsapp"])
            }
            for v in vendors[:5]
        ]

        return f"""
User searched for "{service}" vendors in "{location}".

Top candidates (JSON):
{summary}

Tasks:
1. Explain briefly how vendors were selected.
2. Rate result quality: good / average / weak.
3. Ask ONE clarifying question if needed, otherwise say "NO_QUESTION".

Respond ONLY in JSON with keys:
- explanation
- result_quality
- clarifying_question
"""

    def _safe_json(self, content: str) -> Dict:
        import json
        try:
            return json.loads(content)
        except Exception:
            return {
                "explanation": content,
                "result_quality": "unknown",
                "clarifying_question": "NO_QUESTION"
            }

    def _fallback_analysis(
        self,
        service: str,
        location: str,
        vendors: List[Dict],
        error: Optional[str] = None
    ) -> Dict:
        quality = "good" if len(vendors) >= 3 else "weak"
        return {
            "explanation": (
                f"Found {len(vendors)} vendors for {service} in {location} "
                "based on contact availability and location relevance."
            ),
            "result_quality": quality,
            "clarifying_question": "NO_QUESTION",
            "error": error
        }

    def decide_next_search(
    self,
    service: str,
    location: str,
    platform: str,
    vendors: List[Dict]
    ) -> Dict:
        """
        Decide whether to refine or expand search.
        """

        # Hard guardrail: if results are decent, stop
        if len(vendors) >= 3:
            return {"action": "STOP"}

        if not self.client:
            return {"action": "STOP"}

        vendor_summary = [
            {
                "confidence": v["confidence_score"],
                "has_whatsapp": bool(v["contacts"]["whatsapp"]),
                "location": v["location"].get("resolved")
            }
            for v in vendors
        ]

        prompt = f"""
    User searched for "{service}" vendors in "{location}" on "{platform}".

    Current results (JSON):
    {vendor_summary}

    Decide ONE action:
    - STOP
    - EXPAND_LOCATION
    - TRY_ANOTHER_PLATFORM
    - RELAX_CONFIDENCE

    Rules:
    - Choose STOP if results are acceptable.
    - Choose ONLY ONE action.
    - Do NOT invent data.

    Respond ONLY in JSON:
    {{ "action": "<ACTION_NAME>" }}
    """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4.1-mini",
                temperature=0,
                messages=[
                    {"role": "system", "content": self._system_prompt()},
                    {"role": "user", "content": prompt}
                ]
            )
            return self._safe_json(response.choices[0].message.content)

        except Exception:
            return {"action": "STOP"}

    def is_actual_vendor(self, service: str, vendor: Dict) -> bool:
        """
        LLM-based intent classification.
        """

        if not self.client:
            return True  # fallback: allow deterministic path

        identity = vendor.get("identity", {})
        contacts = vendor.get("contacts", {})
        social = vendor.get("social", {})

        prompt = f"""
    You are evaluating whether an online account is a REAL SERVICE VENDOR.

    Service: {service}

    Account details:
    Name: {identity.get("name")}
    URL: {identity.get("url")}
    Has WhatsApp: {bool(contacts.get("whatsapp"))}
    Has Instagram: {bool(social.get("instagram"))}

    Question:
    Is this account offering services, or is it just content, news, or discussion?

    Respond ONLY in JSON:
    {{ "is_vendor": true | false }}
    """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4.1-mini",
                temperature=0,
                messages=[
                    {"role": "system", "content": self._system_prompt()},
                    {"role": "user", "content": prompt}
                ]
            )
            result = self._safe_json(response.choices[0].message.content)
            return bool(result.get("is_vendor"))

        except Exception:
            return True
