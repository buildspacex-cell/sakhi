"""Tests for kala.graph — in-memory graph primitives and schema validation."""

from __future__ import annotations

from kala.graph.core import (
    build_graph_from_enrichment,
    create_edge,
    create_node,
    reason_about_graph,
)
from kala.graph.schema import (
    VALID_KINDS,
    VALID_RELATIONS,
    sanitize_kind,
    sanitize_relation,
)

# ---------------------------------------------------------------------------
# create_node
# ---------------------------------------------------------------------------


class TestCreateNode:
    def test_basic_node(self) -> None:
        node = create_node("theme", "morning routine")
        assert node["kind"] == "theme"
        assert node["label"] == "morning routine"
        assert node["data"] == {}
        assert "id" in node

    def test_node_with_data(self) -> None:
        node = create_node("goal", "meditate", data={"priority": "high"})
        assert node["data"] == {"priority": "high"}

    def test_node_ids_are_unique(self) -> None:
        n1 = create_node("theme", "a")
        n2 = create_node("theme", "b")
        assert n1["id"] != n2["id"]

    def test_none_data_becomes_empty_dict(self) -> None:
        node = create_node("theme", "x", data=None)
        assert node["data"] == {}


# ---------------------------------------------------------------------------
# create_edge
# ---------------------------------------------------------------------------


class TestCreateEdge:
    def test_basic_edge(self) -> None:
        src = create_node("theme", "a")
        dst = create_node("theme", "b")
        edge = create_edge(src, dst)
        assert edge["src"] == src["id"]
        assert edge["dst"] == dst["id"]
        assert edge["relation"] == "relates_to"

    def test_custom_relation(self) -> None:
        src = create_node("goal", "exercise")
        dst = create_node("value", "health")
        edge = create_edge(src, dst, relation="supports")
        assert edge["relation"] == "supports"


# ---------------------------------------------------------------------------
# build_graph_from_enrichment
# ---------------------------------------------------------------------------


class TestBuildGraphFromEnrichment:
    def test_empty_enrichment(self) -> None:
        graph = build_graph_from_enrichment({})
        assert len(graph["nodes"]) == 1  # reflection node
        assert graph["nodes"][0]["kind"] == "reflection"
        assert graph["edges"] == []

    def test_with_emotion(self) -> None:
        graph = build_graph_from_enrichment({
            "facets": {"emotion": "joy"},
            "meaning": "A good day",
        })
        assert len(graph["nodes"]) == 2  # reflection + emotion
        assert any(n["kind"] == "emotion" and n["label"] == "joy" for n in graph["nodes"])
        assert len(graph["edges"]) == 1
        assert graph["edges"][0]["relation"] == "influences"

    def test_with_themes(self) -> None:
        graph = build_graph_from_enrichment({
            "themes": ["work", "stress", "balance"],
        })
        assert len(graph["nodes"]) == 4  # reflection + 3 themes
        theme_nodes = [n for n in graph["nodes"] if n["kind"] == "theme"]
        assert len(theme_nodes) == 3
        assert all(e["relation"] == "relates_to" for e in graph["edges"])

    def test_with_emotion_and_themes(self) -> None:
        graph = build_graph_from_enrichment({
            "facets": {"emotion": "anxiety"},
            "themes": ["deadline"],
            "meaning": "Tight deadline approaching",
        })
        assert len(graph["nodes"]) == 3  # reflection + emotion + theme
        assert len(graph["edges"]) == 2

    def test_meaning_truncated_for_label(self) -> None:
        long_meaning = "x" * 100
        graph = build_graph_from_enrichment({"meaning": long_meaning})
        reflection = graph["nodes"][0]
        assert len(reflection["label"]) == 40
        assert reflection["data"]["meaning"] == long_meaning


# ---------------------------------------------------------------------------
# reason_about_graph
# ---------------------------------------------------------------------------


class TestReasonAboutGraph:
    def test_basic_reasoning(self) -> None:
        graph = build_graph_from_enrichment({
            "facets": {"emotion": "calm"},
            "themes": ["meditation", "morning"],
        })
        result = reason_about_graph(graph)
        assert result["dominant_theme"] == "meditation"
        assert result["emotion"] == "calm"
        assert result["graph_size"] == 4
        assert result["edge_count"] == 3

    def test_no_themes(self) -> None:
        graph = build_graph_from_enrichment({"facets": {"emotion": "happy"}})
        result = reason_about_graph(graph)
        assert result["dominant_theme"] is None
        assert result["emotion"] == "happy"

    def test_no_emotion(self) -> None:
        graph = build_graph_from_enrichment({"themes": ["growth"]})
        result = reason_about_graph(graph)
        assert result["dominant_theme"] == "growth"
        assert result["emotion"] is None

    def test_empty_graph(self) -> None:
        result = reason_about_graph({"nodes": [], "edges": []})
        assert result["dominant_theme"] is None
        assert result["emotion"] is None
        assert result["graph_size"] == 0
        assert result["edge_count"] == 0


# ---------------------------------------------------------------------------
# sanitize_kind
# ---------------------------------------------------------------------------


class TestSanitizeKind:
    def test_valid_kind(self) -> None:
        assert sanitize_kind("theme") == "theme"

    def test_unknown_kind_defaults(self) -> None:
        assert sanitize_kind("unknown_type") == "reflection"

    def test_empty_string_defaults(self) -> None:
        assert sanitize_kind("") == "reflection"

    def test_namespaced_kind(self) -> None:
        assert sanitize_kind("goal:primary") == "goal"

    def test_case_insensitive(self) -> None:
        assert sanitize_kind("THEME") == "theme"

    def test_whitespace_stripped(self) -> None:
        assert sanitize_kind("  emotion  ") == "emotion"

    def test_all_valid_kinds(self) -> None:
        for kind in VALID_KINDS:
            assert sanitize_kind(kind) == kind


# ---------------------------------------------------------------------------
# sanitize_relation
# ---------------------------------------------------------------------------


class TestSanitizeRelation:
    def test_valid_relation(self) -> None:
        assert sanitize_relation("supports") == "supports"

    def test_unknown_relation_defaults(self) -> None:
        assert sanitize_relation("unknown_rel") == "relates_to"

    def test_empty_string_defaults(self) -> None:
        assert sanitize_relation("") == "relates_to"

    def test_spaces_to_underscores(self) -> None:
        assert sanitize_relation("competes with") == "competes_with"

    def test_case_insensitive(self) -> None:
        assert sanitize_relation("BLOCKS") == "blocks"

    def test_all_valid_relations(self) -> None:
        for rel in VALID_RELATIONS:
            assert sanitize_relation(rel) == rel
