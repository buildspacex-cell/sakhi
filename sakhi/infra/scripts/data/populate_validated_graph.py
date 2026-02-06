"""
Populate Ayurvedic Knowledge Graph with validated, cited data.

This script reads validated data from JSON files (output of validate_ayurvedic_data.py)
and populates the ay_nodes and ay_edges tables with citations and confidence scores.

Usage:
    # After running validation:
    python -m sakhi.infra.scripts.data.populate_validated_graph

    # Or use original data if validation not yet run:
    python -m sakhi.infra.scripts.data.populate_validated_graph --use-original
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from sakhi.apps.api.core.db import exec as dbexec, q as dbfetch

LOGGER = logging.getLogger(__name__)

# Directory containing validated JSON files
VALIDATED_DIR = Path(__file__).parent / "validated"

# Import original data as fallback
from sakhi.infra.scripts.data.populate_ayurvedic_graph import (
    DOSHAS,
    QUALITIES,
    SEASONS,
    TIME_WINDOWS,
    FOODS,
    PRACTICES,
    SYMPTOMS,
)


# =============================================================================
# DATABASE OPERATIONS
# =============================================================================

async def clear_graph() -> None:
    """Clear existing graph data."""
    await dbexec("DELETE FROM ay_validation_log")
    await dbexec("DELETE FROM ay_edges")
    await dbexec("DELETE FROM ay_nodes")
    LOGGER.info("[PopulateGraph] Cleared existing graph data")


async def insert_node(
    kind: str,
    name: str,
    attrs: Dict[str, Any],
    name_sanskrit: Optional[str] = None,
    display_name: Optional[str] = None,
    citations: Optional[List[Dict]] = None,
    confidence: float = 1.0,
    extraction_method: str = "manual",
) -> int:
    """Insert a node with full metadata and return its ID."""
    result = await dbfetch(
        """
        INSERT INTO ay_nodes (kind, name, name_sanskrit, display_name, attrs, citations, confidence, extraction_method, validated_at, validated_by)
        VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb, $7, $8, NOW(), $9)
        ON CONFLICT (kind, name) DO UPDATE SET
            name_sanskrit = COALESCE(EXCLUDED.name_sanskrit, ay_nodes.name_sanskrit),
            display_name = COALESCE(EXCLUDED.display_name, ay_nodes.display_name),
            attrs = EXCLUDED.attrs,
            citations = EXCLUDED.citations,
            confidence = EXCLUDED.confidence,
            extraction_method = EXCLUDED.extraction_method,
            validated_at = NOW(),
            validated_by = EXCLUDED.validated_by,
            updated_at = NOW()
        RETURNING id
        """,
        kind,
        name,
        name_sanskrit,
        display_name or name.replace("_", " ").title(),
        json.dumps(attrs, ensure_ascii=False),
        json.dumps(citations or [], ensure_ascii=False),
        confidence,
        extraction_method,
        "llm:gpt-4o" if extraction_method == "llm_validated" else "system",
        one=True,
    )
    return result["id"] if result else 0


async def insert_edge(
    src_id: int,
    dst_id: int,
    rel: str,
    weight: float = 1.0,
    context: Optional[Dict] = None,
    citations: Optional[List[Dict]] = None,
    confidence: float = 1.0,
) -> None:
    """Insert an edge with optional context and citations."""
    await dbexec(
        """
        INSERT INTO ay_edges (src, dst, rel, weight, context, citations, confidence, extraction_method)
        VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb, $7, $8)
        ON CONFLICT DO NOTHING
        """,
        src_id,
        dst_id,
        rel,
        weight,
        json.dumps(context or {}, ensure_ascii=False),
        json.dumps(citations or [], ensure_ascii=False),
        confidence,
        "llm_validated" if citations else "manual",
    )


async def log_validation(
    node_id: int,
    status: str,
    original_data: Dict,
    corrected_data: Dict,
    llm_reasoning: str,
    citations_found: List[Dict],
    confidence: float,
    contradicts_source: bool,
) -> None:
    """Log validation result."""
    await dbexec(
        """
        INSERT INTO ay_validation_log
            (node_id, status, original_data, corrected_data, llm_reasoning, citations_found, confidence_score, contradicts_source, validated_by)
        VALUES ($1, $2, $3::jsonb, $4::jsonb, $5, $6::jsonb, $7, $8, $9)
        """,
        node_id,
        status,
        json.dumps(original_data, ensure_ascii=False),
        json.dumps(corrected_data, ensure_ascii=False),
        llm_reasoning,
        json.dumps(citations_found, ensure_ascii=False),
        confidence,
        contradicts_source,
        "llm:gpt-4o",
    )


# =============================================================================
# LOAD VALIDATED DATA
# =============================================================================

def load_validated_data(category: str) -> Optional[Dict[str, Any]]:
    """Load validated data from JSON file."""
    path = VALIDATED_DIR / f"{category}_validated.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None


def merge_with_original(validated: Dict, original_list: List[Dict], category: str) -> List[Dict]:
    """Merge validated data with original, using validated where available."""
    if not validated:
        return original_list

    # Create lookup by name
    validated_by_name = {e["name"]: e for e in validated.get("entries", [])}

    merged = []
    for orig in original_list:
        name = orig["name"]
        if name in validated_by_name:
            v = validated_by_name[name]
            merged.append({
                "name": name,
                "name_sanskrit": v.get("name_sanskrit"),
                "attrs": v.get("attrs", orig.get("attrs", {})),
                "citations": v.get("citations", []),
                "confidence": v.get("confidence", 1.0),
                "status": v.get("status", "validated"),
                "corrections": v.get("corrections", []),
                "reasoning": v.get("reasoning", ""),
                "contradicts_source": v.get("contradicts_source", False),
                "original": orig,
            })
        else:
            # Not validated yet, use original
            merged.append({
                "name": name,
                "name_sanskrit": None,
                "attrs": orig.get("attrs", {}),
                "citations": [],
                "confidence": 0.5,  # Lower confidence for unvalidated
                "status": "unvalidated",
                "corrections": [],
                "reasoning": "",
                "contradicts_source": False,
                "original": orig,
            })

    return merged


# =============================================================================
# POPULATION FUNCTIONS
# =============================================================================

async def populate_base_nodes() -> Dict[str, Dict[str, int]]:
    """Populate doshas, qualities, seasons, time windows - these don't need LLM validation."""
    node_map: Dict[str, Dict[str, int]] = {
        "dosha": {},
        "quality": {},
        "season": {},
        "time_window": {},
    }

    # Doshas
    for d in DOSHAS:
        node_id = await insert_node(
            "dosha",
            d["name"],
            d["attrs"],
            name_sanskrit={
                "vata": "वात (Vāta)",
                "pitta": "पित्त (Pitta)",
                "kapha": "कफ (Kapha)",
            }.get(d["name"]),
            display_name=d["attrs"].get("display_name"),
            citations=[{
                "source": "charaka_samhita",
                "chapter": "sutrasthana.1",
                "text": "Fundamental dosha as described in Charaka Samhita"
            }],
            confidence=1.0,
            extraction_method="scholarly",
        )
        node_map["dosha"][d["name"]] = node_id

    # Qualities (Gunas)
    for q in QUALITIES:
        node_id = await insert_node(
            "quality",
            q["name"],
            q["attrs"],
            citations=[{
                "source": "charaka_samhita",
                "chapter": "sutrasthana.1",
                "text": "Twenty qualities (Vimshati Gunas) as enumerated in classical texts"
            }],
            confidence=1.0,
            extraction_method="scholarly",
        )
        node_map["quality"][q["name"]] = node_id

    # Seasons
    for s in SEASONS:
        node_id = await insert_node(
            "season",
            s["name"],
            s["attrs"],
            citations=[{
                "source": "ashtanga_hridaya",
                "chapter": "sutrasthana.3",
                "text": "Ritucharya - seasonal regimen"
            }],
            confidence=1.0,
            extraction_method="scholarly",
        )
        node_map["season"][s["name"]] = node_id

    # Time windows
    for t in TIME_WINDOWS:
        node_id = await insert_node(
            "time_window",
            t["name"],
            t["attrs"],
            citations=[{
                "source": "ashtanga_hridaya",
                "chapter": "sutrasthana.2",
                "text": "Dinacharya - daily routine and dosha predominance by time"
            }],
            confidence=1.0,
            extraction_method="scholarly",
        )
        node_map["time_window"][t["name"]] = node_id

    return node_map


async def populate_foods(node_map: Dict[str, Dict[str, int]], use_original: bool = False) -> int:
    """Populate food nodes with validated data."""
    # Load validated data if available
    validated = None if use_original else load_validated_data("foods")
    foods = merge_with_original(validated, FOODS, "foods")

    node_map["food"] = {}
    count = 0

    for food in foods:
        node_id = await insert_node(
            "food",
            food["name"],
            food["attrs"],
            name_sanskrit=food.get("name_sanskrit"),
            citations=food.get("citations", []),
            confidence=food.get("confidence", 0.5),
            extraction_method="llm_validated" if food.get("citations") else "manual",
        )
        node_map["food"][food["name"]] = node_id

        # Log validation if we have it
        if food.get("status") != "unvalidated":
            await log_validation(
                node_id=node_id,
                status=food.get("status", "validated"),
                original_data=food.get("original", {}),
                corrected_data=food.get("attrs", {}),
                llm_reasoning=food.get("reasoning", ""),
                citations_found=food.get("citations", []),
                confidence=food.get("confidence", 1.0),
                contradicts_source=food.get("contradicts_source", False),
            )

        count += 1

    LOGGER.info(f"[PopulateGraph] Populated {count} foods")
    return count


async def populate_practices(node_map: Dict[str, Dict[str, int]], use_original: bool = False) -> int:
    """Populate practice nodes with validated data."""
    validated = None if use_original else load_validated_data("practices")
    practices = merge_with_original(validated, PRACTICES, "practices")

    node_map["practice"] = {}
    count = 0

    for practice in practices:
        node_id = await insert_node(
            "practice",
            practice["name"],
            practice["attrs"],
            name_sanskrit=practice.get("name_sanskrit"),
            citations=practice.get("citations", []),
            confidence=practice.get("confidence", 0.5),
            extraction_method="llm_validated" if practice.get("citations") else "manual",
        )
        node_map["practice"][practice["name"]] = node_id

        if practice.get("status") != "unvalidated":
            await log_validation(
                node_id=node_id,
                status=practice.get("status", "validated"),
                original_data=practice.get("original", {}),
                corrected_data=practice.get("attrs", {}),
                llm_reasoning=practice.get("reasoning", ""),
                citations_found=practice.get("citations", []),
                confidence=practice.get("confidence", 1.0),
                contradicts_source=practice.get("contradicts_source", False),
            )

        count += 1

    LOGGER.info(f"[PopulateGraph] Populated {count} practices")
    return count


async def populate_symptoms(node_map: Dict[str, Dict[str, int]], use_original: bool = False) -> int:
    """Populate symptom nodes with validated data."""
    validated = None if use_original else load_validated_data("symptoms")
    symptoms = merge_with_original(validated, SYMPTOMS, "symptoms")

    node_map["symptom"] = {}
    count = 0

    for symptom in symptoms:
        node_id = await insert_node(
            "symptom",
            symptom["name"],
            symptom["attrs"],
            name_sanskrit=symptom.get("name_sanskrit"),
            citations=symptom.get("citations", []),
            confidence=symptom.get("confidence", 0.5),
            extraction_method="llm_validated" if symptom.get("citations") else "manual",
        )
        node_map["symptom"][symptom["name"]] = node_id

        if symptom.get("status") != "unvalidated":
            await log_validation(
                node_id=node_id,
                status=symptom.get("status", "validated"),
                original_data=symptom.get("original", {}),
                corrected_data=symptom.get("attrs", {}),
                llm_reasoning=symptom.get("reasoning", ""),
                citations_found=symptom.get("citations", []),
                confidence=symptom.get("confidence", 1.0),
                contradicts_source=symptom.get("contradicts_source", False),
            )

        count += 1

    LOGGER.info(f"[PopulateGraph] Populated {count} symptoms")
    return count


async def populate_edges(node_map: Dict[str, Dict[str, int]]) -> int:
    """Populate all edges between nodes."""
    edge_count = 0

    # Load validated data for citations on edges
    foods_validated = load_validated_data("foods")
    foods_by_name = {}
    if foods_validated:
        foods_by_name = {e["name"]: e for e in foods_validated.get("entries", [])}

    practices_validated = load_validated_data("practices")
    practices_by_name = {}
    if practices_validated:
        practices_by_name = {e["name"]: e for e in practices_validated.get("entries", [])}

    # Food → Dosha edges
    for f in FOODS:
        food_id = node_map["food"].get(f["name"])
        if not food_id:
            continue

        attrs = f["attrs"]
        validated = foods_by_name.get(f["name"], {})
        citations = validated.get("citations", [])
        confidence = validated.get("confidence", 0.8)

        # Use validated attrs if available
        v_attrs = validated.get("attrs", attrs)

        for dosha in v_attrs.get("pacifies", attrs.get("pacifies", [])):
            dosha_id = node_map["dosha"].get(dosha)
            if dosha_id:
                await insert_edge(
                    food_id, dosha_id, "PACIFIES",
                    weight=0.8,
                    citations=citations,
                    confidence=confidence,
                )
                edge_count += 1

        for dosha in v_attrs.get("aggravates", attrs.get("aggravates", [])):
            dosha_id = node_map["dosha"].get(dosha)
            if dosha_id:
                await insert_edge(
                    food_id, dosha_id, "AGGRAVATES",
                    weight=0.7,
                    citations=citations,
                    confidence=confidence,
                )
                edge_count += 1

    # Practice → Dosha edges
    for p in PRACTICES:
        practice_id = node_map["practice"].get(p["name"])
        if not practice_id:
            continue

        attrs = p["attrs"]
        validated = practices_by_name.get(p["name"], {})
        citations = validated.get("citations", [])
        confidence = validated.get("confidence", 0.8)

        v_attrs = validated.get("attrs", attrs)

        for dosha in v_attrs.get("pacifies", attrs.get("pacifies", [])):
            dosha_id = node_map["dosha"].get(dosha)
            if dosha_id:
                await insert_edge(
                    practice_id, dosha_id, "PACIFIES",
                    weight=0.85,
                    citations=citations,
                    confidence=confidence,
                )
                edge_count += 1

        # Practice → Time window
        practice_time = v_attrs.get("optimal_time", attrs.get("time"))
        if practice_time and practice_time not in ("any", None):
            time_id = node_map["time_window"].get(practice_time)
            if time_id:
                await insert_edge(
                    practice_id, time_id, "OPTIMAL_TIME",
                    weight=0.9,
                    confidence=confidence,
                )
                edge_count += 1

    # Symptom → Dosha edges
    for s in SYMPTOMS:
        symptom_id = node_map["symptom"].get(s["name"])
        if not symptom_id:
            continue

        dosha = s["attrs"].get("indicates")
        if dosha:
            dosha_id = node_map["dosha"].get(dosha)
            if dosha_id:
                await insert_edge(
                    symptom_id, dosha_id, "INDICATES",
                    weight=0.8,
                )
                edge_count += 1

    # Season → Dosha edges
    for s in SEASONS:
        season_id = node_map["season"].get(s["name"])
        if not season_id:
            continue

        dosha = s["attrs"].get("dominant_dosha")
        if dosha:
            dosha_id = node_map["dosha"].get(dosha)
            if dosha_id:
                amp = s["attrs"].get("amplification", 1.0)
                await insert_edge(
                    season_id, dosha_id, "AMPLIFIES",
                    weight=amp,
                    citations=[{
                        "source": "ashtanga_hridaya",
                        "chapter": "sutrasthana.3",
                        "text": "Ritucharya describes seasonal dosha variations"
                    }],
                    confidence=1.0,
                )
                edge_count += 1

    # Time window → Dosha edges
    for t in TIME_WINDOWS:
        time_id = node_map["time_window"].get(t["name"])
        if not time_id:
            continue

        dosha = t["attrs"].get("dominant_dosha")
        if dosha:
            dosha_id = node_map["dosha"].get(dosha)
            if dosha_id:
                await insert_edge(
                    time_id, dosha_id, "DOMINANT_DURING",
                    weight=0.7,
                    citations=[{
                        "source": "ashtanga_hridaya",
                        "chapter": "sutrasthana.2",
                        "text": "Dosha clock - dinacharya"
                    }],
                    confidence=1.0,
                )
                edge_count += 1

    # Quality → Dosha edges
    for q in QUALITIES:
        quality_id = node_map["quality"].get(q["name"])
        if not quality_id:
            continue

        effect = q["attrs"].get("effect", "")
        if "aggravates_" in effect:
            dosha = effect.replace("aggravates_", "")
            dosha_id = node_map["dosha"].get(dosha)
            if dosha_id:
                await insert_edge(quality_id, dosha_id, "AGGRAVATES", weight=0.6)
                edge_count += 1
        elif "reduces_" in effect:
            dosha = effect.replace("reduces_", "")
            dosha_id = node_map["dosha"].get(dosha)
            if dosha_id:
                await insert_edge(quality_id, dosha_id, "REDUCES", weight=0.6)
                edge_count += 1

    LOGGER.info(f"[PopulateGraph] Populated {edge_count} edges")
    return edge_count


# =============================================================================
# MAIN
# =============================================================================

async def run_population(clear_first: bool = True, use_original: bool = False) -> Dict[str, Any]:
    """Main population function."""
    if clear_first:
        await clear_graph()

    # Base nodes (doshas, qualities, seasons, time windows)
    node_map = await populate_base_nodes()

    # Foods, practices, symptoms (with validation data if available)
    food_count = await populate_foods(node_map, use_original)
    practice_count = await populate_practices(node_map, use_original)
    symptom_count = await populate_symptoms(node_map, use_original)

    # Edges
    edge_count = await populate_edges(node_map)

    # Calculate totals
    node_counts = {kind: len(names) for kind, names in node_map.items()}
    total_nodes = sum(node_counts.values())

    result = {
        "status": "success",
        "node_counts": node_counts,
        "total_nodes": total_nodes,
        "edge_count": edge_count,
        "used_validated_data": not use_original,
        "validated_files_found": {
            "foods": (VALIDATED_DIR / "foods_validated.json").exists(),
            "practices": (VALIDATED_DIR / "practices_validated.json").exists(),
            "symptoms": (VALIDATED_DIR / "symptoms_validated.json").exists(),
        },
    }

    LOGGER.info(
        "[PopulateGraph] Complete: %s nodes, %s edges (validated=%s)",
        total_nodes,
        edge_count,
        not use_original,
    )

    return result


async def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Populate Ayurvedic knowledge graph")
    parser.add_argument("--use-original", action="store_true", help="Use original data instead of validated")
    parser.add_argument("--no-clear", action="store_true", help="Don't clear existing data")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    result = await run_population(
        clear_first=not args.no_clear,
        use_original=args.use_original,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
