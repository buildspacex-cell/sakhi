"""
Unit tests for kala vector math utilities.

Tests cosine similarity, vector parsing, normalization,
recency weighting, and diversity filtering.
"""

from datetime import datetime, timedelta, timezone

from kala.memory.vector_math import (
    cosine_similarity,
    diversity_filter,
    normalize_vector,
    parse_vector,
    recency_weight,
)

# =============================================================================
# cosine_similarity tests
# =============================================================================


class TestCosineSimilarity:
    """Tests for cosine similarity computation."""

    def test_identical_vectors(self):
        v = [1.0, 2.0, 3.0]
        assert abs(cosine_similarity(v, v) - 1.0) < 1e-6

    def test_orthogonal_vectors(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert abs(cosine_similarity(a, b)) < 1e-6

    def test_opposite_vectors(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert abs(cosine_similarity(a, b) - (-1.0)) < 1e-6

    def test_empty_vectors(self):
        assert cosine_similarity([], [1.0, 2.0]) == 0.0
        assert cosine_similarity([1.0, 2.0], []) == 0.0
        assert cosine_similarity([], []) == 0.0

    def test_zero_vector(self):
        assert cosine_similarity([0.0, 0.0], [1.0, 2.0]) == 0.0

    def test_similar_vectors(self):
        a = [1.0, 2.0, 3.0]
        b = [1.1, 2.1, 3.1]
        sim = cosine_similarity(a, b)
        assert sim > 0.99  # Very similar


# =============================================================================
# parse_vector tests
# =============================================================================


class TestParseVector:
    """Tests for vector parsing from various formats."""

    def test_from_list(self):
        result = parse_vector([1.0, 2.0, 3.0])
        assert result == [1.0, 2.0, 3.0]

    def test_from_string(self):
        result = parse_vector("[0.1, 0.2, 0.3]")
        assert len(result) == 3
        assert abs(result[0] - 0.1) < 1e-6

    def test_none_returns_empty(self):
        assert parse_vector(None) == []

    def test_empty_string_array(self):
        assert parse_vector("[]") == []

    def test_empty_list(self):
        assert parse_vector([]) == []

    def test_integer_list(self):
        result = parse_vector([1, 2, 3])
        assert result == [1.0, 2.0, 3.0]

    def test_invalid_string(self):
        assert parse_vector("not a vector") == []

    def test_string_without_brackets(self):
        assert parse_vector("1.0, 2.0") == []


# =============================================================================
# normalize_vector tests
# =============================================================================


class TestNormalizeVector:
    """Tests for vector normalization (pad/trim to target dim)."""

    def test_correct_dimension_unchanged(self):
        vec = [0.1] * 4
        result = normalize_vector(vec, dim=4)
        assert len(result) == 4
        assert result == vec

    def test_shorter_vector_padded(self):
        vec = [1.0, 2.0]
        result = normalize_vector(vec, dim=4)
        assert len(result) == 4
        assert result == [1.0, 2.0, 0.0, 0.0]

    def test_longer_vector_trimmed(self):
        vec = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = normalize_vector(vec, dim=3)
        assert result == [1.0, 2.0, 3.0]

    def test_nested_list_unwrapped(self):
        vec = [[1.0, 2.0, 3.0]]  # Common embedding API format
        result = normalize_vector(vec, dim=3)
        assert result == [1.0, 2.0, 3.0]

    def test_non_list_returns_zeros(self):
        result = normalize_vector("not a vector", dim=3)
        assert result == [0.0, 0.0, 0.0]

    def test_none_returns_zeros(self):
        result = normalize_vector(None, dim=3)
        assert result == [0.0, 0.0, 0.0]

    def test_default_dim_is_1536(self):
        result = normalize_vector(None)
        assert len(result) == 1536


# =============================================================================
# recency_weight tests
# =============================================================================


class TestRecencyWeight:
    """Tests for exponential-decay recency weighting."""

    def test_recent_timestamp_high_weight(self):
        now = datetime.now(timezone.utc)
        weight = recency_weight(now)
        assert weight > 0.99

    def test_old_timestamp_low_weight(self):
        old = datetime.now(timezone.utc) - timedelta(days=90)
        weight = recency_weight(old, halflife_days=45)
        # 90 days with 45-day halflife = 2 half-lives = 0.25
        assert abs(weight - 0.25) < 0.05

    def test_halflife_correct(self):
        one_halflife = datetime.now(timezone.utc) - timedelta(days=45)
        weight = recency_weight(one_halflife, halflife_days=45)
        assert abs(weight - 0.5) < 0.05

    def test_none_returns_one(self):
        assert recency_weight(None) == 1.0

    def test_string_timestamp(self):
        ts = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        weight = recency_weight(ts)
        assert weight > 0.99

    def test_naive_timestamp(self):
        """Naive datetime (no tzinfo) should still work."""
        naive = datetime.utcnow()
        weight = recency_weight(naive)
        assert weight > 0.99

    def test_invalid_string_returns_one(self):
        assert recency_weight("not-a-date") == 1.0


# =============================================================================
# diversity_filter tests
# =============================================================================


class TestDiversityFilter:
    """Tests for diversity-based deduplication."""

    def test_diverse_items_pass_through(self):
        items = [
            (0.9, {"id": 1, "vec": [1.0, 0.0]}),
            (0.8, {"id": 2, "vec": [0.0, 1.0]}),
            (0.7, {"id": 3, "vec": [-1.0, 0.0]}),
        ]
        result = diversity_filter(items, top_k=3)
        assert len(result) == 3

    def test_duplicate_items_filtered(self):
        items = [
            (0.9, {"id": 1, "vec": [1.0, 0.0, 0.0]}),
            (0.8, {"id": 2, "vec": [0.999, 0.01, 0.0]}),  # Near-duplicate of #1
            (0.7, {"id": 3, "vec": [0.0, 1.0, 0.0]}),     # Diverse
        ]
        result = diversity_filter(items, top_k=2)
        ids = [r["id"] for r in result]
        assert 1 in ids
        assert 3 in ids  # Should pick diverse item over duplicate

    def test_top_k_limit(self):
        items = [
            (0.9, {"id": 1, "vec": [1.0, 0.0]}),
            (0.8, {"id": 2, "vec": [0.0, 1.0]}),
        ]
        result = diversity_filter(items, top_k=1)
        assert len(result) == 1

    def test_fills_remaining_slots(self):
        """If not enough diverse items, backfill with non-diverse ones."""
        # All very similar vectors
        items = [
            (0.9, {"id": 1, "vec": [1.0, 0.0]}),
            (0.8, {"id": 2, "vec": [0.99, 0.01]}),
            (0.7, {"id": 3, "vec": [0.98, 0.02]}),
        ]
        result = diversity_filter(items, top_k=3)
        assert len(result) == 3  # Backfilled even though duplicates

    def test_custom_threshold(self):
        items = [
            (0.9, {"id": 1, "vec": [1.0, 0.0]}),
            (0.8, {"id": 2, "vec": [0.95, 0.05]}),  # Slightly different
        ]
        # Low threshold = more filtering
        result = diversity_filter(items, top_k=2, threshold=0.5)
        assert len(result) == 2  # Both still pass at 0.5

    def test_empty_input(self):
        result = diversity_filter([], top_k=5)
        assert result == []
