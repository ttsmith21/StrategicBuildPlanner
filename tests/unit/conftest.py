"""Shared test fixtures for unit tests."""

import pytest
from server.lib.schema import Source, Fact, Citation


@pytest.fixture
def sample_sources():
    """Standard set of test sources covering all precedence levels."""
    return [
        Source(
            kind="drawing",
            authority="mandatory",
            precedence_rank=1,
            scope=["mechanical"],
            applies_if=None,
            rev="C",
            effective_date="2024-01-15",
            id="DWG-001",
            title="Main Assembly Drawing",
            customer="ACME",
            family="Bracket"
        ),
        Source(
            kind="po",
            authority="mandatory",
            precedence_rank=1,
            scope=["commercial"],
            applies_if=None,
            rev=None,
            effective_date="2024-02-01",
            id="PO-1001",
            title="Purchase Order 1001",
            customer="ACME",
            family="Bracket"
        ),
        Source(
            kind="quote",
            authority="conditional",
            precedence_rank=2,
            scope=["pricing"],
            applies_if={"customer": "ACME"},
            rev="B",
            effective_date="2024-01-20",
            id="QUOTE-500",
            title="Quote 500 Rev B",
            customer="ACME",
            family=None
        ),
        Source(
            kind="customer_spec",
            authority="mandatory",
            precedence_rank=3,
            scope=["quality"],
            applies_if=None,
            rev="D",
            effective_date="2023-12-01",
            id="SPEC-9001",
            title="Customer Spec 9001",
            customer="ACME",
            family=None
        ),
        Source(
            kind="lessons_learned",
            authority="internal",
            precedence_rank=99,
            scope=["knowledge"],
            applies_if=None,
            rev=None,
            effective_date=None,
            id="LL-42",
            title="Lessons Learned - Bracket Program",
            customer="ACME",
            family="Bracket"
        ),
    ]


@pytest.fixture
def sample_project():
    """Standard test project context."""
    return {
        "customer": "ACME",
        "family": "Bracket",
        "name": "ACME Bracket Project",
    }


@pytest.fixture
def make_fact():
    """Factory fixture to create test Facts easily."""
    def _make(
        topic: str,
        claim: str,
        source_id: str,
        authority: str = "mandatory",
        precedence: int = 1,
        applies_if: dict = None,
        status: str = "proposed"
    ):
        return Fact(
            id=f"fact-{topic}-{source_id}",
            claim=claim,
            topic=topic,
            citation=Citation(source_id=source_id, page_ref="1", passage_sha=None),
            authority=authority,
            precedence_rank=precedence,
            applies_if=applies_if,
            status=status,
            confidence_model=0.85
        )
    return _make
