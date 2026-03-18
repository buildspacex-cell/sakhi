from datetime import UTC, datetime

import pytest

from sakhi.apps.api.services.continuity import cross_topic


def test_normalize_correlation_row_carries_related_topic_depth():
    row = {
        "combined_score": 0.58,
        "temporal_score": 0.61,
        "semantic_score": 0.44,
        "facet_score": 0.33,
        "directional_score": 0.29,
        "correlation_types": ["temporal", "semantic"],
        "shared_facets": ["boundaries"],
        "overlap_windows": [],
        "source_window_start": "2026-01-01T00:00:00+00:00",
        "source_window_end": "2026-03-10T00:00:00+00:00",
        "computed_at": "2026-03-10T10:00:00+00:00",
    }
    related_topic = {
        "label": "Career",
        "selected_count": 11,
        "arc": {"end_ts": "2026-03-09T00:00:00+00:00"},
    }

    payload = cross_topic._normalize_correlation_row(
        row,
        related_anchor="career",
        related_topic=related_topic,
    )

    assert payload["related_topic_label"] == "Career"
    assert payload["related_selected_count"] == 11
    assert payload["related_end_ts"] == "2026-03-09T00:00:00+00:00"


def test_whole_story_uses_related_depth_from_correlation_payload():
    now = datetime(2026, 3, 10, 12, 0, tzinfo=UTC)
    selected_topic = {
        "anchor": "sakhi",
        "selected_count": 10,
        "primary_selected_count": 10,
        "surface": {"detail_allowed": True},
        "arc": {"end_ts": "2026-03-10T11:00:00+00:00"},
        "entry_tags": {},
    }
    related_topic = {
        "anchor": "career",
        "selected_count": 7,
        "primary_selected_count": 7,
        "surface": {"detail_allowed": True},
        "arc": {"end_ts": "2026-03-10T10:00:00+00:00"},
        "entry_tags": {},
    }
    correlations = [
        {
            "related_topic_key": "career",
            "related_topic_label": "Career",
            "related_selected_count": 7,
            "related_end_ts": "2026-03-10T10:00:00+00:00",
            "combined_score": 0.52,
            "temporal_score": 0.64,
            "semantic_score": 0.41,
            "facet_score": 0.35,
            "directional_score": 0.31,
            "correlation_types": ["temporal", "semantic"],
            "overlap_pairs": 5,
        }
    ]

    cross_context = cross_topic._build_cross_context_signal(
        selected_topic=selected_topic,
        selected_anchor="sakhi",
        topics_map={"sakhi": selected_topic, "career": related_topic},
        correlations=correlations,
        now=now,
    )
    whole_story = cross_topic._build_whole_story_signal(
        selected_topic=selected_topic,
        cross_context=cross_context,
        topics_map={"sakhi": selected_topic, "career": related_topic},
    )

    assert cross_context["ready"] is True
    assert cross_context["correlated_selected_count"] == 7
    assert whole_story is not None
    assert whole_story["ready"] is True
    assert whole_story["selected_topics"] == ["sakhi", "career"]


def test_semantic_overlap_prefers_vector_similarity_when_available():
    moments_a = [
        {
            "source_ref": "journal:11111111-1111-4111-8111-111111111111",
            "snippet": "work stress",
        }
    ]
    moments_b = [
        {
            "source_ref": "journal:22222222-2222-4222-8222-222222222222",
            "snippet": "career anxiety",
        }
    ]
    lexical_score = cross_topic._semantic_overlap_score(
        moments_a,
        moments_b,
        embedding_lookup=None,
    )
    vector_score = cross_topic._semantic_overlap_score(
        moments_a,
        moments_b,
        embedding_lookup={
            "11111111-1111-4111-8111-111111111111": [1.0, 0.0, 0.0],
            "22222222-2222-4222-8222-222222222222": [0.95, 0.05, 0.0],
        },
    )
    assert lexical_score == 0.0
    assert vector_score > 0.9


def test_included_moments_resolves_tags_with_timestamp_variants_and_source_ref():
    topic = {
        "arc": {
            "event_refs": [
                {
                    "day": 5,
                    "ts": "2026-03-05T10:00:00+00:00",
                    "source_ref": "journal:33333333-3333-4333-8333-333333333333",
                    "excerpt": "Founder update.",
                }
            ]
        },
        "entry_tags": {
            "5|2026-03-05T10:00:00Z": {
                "source_ref": "journal:33333333-3333-4333-8333-333333333333",
                "facet": "founder_alignment",
                "stance": "toward",
            }
        },
    }

    moments = cross_topic._included_moments(topic)

    assert len(moments) == 1
    assert moments[0]["facet"] == "founder_alignment"
    assert moments[0]["stance"] == "toward"


def test_is_cache_fresh_uses_threshold_profile_ttl():
    now = datetime(2026, 3, 10, 12, 0, tzinfo=UTC)
    fresh = {"computed_at": "2026-03-10T07:00:01+00:00"}
    stale = {"computed_at": "2026-03-10T05:59:59+00:00"}

    assert cross_topic._is_cache_fresh(fresh, now=now) is True
    assert cross_topic._is_cache_fresh(stale, now=now) is False


@pytest.mark.asyncio
async def test_invalidate_person_cross_topic_cache_deletes_both_tables(
    monkeypatch: pytest.MonkeyPatch,
):
    calls: list[tuple[str, tuple[object, ...]]] = []

    async def fake_dbexec(sql: str, *args):
        calls.append((sql, args))

    monkeypatch.setattr(cross_topic, "dbexec", fake_dbexec)

    await cross_topic.invalidate_person_cross_topic_cache(
        person_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    )

    assert len(calls) == 2
    assert "continuity_topic_correlations" in calls[0][0]
    assert "continuity_life_dimensions" in calls[1][0]
    assert calls[0][1] == ("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",)
    assert calls[1][1] == ("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",)


@pytest.mark.asyncio
async def test_invalidate_person_cross_topic_cache_continues_on_db_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    calls: list[str] = []

    async def fake_dbexec(sql: str, *args):
        calls.append(sql)
        if "continuity_topic_correlations" in sql:
            raise RuntimeError("boom")

    monkeypatch.setattr(cross_topic, "dbexec", fake_dbexec)

    await cross_topic.invalidate_person_cross_topic_cache(
        person_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    )

    assert len(calls) == 2
    assert "continuity_topic_correlations" in calls[0]
    assert "continuity_life_dimensions" in calls[1]


@pytest.mark.asyncio
async def test_load_or_compute_correlations_warms_all_pairs(
    monkeypatch: pytest.MonkeyPatch,
):
    async def fake_dbfetch(sql: str, *args, **kwargs):
        if "FROM continuity_topic_correlations" in sql:
            return []
        if "FROM journal_embeddings" in sql:
            return []
        return []

    upserts: list[tuple[str, str]] = []

    async def fake_upsert(**kwargs):
        metrics = kwargs["metrics"]
        upserts.append((str(metrics["topic_key_a"]), str(metrics["topic_key_b"])))

    monkeypatch.setattr(cross_topic, "dbfetch", fake_dbfetch)
    monkeypatch.setattr(cross_topic, "_upsert_correlation_row", fake_upsert)

    def _topic(
        anchor: str, ts: str, day: int, stance: str, facet: str
    ) -> dict[str, object]:
        key = f"{day}|{ts}"
        return {
            "anchor": anchor,
            "label": anchor.title(),
            "selected_count": 8,
            "surface": {"detail_allowed": True},
            "arc": {
                "end_ts": ts,
                "event_refs": [
                    {
                        "day": day,
                        "ts": ts,
                        "source_ref": f"journal:{anchor}-{day}",
                        "excerpt": f"{anchor} moment {day}",
                    }
                ],
            },
            "entry_tags": {
                key: {
                    "facet": facet,
                    "stance": stance,
                    "source_ref": f"journal:{anchor}-{day}",
                }
            },
        }

    topics_map = {
        "sakhi": _topic("sakhi", "2026-03-01T10:00:00+00:00", 1, "toward", "focus"),
        "career": _topic(
            "career", "2026-03-02T10:00:00+00:00", 2, "away", "boundaries"
        ),
        "family": _topic(
            "family", "2026-03-03T10:00:00+00:00", 3, "toward", "caregiving"
        ),
    }
    selected_topic = topics_map["sakhi"]

    rows = await cross_topic._load_or_compute_correlations(
        person_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        selected_anchor="sakhi",
        selected_topic=selected_topic,
        topics_map=topics_map,
        window_start="2026-01-01T00:00:00+00:00",
        window_end="2026-03-10T00:00:00+00:00",
        now=datetime(2026, 3, 10, 12, 0, tzinfo=UTC),
    )

    assert sorted(set(upserts)) == [
        ("career", "family"),
        ("career", "sakhi"),
        ("family", "sakhi"),
    ]
    assert len(rows) == 2
    assert {row["related_topic_key"] for row in rows} == {"career", "family"}


# ---------------------------------------------------------------------------
# _pair_key / _topic_pairs
# ---------------------------------------------------------------------------


def test_pair_key_is_canonical():
    assert cross_topic._pair_key("career", "sakhi") == ("career", "sakhi")
    assert cross_topic._pair_key("sakhi", "career") == ("career", "sakhi")
    assert cross_topic._pair_key("z", "a") == ("a", "z")


def test_topic_pairs_generates_all_combinations():
    pairs = cross_topic._topic_pairs(["sakhi", "career", "family"])
    assert sorted(pairs) == [
        ("career", "family"),
        ("career", "sakhi"),
        ("family", "sakhi"),
    ]


def test_topic_pairs_empty_when_fewer_than_two():
    assert cross_topic._topic_pairs([]) == []
    assert cross_topic._topic_pairs(["sakhi"]) == []


# ---------------------------------------------------------------------------
# _journal_id_from_source_ref
# ---------------------------------------------------------------------------


def test_journal_id_from_source_ref_parses_uuid():
    uid = "11111111-1111-4111-8111-111111111111"
    assert cross_topic._journal_id_from_source_ref(f"journal:{uid}") == uid
    assert cross_topic._journal_id_from_source_ref(uid) == uid


def test_journal_id_from_source_ref_rejects_non_journal_prefix():
    assert cross_topic._journal_id_from_source_ref("entry:abc") is None


def test_journal_id_from_source_ref_rejects_non_uuid_token():
    assert cross_topic._journal_id_from_source_ref("journal:not-a-uuid") is None
    assert cross_topic._journal_id_from_source_ref("") is None
    assert cross_topic._journal_id_from_source_ref(None) is None


# ---------------------------------------------------------------------------
# _coerce_ts
# ---------------------------------------------------------------------------


def test_coerce_ts_accepts_datetime_naive():
    from datetime import UTC, datetime

    naive = datetime(2026, 3, 10, 12, 0)
    result = cross_topic._coerce_ts(naive)
    assert result is not None
    assert result.tzinfo is not None


def test_coerce_ts_accepts_iso_string_with_z():
    result = cross_topic._coerce_ts("2026-03-10T12:00:00Z")
    assert result is not None
    assert result.year == 2026


def test_coerce_ts_returns_none_for_blank():
    assert cross_topic._coerce_ts("") is None
    assert cross_topic._coerce_ts(None) is None
    assert cross_topic._coerce_ts(42) is None


# ---------------------------------------------------------------------------
# _centroid / _cosine_similarity
# ---------------------------------------------------------------------------


def test_centroid_single_vector():
    assert cross_topic._centroid([[1.0, 2.0, 3.0]]) == [1.0, 2.0, 3.0]


def test_centroid_two_vectors():
    result = cross_topic._centroid([[1.0, 0.0], [0.0, 1.0]])
    assert result == [0.5, 0.5]


def test_centroid_empty_returns_none():
    assert cross_topic._centroid([]) is None


def test_centroid_skips_mismatched_length():
    result = cross_topic._centroid([[1.0, 2.0], [1.0, 2.0, 3.0]])
    # Only the first valid-length vector is used
    assert result is not None


def test_cosine_similarity_parallel_vectors():
    score = cross_topic._cosine_similarity([1.0, 0.0], [1.0, 0.0])
    assert score == pytest.approx(1.0)


def test_cosine_similarity_orthogonal_vectors():
    score = cross_topic._cosine_similarity([1.0, 0.0], [0.0, 1.0])
    assert score == pytest.approx(0.0, abs=1e-9)


def test_cosine_similarity_antiparallel_vectors():
    score = cross_topic._cosine_similarity([1.0, 0.0], [-1.0, 0.0])
    assert score == pytest.approx(-1.0)


def test_cosine_similarity_different_lengths_returns_none():
    assert cross_topic._cosine_similarity([1.0], [1.0, 2.0]) is None


def test_cosine_similarity_zero_vector_returns_none():
    assert cross_topic._cosine_similarity([0.0, 0.0], [1.0, 0.0]) is None


# ---------------------------------------------------------------------------
# _semantic_overlap_score_from_vectors
# ---------------------------------------------------------------------------


def test_semantic_overlap_from_vectors_high_similarity():
    uid_a = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    uid_b = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
    moments_a = [{"source_ref": f"journal:{uid_a}"}]
    moments_b = [{"source_ref": f"journal:{uid_b}"}]
    lookup = {uid_a: [1.0, 0.0], uid_b: [0.99, 0.01]}
    score = cross_topic._semantic_overlap_score_from_vectors(
        moments_a=moments_a, moments_b=moments_b, embedding_lookup=lookup
    )
    assert score is not None
    assert score > 0.98


def test_semantic_overlap_from_vectors_returns_none_when_no_vectors():
    moments_a = [{"source_ref": "journal:11111111-1111-4111-8111-111111111111"}]
    moments_b = [{"source_ref": "journal:22222222-2222-4222-8222-222222222222"}]
    # lookup has nothing for these IDs
    score = cross_topic._semantic_overlap_score_from_vectors(
        moments_a=moments_a, moments_b=moments_b, embedding_lookup={}
    )
    assert score is None


# ---------------------------------------------------------------------------
# _temporal_overlap_details
# ---------------------------------------------------------------------------


def test_temporal_overlap_within_window():
    moments_a = [{"ts": "2026-03-01T10:00:00+00:00"}]
    moments_b = [{"ts": "2026-03-03T10:00:00+00:00"}]  # 2 days apart
    score, pairs, windows = cross_topic._temporal_overlap_details(
        moments_a, moments_b, max_days=7
    )
    assert score > 0.0
    assert pairs == 1
    assert len(windows) == 1


def test_temporal_overlap_outside_window():
    moments_a = [{"ts": "2026-01-01T00:00:00+00:00"}]
    moments_b = [{"ts": "2026-03-01T00:00:00+00:00"}]  # 59 days apart
    score, pairs, windows = cross_topic._temporal_overlap_details(
        moments_a, moments_b, max_days=7
    )
    assert score == 0.0
    assert pairs == 0
    assert windows == []


def test_temporal_overlap_empty_moments():
    score, pairs, windows = cross_topic._temporal_overlap_details([], [], max_days=7)
    assert score == 0.0 and pairs == 0 and windows == []


def test_temporal_overlap_none_timestamps_skipped():
    moments_a = [{"ts": None}, {"ts": "2026-03-01T10:00:00+00:00"}]
    moments_b = [{"ts": "2026-03-02T10:00:00+00:00"}]
    score, pairs, windows = cross_topic._temporal_overlap_details(
        moments_a, moments_b, max_days=7
    )
    assert pairs == 1


def test_temporal_overlap_score_capped_at_one():
    # More overlap pairs than baseline → score stays ≤ 1.0
    ts_a = [{"ts": f"2026-03-0{i}T10:00:00+00:00"} for i in range(1, 5)]
    ts_b = [{"ts": f"2026-03-0{i}T12:00:00+00:00"} for i in range(1, 5)]
    score, _, _ = cross_topic._temporal_overlap_details(ts_a, ts_b, max_days=7)
    assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# _facet_overlap_score
# ---------------------------------------------------------------------------


def test_facet_overlap_shared_facets():
    moments_a = [{"facet": "boundaries"}, {"facet": "focus"}]
    moments_b = [{"facet": "boundaries"}, {"facet": "caregiving"}]
    score, shared = cross_topic._facet_overlap_score(moments_a, moments_b)
    assert score == pytest.approx(1 / 3)  # 1 shared out of 3 unique
    assert shared == ["boundaries"]


def test_facet_overlap_no_shared():
    moments_a = [{"facet": "focus"}]
    moments_b = [{"facet": "caregiving"}]
    score, shared = cross_topic._facet_overlap_score(moments_a, moments_b)
    assert score == 0.0
    assert shared == []


def test_facet_overlap_empty_moments():
    assert cross_topic._facet_overlap_score([], []) == (0.0, [])
    assert cross_topic._facet_overlap_score([{"facet": "focus"}], []) == (0.0, [])


def test_facet_overlap_missing_facet_field():
    moments_a = [{"snippet": "no facet here"}]
    moments_b = [{"snippet": "also no facet"}]
    score, shared = cross_topic._facet_overlap_score(moments_a, moments_b)
    assert score == 0.0


# ---------------------------------------------------------------------------
# _pearson
# ---------------------------------------------------------------------------


def test_pearson_perfect_positive_correlation():
    assert cross_topic._pearson([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == pytest.approx(
        1.0
    )


def test_pearson_perfect_negative_correlation():
    assert cross_topic._pearson([1.0, 2.0, 3.0], [3.0, 2.0, 1.0]) == pytest.approx(
        -1.0
    )


def test_pearson_no_variance_returns_zero():
    # All same values → denominator is 0
    assert cross_topic._pearson([1.0, 1.0, 1.0], [2.0, 2.0, 2.0]) == 0.0


def test_pearson_single_element_returns_zero():
    assert cross_topic._pearson([1.0], [1.0]) == 0.0


# ---------------------------------------------------------------------------
# _weekly_stance_series
# ---------------------------------------------------------------------------


def test_weekly_stance_series_buckets_by_week():
    moments = [
        {"ts": "2026-03-02T10:00:00+00:00", "stance": "toward"},
        {"ts": "2026-03-03T10:00:00+00:00", "stance": "toward"},
        {"ts": "2026-03-10T10:00:00+00:00", "stance": "away"},
    ]
    series = cross_topic._weekly_stance_series(moments)
    assert len(series) == 2
    # Week with two "toward" → mean 1.0
    first_week = "2026-09"  # week 9
    values = list(series.values())
    assert any(v == pytest.approx(1.0) for v in values)
    assert any(v == pytest.approx(-1.0) for v in values)


def test_weekly_stance_series_ignores_no_stance():
    moments = [
        {"ts": "2026-03-02T10:00:00+00:00", "stance": ""},
    ]
    series = cross_topic._weekly_stance_series(moments)
    values = list(series.values())
    assert values == [pytest.approx(0.0)]


# ---------------------------------------------------------------------------
# _directional_alignment_score
# ---------------------------------------------------------------------------


def test_directional_alignment_correlated():
    # Both topics show toward in week 9, away in week 10 → perfect positive Pearson → score = 1.0
    moments_a = [
        {"ts": "2026-03-02T10:00:00+00:00", "stance": "toward"},  # week 09
        {"ts": "2026-03-10T10:00:00+00:00", "stance": "away"},    # week 10
    ]
    moments_b = [
        {"ts": "2026-03-02T11:00:00+00:00", "stance": "toward"},  # week 09
        {"ts": "2026-03-10T11:00:00+00:00", "stance": "away"},    # week 10
    ]
    score = cross_topic._directional_alignment_score(moments_a, moments_b)
    assert score == pytest.approx(1.0)


def test_directional_alignment_no_common_weeks_returns_zero():
    moments_a = [{"ts": "2026-01-05T10:00:00+00:00", "stance": "toward"}]
    moments_b = [{"ts": "2026-03-09T10:00:00+00:00", "stance": "away"}]
    score = cross_topic._directional_alignment_score(moments_a, moments_b)
    assert score == 0.0


# ---------------------------------------------------------------------------
# _should_surface_dimension
# ---------------------------------------------------------------------------


def test_should_surface_dimension_blocked_by_topic_count():
    assert (
        cross_topic._should_surface_dimension(
            level=0.8, topic_count=1, entry_count=10, financial=False
        )
        is False
    )


def test_should_surface_dimension_blocked_by_entry_count():
    assert (
        cross_topic._should_surface_dimension(
            level=0.8, topic_count=3, entry_count=2, financial=False
        )
        is False
    )


def test_should_surface_dimension_high_level():
    # level=0.8 >= 0.5 threshold
    assert (
        cross_topic._should_surface_dimension(
            level=0.8, topic_count=3, entry_count=5, financial=False
        )
        is True
    )


def test_should_surface_dimension_low_level():
    # level=0.1 <= 0.3 threshold (resourced)
    assert (
        cross_topic._should_surface_dimension(
            level=0.1, topic_count=3, entry_count=5, financial=False
        )
        is True
    )


def test_should_surface_dimension_financial_below_threshold():
    # financial needs >= 0.65
    assert (
        cross_topic._should_surface_dimension(
            level=0.5, topic_count=3, entry_count=5, financial=True
        )
        is False
    )


def test_should_surface_dimension_financial_above_threshold():
    assert (
        cross_topic._should_surface_dimension(
            level=0.7, topic_count=3, entry_count=5, financial=True
        )
        is True
    )


# ---------------------------------------------------------------------------
# _direction_for_level
# ---------------------------------------------------------------------------


def test_direction_for_level_pressured():
    assert cross_topic._direction_for_level(0.8) == "pressured"


def test_direction_for_level_resourced():
    assert cross_topic._direction_for_level(0.1) == "resourced"


def test_direction_for_level_neutral():
    assert cross_topic._direction_for_level(0.4) == "neutral"


# ---------------------------------------------------------------------------
# _build_cross_context_signal edge cases
# ---------------------------------------------------------------------------


def test_build_cross_context_signal_blocks_when_primary_is_not_dominant():
    selected_topic = {
        "surface": {"detail_allowed": False, "mirror_allowed": True},
        "selected_count": 20,
        "primary_selected_count": 20,
        "arc": {"end_ts": "2026-03-10T12:00:00+00:00"},
    }
    signal = cross_topic._build_cross_context_signal(
        selected_topic=selected_topic,
        selected_anchor="sakhi",
        topics_map={
            "sakhi": selected_topic,
            "career": {
                "surface": {"detail_allowed": True, "mirror_allowed": True},
                "selected_count": 16,
                "primary_selected_count": 16,
                "arc": {"end_ts": "2026-03-09T12:00:00+00:00"},
            },
        },
        correlations=[],
        now=datetime(2026, 3, 10, 12, 0, tzinfo=UTC),
    )
    assert signal["ready"] is False
    assert signal["reason"] == "insufficient_depth"


def test_build_cross_context_signal_threads_inactive_when_stale():
    now = datetime(2026, 3, 10, 12, 0, tzinfo=UTC)
    selected_topic = {
        "surface": {"detail_allowed": True},
        "selected_count": 10,
        "arc": {"end_ts": "2025-01-01T00:00:00+00:00"},  # very old
    }
    correlations = [
        {
            "related_topic_key": "career",
            "related_topic_label": "Career",
            "related_selected_count": 8,
            "related_end_ts": "2025-01-02T00:00:00+00:00",  # also old
            "combined_score": 0.55,
            "temporal_score": 0.6,
            "semantic_score": 0.4,
            "facet_score": 0.3,
            "directional_score": 0.3,
            "correlation_types": ["temporal"],
            "overlap_pairs": 4,
        }
    ]
    signal = cross_topic._build_cross_context_signal(
        selected_topic=selected_topic,
        selected_anchor="sakhi",
        topics_map={"sakhi": selected_topic, "career": {"selected_count": 8}},
        correlations=correlations,
        now=now,
    )
    assert signal["ready"] is False
    assert signal["reason"] == "threads_inactive"


def test_build_cross_context_signal_insufficient_overlap_score():
    now = datetime(2026, 3, 10, 12, 0, tzinfo=UTC)
    selected_topic = {
        "surface": {"detail_allowed": True},
        "selected_count": 10,
        "arc": {"end_ts": "2026-03-09T00:00:00+00:00"},
    }
    correlations = [
        {
            "related_topic_key": "career",
            "related_topic_label": "Career",
            "related_selected_count": 8,
            "related_end_ts": "2026-03-08T00:00:00+00:00",
            "combined_score": 0.10,  # below min_combined_score=0.35
            "temporal_score": 0.1,
            "semantic_score": 0.1,
            "facet_score": 0.0,
            "directional_score": 0.0,
            "correlation_types": [],
            "overlap_pairs": 1,
        }
    ]
    signal = cross_topic._build_cross_context_signal(
        selected_topic=selected_topic,
        selected_anchor="sakhi",
        topics_map={"sakhi": selected_topic, "career": {"selected_count": 8}},
        correlations=correlations,
        now=now,
    )
    assert signal["ready"] is False
    assert signal["reason"] == "insufficient_overlap"


def test_build_cross_context_signal_allows_dominant_mirror_safe_primary():
    now = datetime(2026, 3, 10, 12, 0, tzinfo=UTC)
    selected_topic = {
        "surface": {"detail_allowed": False, "mirror_allowed": True},
        "selected_count": 18,
        "primary_selected_count": 18,
        "arc": {"end_ts": "2026-03-09T00:00:00+00:00"},
    }
    related_topic = {
        "surface": {"detail_allowed": True, "mirror_allowed": True},
        "selected_count": 7,
        "primary_selected_count": 7,
        "arc": {"end_ts": "2026-03-08T00:00:00+00:00"},
    }
    correlations = [
        {
            "related_topic_key": "career",
            "related_topic_label": "Career",
            "related_selected_count": 7,
            "related_end_ts": "2026-03-08T00:00:00+00:00",
            "combined_score": 0.52,
            "temporal_score": 0.61,
            "semantic_score": 0.42,
            "facet_score": 0.31,
            "directional_score": 0.3,
            "correlation_types": ["temporal"],
            "overlap_pairs": 4,
        }
    ]

    signal = cross_topic._build_cross_context_signal(
        selected_topic=selected_topic,
        selected_anchor="sakhi",
        topics_map={"sakhi": selected_topic, "career": related_topic},
        correlations=correlations,
        now=now,
    )

    assert signal["ready"] is True
    assert signal["correlated_topic_key"] == "career"


# ---------------------------------------------------------------------------
# _build_whole_story_signal edge cases
# ---------------------------------------------------------------------------


def test_build_whole_story_signal_not_ready_propagates_cross_context_reason():
    selected_topic = {"anchor": "sakhi", "selected_count": 10}
    cross_ctx = {
        "ready": False,
        "reason": "threads_inactive",
        "correlated_topic_key": "career",
        "correlated_selected_count": 8,
        "correlation_score": 0.2,
    }
    ws = cross_topic._build_whole_story_signal(
        selected_topic=selected_topic,
        cross_context=cross_ctx,
        topics_map={"sakhi": selected_topic, "career": {"selected_count": 8}},
    )
    assert ws is not None
    assert ws["ready"] is False
    assert ws["reason"] == "threads_inactive"


def test_build_whole_story_signal_insufficient_primary_depth():
    selected_topic = {"anchor": "sakhi", "selected_count": 4, "primary_selected_count": 4}
    cross_ctx = {
        "ready": True,
        "reason": "ready",
        "correlated_topic_key": "career",
        "correlated_selected_count": 8,
        "correlation_score": 0.55,
    }
    ws = cross_topic._build_whole_story_signal(
        selected_topic=selected_topic,
        cross_context=cross_ctx,
        topics_map={"sakhi": selected_topic, "career": {"selected_count": 8}},
    )
    assert ws is not None
    assert ws["ready"] is False
    assert ws["reason"] == "insufficient_depth"


def test_build_whole_story_signal_insufficient_related_depth():
    selected_topic = {"anchor": "sakhi", "selected_count": 12, "primary_selected_count": 12}
    cross_ctx = {
        "ready": True,
        "reason": "ready",
        "correlated_topic_key": "career",
        "correlated_selected_count": 3,  # below min 5
        "correlation_score": 0.55,
    }
    ws = cross_topic._build_whole_story_signal(
        selected_topic=selected_topic,
        cross_context=cross_ctx,
        topics_map={"sakhi": selected_topic, "career": {"selected_count": 3}},
    )
    assert ws is not None
    assert ws["ready"] is False
    assert ws["reason"] == "insufficient_depth"


def test_build_whole_story_signal_dedupes_shared_moments_across_topics():
    shared_ref = "journal:11111111-1111-4111-8111-111111111111"
    selected_topic = {
        "anchor": "sakhi",
        "selected_count": 12,
        "primary_selected_count": 12,
        "arc": {
            "event_refs": [
                {
                    "day": 1,
                    "ts": "2026-03-01T10:00:00+00:00",
                    "source_ref": shared_ref,
                    "excerpt": "Family pressure spilled into Sakhi work.",
                },
                {
                    "day": 2,
                    "ts": "2026-03-02T10:00:00+00:00",
                    "source_ref": "journal:22222222-2222-4222-8222-222222222222",
                    "excerpt": "Investor planning.",
                },
            ]
        },
        "entry_tags": {
            "1|2026-03-01T10:00:00+00:00": {
                "source_ref": shared_ref,
                "facet": "focus",
                "stance": "toward",
            },
            "2|2026-03-02T10:00:00+00:00": {
                "source_ref": "journal:22222222-2222-4222-8222-222222222222",
                "facet": "focus",
                "stance": "toward",
            },
        },
    }
    related_topic = {
        "anchor": "family",
        "selected_count": 5,
        "primary_selected_count": 5,
        "arc": {
            "event_refs": [
                {
                    "day": 1,
                    "ts": "2026-03-01T10:00:00+00:00",
                    "source_ref": shared_ref,
                    "excerpt": "Family pressure spilled into Sakhi work.",
                },
                {
                    "day": 3,
                    "ts": "2026-03-03T10:00:00+00:00",
                    "source_ref": "journal:33333333-3333-4333-8333-333333333333",
                    "excerpt": "Care conversation.",
                },
            ]
        },
        "entry_tags": {
            "1|2026-03-01T10:00:00+00:00": {
                "source_ref": shared_ref,
                "facet": "caregiving",
                "stance": "away",
            },
            "3|2026-03-03T10:00:00+00:00": {
                "source_ref": "journal:33333333-3333-4333-8333-333333333333",
                "facet": "caregiving",
                "stance": "toward",
            },
        },
    }
    cross_ctx = {
        "ready": True,
        "reason": "ready",
        "correlated_topic_key": "family",
        "correlated_selected_count": 5,
        "correlation_score": 0.61,
    }

    ws = cross_topic._build_whole_story_signal(
        selected_topic=selected_topic,
        cross_context=cross_ctx,
        topics_map={"sakhi": selected_topic, "family": related_topic},
    )

    assert ws is not None
    assert ws["selected_count_total"] == 3


# ---------------------------------------------------------------------------
# _compute_life_dimensions (pure computation; no DB)
# ---------------------------------------------------------------------------


def _make_topic_with_moments(anchor: str, moments: list[dict]) -> dict:
    event_refs = [
        {"ts": m["ts"], "source_ref": f"journal:{anchor}-{i}", "excerpt": m.get("excerpt", "")}
        for i, m in enumerate(moments)
    ]
    entry_tags = {}
    for i, m in enumerate(moments):
        key = f"journal:{anchor}-{i}"
        entry_tags[key] = {
            "facet": m.get("facet", ""),
            "stance": m.get("stance", ""),
            "source_ref": key,
        }
    return {
        "anchor": anchor,
        "selected_count": len(moments),
        "surface": {"detail_allowed": True},
        "arc": {"end_ts": moments[-1]["ts"] if moments else "", "event_refs": event_refs},
        "entry_tags": entry_tags,
    }


def test_compute_life_dimensions_time_availability_high_when_many_topics_active():
    now = datetime(2026, 3, 10, 12, 0, tzinfo=UTC)
    # 4 topics each with 5 recent moments → time_level = min(1.0, (4/4)*0.6 + (20/20)*0.4) = 1.0
    topics_map = {
        k: _make_topic_with_moments(
            k,
            [{"ts": "2026-03-09T10:00:00+00:00", "stance": "", "facet": k} for _ in range(5)],
        )
        for k in ("sakhi", "career", "family", "health")
    }
    dims = cross_topic._compute_life_dimensions(topics_map=topics_map, now=now)
    time_dim = dims["time_availability"]
    assert time_dim["level"] == pytest.approx(1.0)
    assert time_dim["direction"] == "pressured"


def test_compute_life_dimensions_financial_pressure_detected():
    now = datetime(2026, 3, 10, 12, 0, tzinfo=UTC)
    # enough money-term mentions to cross 0.65 threshold (need >= 8*0.65=5.2 → 6 rows)
    moments = [
        {"ts": "2026-03-09T10:00:00+00:00", "stance": "", "facet": "money", "excerpt": "budget pressure"}
        for _ in range(6)
    ] + [
        {"ts": "2026-03-08T10:00:00+00:00", "stance": "", "facet": "cost", "excerpt": "runway concern"}
        for _ in range(2)
    ]
    topics_map = {
        "startup": _make_topic_with_moments("startup", moments),
        "career": _make_topic_with_moments(
            "career",
            [{"ts": "2026-03-08T10:00:00+00:00", "stance": "", "facet": "budget", "excerpt": "salary"}],
        ),
    }
    dims = cross_topic._compute_life_dimensions(topics_map=topics_map, now=now)
    fin = dims["financial_pressure"]
    # financial level = min(1.0, financial_rows / 8)
    assert fin["level"] > 0.0


def test_compute_life_dimensions_emotional_bandwidth_away_pressure():
    now = datetime(2026, 3, 10, 12, 0, tzinfo=UTC)
    # All "away" stance → emotional_level = 1.0 → pressured
    moments = [
        {"ts": "2026-03-09T10:00:00+00:00", "stance": "away", "facet": "focus"}
        for _ in range(5)
    ]
    topics_map = {
        "sakhi": _make_topic_with_moments("sakhi", moments),
        "career": _make_topic_with_moments(
            "career",
            [{"ts": "2026-03-08T10:00:00+00:00", "stance": "away", "facet": "boundaries"}],
        ),
    }
    dims = cross_topic._compute_life_dimensions(topics_map=topics_map, now=now)
    emotional = dims["emotional_bandwidth"]
    assert emotional["level"] == pytest.approx(1.0)
    assert emotional["direction"] == "pressured"


def test_compute_life_dimensions_emotional_bandwidth_toward_resourced():
    now = datetime(2026, 3, 10, 12, 0, tzinfo=UTC)
    # All "toward" stance → emotional_level = 0.0 → resourced
    moments = [
        {"ts": "2026-03-09T10:00:00+00:00", "stance": "toward", "facet": "focus"}
        for _ in range(4)
    ]
    topics_map = {
        "sakhi": _make_topic_with_moments("sakhi", moments),
        "career": _make_topic_with_moments(
            "career",
            [{"ts": "2026-03-08T10:00:00+00:00", "stance": "toward", "facet": "growth"}],
        ),
    }
    dims = cross_topic._compute_life_dimensions(topics_map=topics_map, now=now)
    emotional = dims["emotional_bandwidth"]
    assert emotional["level"] == pytest.approx(0.0)
    assert emotional["direction"] == "resourced"


# ---------------------------------------------------------------------------
# _resolve_entry_tag fallback by source_ref
# ---------------------------------------------------------------------------


def test_resolve_entry_tag_matches_by_source_ref_value_scan():
    uid = "44444444-4444-4444-8444-444444444444"
    entry_tags = {
        "some-other-key": {
            "source_ref": f"journal:{uid}",
            "facet": "founder_alignment",
            "stance": "toward",
        }
    }
    ref = {"source_ref": f"journal:{uid}", "ts": "2026-03-05T10:00:00+00:00", "day": 5}
    result = cross_topic._resolve_entry_tag(entry_tags=entry_tags, ref=ref)
    assert result["facet"] == "founder_alignment"


def test_resolve_entry_tag_returns_empty_when_no_match():
    entry_tags = {"1|2026-03-01T10:00:00Z": {"facet": "focus", "stance": "toward"}}
    ref = {"source_ref": "journal:99999999-9999-4999-8999-999999999999", "day": 99}
    result = cross_topic._resolve_entry_tag(entry_tags=entry_tags, ref=ref)
    assert result == {}


# ---------------------------------------------------------------------------
# _parse_json_array / _parse_json_object
# ---------------------------------------------------------------------------


def test_parse_json_array_handles_list_passthrough():
    assert cross_topic._parse_json_array(["a", "b"]) == ["a", "b"]


def test_parse_json_array_parses_json_string():
    assert cross_topic._parse_json_array('["temporal", "semantic"]') == [
        "temporal",
        "semantic",
    ]


def test_parse_json_array_returns_empty_on_bad_input():
    assert cross_topic._parse_json_array("not-json") == []
    assert cross_topic._parse_json_array(None) == []


def test_parse_json_object_handles_dict_passthrough():
    assert cross_topic._parse_json_object({"key": "val"}) == {"key": "val"}


def test_parse_json_object_parses_json_string():
    assert cross_topic._parse_json_object('{"entry_count": 5}') == {"entry_count": 5}


def test_parse_json_object_returns_empty_on_bad_input():
    assert cross_topic._parse_json_object("bad") == {}
    assert cross_topic._parse_json_object(None) == {}
