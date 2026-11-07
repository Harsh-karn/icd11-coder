import os
import json
import re
import asyncio
from typing import List, Dict, Any, Optional

try:
    from openai import OpenAI, AsyncOpenAI
except ImportError:
    OpenAI = None
    AsyncOpenAI = None

try:
    # pyrefly: ignore[missing-import]
    from anthropic import Anthropic, AsyncAnthropic
except ImportError:
    Anthropic = None
    AsyncAnthropic = None

SYSTEM_PROMPT = """You are an expert WHO ICD-11 medical coding specialist for outpatient clinics.
Your job is to read a clinical encounter note and propose up to 3 diagnostic codes from ICD-11 MMS (2026-01), ranked from best to worst.

CRITICAL ICD-11 CODING RULES:
1. PRIMARY ENCOUNTER DIAGNOSIS: Code the acute complaint or definitive diagnosis driving this clinic visit.
2. SPECIFICITY FIRST: Choose the most specific leaf code supported by the note. Parent category codes do NOT count when a more specific child category applies.
3. UNSPECIFIED (.Z) RESIDUAL CODES: If the clinical note mentions a diagnosis (e.g., malaria, pneumonia, gastroenteritis, tonsillitis, asthma) but does not provide the organism or subtype detail, you MUST pick the .Z (unspecified) residual code.
4. EXCLUSIONS & NEGATIONS: Do NOT code conditions that are ruled out, tested negative, or excluded (e.g. "mRDT NEG, malaria excluded" -> code the viral URTI, NOT malaria).
5. ONLY CODES FROM THE CANDIDATE LIST: You MUST pick exclusively from the candidate list provided below. Every code must be an exact category code.
6. OUTPUT FORMAT: Respond ONLY with a valid JSON object containing a "codes" array with up to 3 codes in descending order of confidence:
{"codes": ["CODE_1", "CODE_2", "CODE_3"]}"""

USER_PROMPT_TEMPLATE = """CLINICAL NOTE:
\"\"\"
{note_text}
\"\"\"

TOP RETRIEVED ICD-11 CANDIDATES:
{candidate_list}

Select the best 1 to 3 codes for this note. Respond ONLY with valid JSON:
{{"codes": ["...", "..."]}}"""


class LLMCoder:
    def __init__(self, valid_codes: set):
        self.valid_codes = valid_codes
        self.openai_key = os.environ.get("OPENAI_API_KEY")
        self.anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        
        self.openai_client = None
        self.anthropic_client = None
        self.async_openai = None
        self.async_anthropic = None

        if self.openai_key and OpenAI:
            # Respects HTTPS_PROXY automatically
            self.openai_client = OpenAI(api_key=self.openai_key)
            self.async_openai = AsyncOpenAI(api_key=self.openai_key)
        elif self.anthropic_key and Anthropic:
            self.anthropic_client = Anthropic(api_key=self.anthropic_key)
            self.async_anthropic = AsyncAnthropic(api_key=self.anthropic_key)

    @property
    def is_available(self) -> bool:
        return bool(self.openai_client or self.anthropic_client)

    def format_candidates(self, candidates: List[Dict[str, Any]]) -> str:
        lines = []
        for i, c in enumerate(candidates[:20], 1):
            leaf_str = "LEAF" if c.get("leaf") else "PARENT"
            res_str = "UNSPECIFIED/RESIDUAL" if c.get("residual") else "SPECIFIC"
            hier = " > ".join(c.get("hierarchy", [])[-2:])
            lines.append(f"{i}. [{c['code']}] {c['title']} ({leaf_str}, {res_str}) | Context: {hier}")
        return "\n".join(lines)

    def predict_sync(self, note_text: str, candidates: List[Dict[str, Any]]) -> List[str]:
        """Synchronous single-note prediction using LLM if available, with validation."""
        if not self.is_available or not candidates:
            return []

        cand_str = self.format_candidates(candidates)
        prompt = USER_PROMPT_TEMPLATE.format(note_text=note_text.strip(), candidate_list=cand_str)

        response_text = None
        try:
            if self.openai_client:
                # gpt-4o-mini is ultra-fast and cheap (~$0.15 / 1M input tokens)
                resp = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.0,
                    max_tokens=150,
                    timeout=8.0
                )
                response_text = resp.choices[0].message.content
            elif self.anthropic_client:
                resp = self.anthropic_client.messages.create(
                    model="claude-3-5-haiku-20241022",
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=150,
                    temperature=0.0,
                    timeout=8.0
                )
                response_text = resp.content[0].text
        except Exception as e:
            # Silently fall back to retriever on network / proxy timeout
            return []

        return self._parse_and_validate(response_text)

    async def predict_async(self, note_text: str, candidates: List[Dict[str, Any]]) -> List[str]:
        """Asynchronous single-note prediction with timeout."""
        if not self.is_available or not candidates:
            return []

        cand_str = self.format_candidates(candidates)
        prompt = USER_PROMPT_TEMPLATE.format(note_text=note_text.strip(), candidate_list=cand_str)

        response_text = None
        try:
            if self.async_openai:
                resp = await asyncio.wait_for(
                    self.async_openai.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": prompt}
                        ],
                        response_format={"type": "json_object"},
                        temperature=0.0,
                        max_tokens=150
                    ),
                    timeout=7.0
                )
                response_text = resp.choices[0].message.content
            elif self.async_anthropic:
                resp = await asyncio.wait_for(
                    self.async_anthropic.messages.create(
                        model="claude-3-5-haiku-20241022",
                        system=SYSTEM_PROMPT,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=150,
                        temperature=0.0
                    ),
                    timeout=7.0
                )
                response_text = resp.content[0].text
        except Exception:
            return []

        return self._parse_and_validate(response_text)

    def _parse_and_validate(self, text: Optional[str]) -> List[str]:
        if not text:
            return []
        try:
            data = json.loads(text)
            raw_codes = data.get("codes", [])
        except Exception:
            # Fallback regex extraction if json fails
            raw_codes = re.findall(r"\b[0-9][A-Z0-9]+(?:\.[A-Z0-9]+)?\b", text)

        valid_predictions = []
        for c in raw_codes:
            clean_c = c.strip().upper()
            if clean_c in self.valid_codes and clean_c not in valid_predictions:
                valid_predictions.append(clean_c)
            if len(valid_predictions) >= 3:
                break
                
        return valid_predictions

