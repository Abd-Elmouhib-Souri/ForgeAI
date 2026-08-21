from app.services.final_report_builder import FinalReportBuilder


def test_source_ids_prefers_canonical_identity_and_keeps_legacy_fallback():
    builder = FinalReportBuilder()

    result = builder._source_ids(
        [
            {
                "canonical_source_id": "src_a",
                "source_id": "legacy_a",
            },
            {
                "canonical_source_id": "src_b",
            },
            {
                "source_id": "legacy_c",
            },
            {
                "canonical_source_id": "src_a",
            },
            {
                "canonical_source_id": "",
                "source_id": "",
            },
        ]
    )

    assert result == [
        "src_a",
        "src_b",
        "legacy_c",
    ]


def test_competitive_projection_preserves_canonical_ledger_identity():
    builder = FinalReportBuilder()

    bucket = builder.SOURCE_BUCKETS[0]

    source_a = {
        "canonical_source_id": "src_a",
        "source_role": "direct_competitor",
    }

    source_b = {
        "canonical_source_id": "src_b",
        "source_role": "adjacent_solution",
    }

    analysis = {
        "competitive_analysis": {
            "canonical_source_ledger": {
                "canonical_sources_count": 2,
                "sources": [
                    source_a,
                    source_b,
                ],
                bucket: [
                    source_a,
                ],
            }
        }
    }

    projection = (
        builder._canonical_competitive_projection(
            analysis
        )
    )

    assert projection[
        "canonical_source_ids"
    ] == [
        "src_a",
        "src_b",
    ]

    assert projection[
        builder._bucket_id_key(
            bucket
        )
    ] == [
        "src_a",
    ]

    assert projection[
        "canonical_sources_count"
    ] == 2
