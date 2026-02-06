"""
Validate and enrich Ayurvedic knowledge graph data using LLM.

Phase 1: Validate existing data against Ayurvedic source texts.

This script:
1. Takes existing food, practice, and symptom data
2. Uses LLM to validate properties against Ayurvedic knowledge
3. Adds citations from classical texts (Charaka, Ashtanga Hridaya, etc.)
4. Flags contradictions and corrections
5. Outputs validated JSON for database population

Usage:
    python -m sakhi.infra.scripts.data.validate_ayurvedic_data --category foods
    python -m sakhi.infra.scripts.data.validate_ayurvedic_data --category practices
    python -m sakhi.infra.scripts.data.validate_ayurvedic_data --category symptoms
    python -m sakhi.infra.scripts.data.validate_ayurvedic_data --all
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# LLM client - using OpenAI-compatible interface
try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

LOGGER = logging.getLogger(__name__)

# Output directory for validated data
OUTPUT_DIR = Path(__file__).parent / "validated"
OUTPUT_DIR.mkdir(exist_ok=True)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Citation:
    """A citation from an Ayurvedic source text."""
    source: str              # charaka_samhita, ashtanga_hridaya, etc.
    chapter: str             # e.g., "sutrasthana.27"
    shloka: Optional[str]    # e.g., "3-5" or "12"
    text: Optional[str]      # Relevant quote (Sanskrit or English)
    translation: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of validating an entry."""
    name: str
    kind: str
    status: str              # validated, corrected, flagged, rejected
    original_data: Dict[str, Any]
    validated_data: Dict[str, Any]
    citations: List[Citation] = field(default_factory=list)
    corrections: List[str] = field(default_factory=list)
    confidence: float = 1.0
    llm_reasoning: str = ""
    sanskrit_name: Optional[str] = None
    contradicts_source: bool = False


# =============================================================================
# EXISTING DATA (from populate_ayurvedic_graph.py)
# =============================================================================

# Import existing data - we'll validate and enrich this
from sakhi.infra.scripts.data.populate_ayurvedic_graph import (
    FOODS,
    PRACTICES,
    SYMPTOMS,
    DOSHAS,
    QUALITIES,
    SEASONS,
    TIME_WINDOWS,
)


# =============================================================================
# VALIDATION PROMPTS
# =============================================================================

FOOD_VALIDATION_PROMPT = """You are an expert Ayurvedic scholar with deep knowledge of classical texts including Charaka Samhita, Ashtanga Hridaya, Sushruta Samhita, and Bhavaprakasha Nighantu.

Your task is to validate and enrich the following food entry from our Ayurvedic knowledge base.

FOOD ENTRY TO VALIDATE:
```json
{entry_json}
```

Please analyze this entry and provide:

1. **Validation Status**: Is this entry accurate according to classical Ayurvedic texts?
   - "validated" = Correct as-is
   - "corrected" = Minor corrections needed
   - "flagged" = Significant issues, needs review
   - "rejected" = Fundamentally incorrect

2. **Sanskrit Name**: The traditional Sanskrit name for this food (if known)

3. **Property Validation**:
   - Rasa (taste): Is the listed taste correct? (madhura/amla/lavana/katu/tikta/kashaya)
   - Virya (potency): Is warming/cooling correct? (ushna/shita)
   - Vipaka (post-digestive effect): What is the vipaka? (madhura/amla/katu)
   - Guna (qualities): What are the main qualities? (guru/laghu/snigdha/ruksha/etc.)

4. **Dosha Effects**: Are the "pacifies" and "aggravates" lists accurate?

5. **Citations**: Provide specific references from classical texts:
   - Source (charaka_samhita, ashtanga_hridaya, bhavaprakasha, etc.)
   - Chapter (e.g., "sutrasthana.27" for Annapana Vidhi chapter)
   - Shloka numbers if known
   - Brief relevant quote or paraphrase

6. **Corrections**: List any corrections needed

7. **Confidence Score**: 0.0-1.0 based on how certain you are

Respond in this exact JSON format:
```json
{{
  "status": "validated|corrected|flagged|rejected",
  "sanskrit_name": "name or null",
  "validated_properties": {{
    "rasa": "taste",
    "virya": "warming|cooling",
    "vipaka": "madhura|amla|katu",
    "guna": ["quality1", "quality2"],
    "pacifies": ["dosha1"],
    "aggravates": ["dosha2"],
    "best_season": "season or all",
    "special_notes": "any important notes"
  }},
  "citations": [
    {{
      "source": "text_code",
      "chapter": "section.chapter_num",
      "shloka": "shloka_range or null",
      "text": "brief quote or paraphrase"
    }}
  ],
  "corrections": ["correction1", "correction2"],
  "confidence": 0.85,
  "reasoning": "Brief explanation of your analysis"
}}
```

Be precise and cite specific chapters. For foods, the key references are:
- Charaka Samhita Sutrasthana Chapter 27 (Annapana Vidhi)
- Ashtanga Hridaya Sutrasthana Chapters 5-8 (Dravadravya, Anna Svarupa)
- Bhavaprakasha Madhya Khanda (Nighantu section)"""


PRACTICE_VALIDATION_PROMPT = """You are an expert Ayurvedic scholar with deep knowledge of classical texts.

Your task is to validate and enrich the following practice/routine entry from our Ayurvedic knowledge base.

PRACTICE ENTRY TO VALIDATE:
```json
{entry_json}
```

Please analyze this entry and provide:

1. **Validation Status**: Is this entry accurate according to classical Ayurvedic texts?
   - "validated" = Correct as-is
   - "corrected" = Minor corrections needed
   - "flagged" = Significant issues, needs review
   - "rejected" = Fundamentally incorrect

2. **Sanskrit Name**: The traditional Sanskrit name for this practice (if applicable)

3. **Property Validation**:
   - Type: Is the categorization correct? (yoga, pranayama, meditation, dinacharya, exercise)
   - Intensity: Is the intensity rating appropriate?
   - Dosha effects: Are the "pacifies" effects accurate?
   - Optimal time: Is the recommended time correct?
   - Duration: Is the suggested duration appropriate?

4. **Citations**: Provide specific references from classical texts:
   - For dinacharya: Ashtanga Hridaya Sutrasthana Chapter 2-3
   - For yoga/pranayama: Classical yoga texts and Ayurvedic adaptations
   - For seasonal practices: Ritucharya chapters

5. **Corrections**: List any corrections needed

6. **Confidence Score**: 0.0-1.0

Respond in this exact JSON format:
```json
{{
  "status": "validated|corrected|flagged|rejected",
  "sanskrit_name": "name or null",
  "validated_properties": {{
    "type": "category",
    "intensity": "gentle|moderate|active|intense|restorative",
    "pacifies": ["dosha1"],
    "duration_min": 15,
    "optimal_time": "time_window",
    "contraindications": ["condition1"],
    "special_notes": "any important notes"
  }},
  "citations": [
    {{
      "source": "text_code",
      "chapter": "section.chapter_num",
      "shloka": "shloka_range or null",
      "text": "brief quote or paraphrase"
    }}
  ],
  "corrections": ["correction1"],
  "confidence": 0.85,
  "reasoning": "Brief explanation"
}}
```"""


SYMPTOM_VALIDATION_PROMPT = """You are an expert Ayurvedic scholar with deep knowledge of classical texts.

Your task is to validate and enrich the following symptom entry from our Ayurvedic knowledge base.

SYMPTOM ENTRY TO VALIDATE:
```json
{entry_json}
```

Please analyze this entry and provide:

1. **Validation Status**: Is this entry accurate according to classical Ayurvedic texts?

2. **Sanskrit Name**: The traditional Ayurvedic term for this symptom (if known)

3. **Property Validation**:
   - Indicates: Is the dosha association correct?
   - Could this symptom indicate multiple dosha imbalances?
   - Severity: Is the severity rating appropriate?
   - Category: Is the categorization correct?

4. **Citations**: Provide specific references:
   - For symptoms: Nidana Sthana chapters in Charaka/Sushruta
   - For mental symptoms: Unmada/Manas chapters

5. **Nuances**: Are there conditions where this symptom might indicate a different dosha?

Respond in this exact JSON format:
```json
{{
  "status": "validated|corrected|flagged|rejected",
  "sanskrit_name": "name or null",
  "validated_properties": {{
    "primary_indicates": "dosha",
    "secondary_indicates": ["other_doshas"],
    "severity": "mild|moderate|severe",
    "category": "category",
    "associated_symptoms": ["symptom1"],
    "special_notes": "contextual notes"
  }},
  "citations": [
    {{
      "source": "text_code",
      "chapter": "section.chapter_num",
      "shloka": "shloka_range or null",
      "text": "brief quote or paraphrase"
    }}
  ],
  "corrections": ["correction1"],
  "confidence": 0.85,
  "reasoning": "Brief explanation"
}}
```"""


# =============================================================================
# LLM CLIENT
# =============================================================================

class AyurvedicValidator:
    """Validates Ayurvedic data using LLM."""

    def __init__(self, model: str = "gpt-4o"):
        self.model = model
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable required")

        if AsyncOpenAI is None:
            raise ImportError("openai package required: pip install openai")

        self.client = AsyncOpenAI(api_key=api_key)

    async def validate_entry(
        self,
        entry: Dict[str, Any],
        kind: str,
        prompt_template: str,
    ) -> ValidationResult:
        """Validate a single entry using LLM."""
        entry_json = json.dumps(entry, indent=2)
        prompt = prompt_template.format(entry_json=entry_json)

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert Ayurvedic scholar. Always respond with valid JSON."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Lower temperature for more consistent output
                max_tokens=2000,
            )

            content = response.choices[0].message.content
            # Extract JSON from response (handle markdown code blocks)
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            result_data = json.loads(content.strip())

            # Build ValidationResult
            citations = [
                Citation(
                    source=c.get("source", ""),
                    chapter=c.get("chapter", ""),
                    shloka=c.get("shloka"),
                    text=c.get("text"),
                )
                for c in result_data.get("citations", [])
            ]

            return ValidationResult(
                name=entry["name"],
                kind=kind,
                status=result_data.get("status", "flagged"),
                original_data=entry,
                validated_data=result_data.get("validated_properties", entry.get("attrs", {})),
                citations=citations,
                corrections=result_data.get("corrections", []),
                confidence=result_data.get("confidence", 0.5),
                llm_reasoning=result_data.get("reasoning", ""),
                sanskrit_name=result_data.get("sanskrit_name"),
                contradicts_source=len(result_data.get("corrections", [])) > 2,
            )

        except json.JSONDecodeError as e:
            LOGGER.error(f"Failed to parse LLM response for {entry['name']}: {e}")
            return ValidationResult(
                name=entry["name"],
                kind=kind,
                status="flagged",
                original_data=entry,
                validated_data=entry.get("attrs", {}),
                confidence=0.0,
                llm_reasoning=f"Parse error: {e}",
            )
        except Exception as e:
            LOGGER.error(f"LLM validation failed for {entry['name']}: {e}")
            return ValidationResult(
                name=entry["name"],
                kind=kind,
                status="flagged",
                original_data=entry,
                validated_data=entry.get("attrs", {}),
                confidence=0.0,
                llm_reasoning=f"Error: {e}",
            )

    async def validate_foods(self, foods: List[Dict]) -> List[ValidationResult]:
        """Validate all food entries."""
        results = []
        for i, food in enumerate(foods):
            LOGGER.info(f"Validating food {i+1}/{len(foods)}: {food['name']}")
            result = await self.validate_entry(food, "food", FOOD_VALIDATION_PROMPT)
            results.append(result)
            # Rate limiting
            await asyncio.sleep(0.5)
        return results

    async def validate_practices(self, practices: List[Dict]) -> List[ValidationResult]:
        """Validate all practice entries."""
        results = []
        for i, practice in enumerate(practices):
            LOGGER.info(f"Validating practice {i+1}/{len(practices)}: {practice['name']}")
            result = await self.validate_entry(practice, "practice", PRACTICE_VALIDATION_PROMPT)
            results.append(result)
            await asyncio.sleep(0.5)
        return results

    async def validate_symptoms(self, symptoms: List[Dict]) -> List[ValidationResult]:
        """Validate all symptom entries."""
        results = []
        for i, symptom in enumerate(symptoms):
            LOGGER.info(f"Validating symptom {i+1}/{len(symptoms)}: {symptom['name']}")
            result = await self.validate_entry(symptom, "symptom", SYMPTOM_VALIDATION_PROMPT)
            results.append(result)
            await asyncio.sleep(0.5)
        return results


# =============================================================================
# OUTPUT GENERATION
# =============================================================================

def results_to_json(results: List[ValidationResult]) -> Dict[str, Any]:
    """Convert validation results to JSON structure."""
    entries = []
    for r in results:
        entry = {
            "name": r.name,
            "name_sanskrit": r.sanskrit_name,
            "kind": r.kind,
            "status": r.status,
            "confidence": r.confidence,
            "attrs": r.validated_data,
            "citations": [
                {
                    "source": c.source,
                    "chapter": c.chapter,
                    "shloka": c.shloka,
                    "text": c.text,
                }
                for c in r.citations
            ],
            "corrections": r.corrections,
            "reasoning": r.llm_reasoning,
            "contradicts_source": r.contradicts_source,
            "original": r.original_data,
        }
        entries.append(entry)

    return {
        "validated_at": datetime.utcnow().isoformat(),
        "model": "gpt-4o",
        "total_entries": len(entries),
        "summary": {
            "validated": len([r for r in results if r.status == "validated"]),
            "corrected": len([r for r in results if r.status == "corrected"]),
            "flagged": len([r for r in results if r.status == "flagged"]),
            "rejected": len([r for r in results if r.status == "rejected"]),
        },
        "entries": entries,
    }


def save_results(results: List[ValidationResult], category: str) -> Path:
    """Save validation results to JSON file."""
    data = results_to_json(results)
    output_path = OUTPUT_DIR / f"{category}_validated.json"
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    LOGGER.info(f"Saved {len(results)} {category} to {output_path}")
    return output_path


# =============================================================================
# BATCH VALIDATION (for cost management)
# =============================================================================

async def validate_batch(
    validator: AyurvedicValidator,
    items: List[Dict],
    kind: str,
    prompt_template: str,
    batch_size: int = 5,
) -> List[ValidationResult]:
    """Validate items in batches with progress tracking."""
    results = []
    total = len(items)

    for i in range(0, total, batch_size):
        batch = items[i:i + batch_size]
        LOGGER.info(f"Processing {kind} batch {i//batch_size + 1}/{(total + batch_size - 1)//batch_size}")

        batch_results = await asyncio.gather(*[
            validator.validate_entry(item, kind, prompt_template)
            for item in batch
        ])
        results.extend(batch_results)

        # Longer pause between batches to avoid rate limits
        if i + batch_size < total:
            await asyncio.sleep(2)

    return results


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Validate Ayurvedic knowledge graph data")
    parser.add_argument("--category", choices=["foods", "practices", "symptoms"], help="Category to validate")
    parser.add_argument("--all", action="store_true", help="Validate all categories")
    parser.add_argument("--limit", type=int, help="Limit number of entries (for testing)")
    parser.add_argument("--model", default="gpt-4o", help="LLM model to use")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    validator = AyurvedicValidator(model=args.model)

    if args.all or args.category == "foods":
        foods = FOODS[:args.limit] if args.limit else FOODS
        LOGGER.info(f"Validating {len(foods)} foods...")
        results = await validate_batch(
            validator, foods, "food", FOOD_VALIDATION_PROMPT, batch_size=3
        )
        save_results(results, "foods")

    if args.all or args.category == "practices":
        practices = PRACTICES[:args.limit] if args.limit else PRACTICES
        LOGGER.info(f"Validating {len(practices)} practices...")
        results = await validate_batch(
            validator, practices, "practice", PRACTICE_VALIDATION_PROMPT, batch_size=3
        )
        save_results(results, "practices")

    if args.all or args.category == "symptoms":
        symptoms = SYMPTOMS[:args.limit] if args.limit else SYMPTOMS
        LOGGER.info(f"Validating {len(symptoms)} symptoms...")
        results = await validate_batch(
            validator, symptoms, "symptom", SYMPTOM_VALIDATION_PROMPT, batch_size=3
        )
        save_results(results, "symptoms")

    LOGGER.info("Validation complete!")


if __name__ == "__main__":
    asyncio.run(main())
