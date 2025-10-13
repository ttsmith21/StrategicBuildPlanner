"""Unit tests for server.lib.context_pack module.

Tests cover:
- Source kind detection from filenames/labels
- Precedence and authority resolution
- Fact conflict resolution with canonical/superseded/proposed statuses
- Scope filtering with applies_if conditions
- User metadata overrides
"""

import pytest
from server.lib.context_pack import (
    build_source_registry,
    freeze_context_pack,
    _detect_kind,
    _resolve_precedence,
    _resolve_authority,
    _coerce_precedence_override,
    _coerce_authority_override,
    _fact_in_scope,
)
from server.lib.schema import Source, Fact, Citation, ContextPack


class TestSourceKindDetection:
    """Test automatic detection of source document types."""

    def test_detect_drawing_from_filename(self):
        entry = {"filename": "ACME_bracket_drawing.pdf"}
        assert _detect_kind(entry) == "drawing"

    def test_detect_drawing_from_extension(self):
        entry = {"filename": "assembly.dwg"}
        assert _detect_kind(entry) == "drawing"

        entry = {"filename": "part.dxf"}
        assert _detect_kind(entry) == "drawing"

    def test_detect_po_from_filename(self):
        # Fixed: Underscores are now normalized to spaces
        entry = {"filename": "Purchase_Order_1001.pdf"}
        assert _detect_kind(entry) == "po"

        # PO alone works
        entry = {"title": "PO 1001"}
        assert _detect_kind(entry) == "po"

        # Space-separated works
        entry = {"filename": "Purchase Order 1001.pdf"}
        assert _detect_kind(entry) == "po"

    def test_detect_quote(self):
        entry = {"filename": "Quote_500_RevB.pdf"}
        assert _detect_kind(entry) == "quote"

        # Fixed: "proposal" is now checked before "po" substring
        entry = {"title": "Proposal for ACME Project"}
        assert _detect_kind(entry) == "quote"

    def test_detect_itp(self):
        entry = {"filename": "Inspection_Test_Plan.docx"}
        assert _detect_kind(entry) == "itp"

        entry = {"title": "ITP Rev C"}
        assert _detect_kind(entry) == "itp"

    def test_detect_customer_spec_from_labels(self):
        entry = {
            "filename": "spec_9001.pdf",
            "labels": ["customer", "spec"]
        }
        assert _detect_kind(entry) == "customer_spec"

    def test_detect_lessons_learned(self):
        entry = {"title": "Lessons Learned - Bracket Program"}
        assert _detect_kind(entry) == "lessons_learned"

        entry = {"filename": "retrospective_notes.txt"}
        assert _detect_kind(entry) == "lessons_learned"

    def test_detect_meeting_notes(self):
        entry = {"filename": "kickoff_meeting_notes.txt"}
        assert _detect_kind(entry) == "meeting_notes"

    def test_detect_email(self):
        entry = {"filename": "customer_email_thread.eml"}
        assert _detect_kind(entry) == "email"

    def test_detect_sow(self):
        entry = {"title": "Statement of Work - ACME Project"}
        assert _detect_kind(entry) == "sow_spec"

    def test_detect_generic_spec(self):
        entry = {"filename": "welding_procedure_spec.pdf"}
        assert _detect_kind(entry) == "generic_spec"

    def test_fallback_to_other(self):
        entry = {"filename": "random_document.txt"}
        assert _detect_kind(entry) == "other"


class TestPrecedenceAndAuthority:
    """Test precedence ranking and authority assignment."""

    def test_resolve_precedence_drawing(self):
        assert _resolve_precedence("drawing") == 1

    def test_resolve_precedence_po(self):
        assert _resolve_precedence("po") == 1

    def test_resolve_precedence_quote(self):
        assert _resolve_precedence("quote") == 2

    def test_resolve_precedence_customer_spec(self):
        assert _resolve_precedence("customer_spec") == 3

    def test_resolve_precedence_lessons_learned(self):
        assert _resolve_precedence("lessons_learned") == 6

    def test_resolve_precedence_email(self):
        assert _resolve_precedence("email") == 20

    def test_resolve_precedence_unknown_kind(self):
        assert _resolve_precedence("unknown_type") == 10  # default

    def test_resolve_authority_drawing(self):
        assert _resolve_authority("drawing") == "mandatory"

    def test_resolve_authority_po(self):
        assert _resolve_authority("po") == "mandatory"

    def test_resolve_authority_quote(self):
        assert _resolve_authority("quote") == "conditional"

    def test_resolve_authority_lessons(self):
        assert _resolve_authority("lessons_learned") == "internal"

    def test_precedence_override_integer(self):
        assert _coerce_precedence_override(5, fallback=10) == 5

    def test_precedence_override_string_digit(self):
        assert _coerce_precedence_override("3", fallback=10) == 3

    def test_precedence_override_keyword(self):
        assert _coerce_precedence_override("highest", fallback=10) == 1
        assert _coerce_precedence_override("high", fallback=10) == 2
        assert _coerce_precedence_override("medium", fallback=10) == 5
        assert _coerce_precedence_override("low", fallback=10) == 10

    def test_precedence_override_invalid_falls_back(self):
        assert _coerce_precedence_override("garbage", fallback=10) == 10
        assert _coerce_precedence_override(None, fallback=10) == 10

    def test_authority_override_valid(self):
        assert _coerce_authority_override("mandatory", "reference") == "mandatory"
        assert _coerce_authority_override("conditional", "reference") == "conditional"
        assert _coerce_authority_override("reference", "mandatory") == "reference"
        assert _coerce_authority_override("internal", "mandatory") == "internal"

    def test_authority_override_synonym(self):
        assert _coerce_authority_override("must", "reference") == "mandatory"
        assert _coerce_authority_override("shall", "reference") == "mandatory"
        assert _coerce_authority_override("should", "reference") == "conditional"
        assert _coerce_authority_override("guidance", "mandatory") == "reference"

    def test_authority_override_invalid_falls_back(self):
        assert _coerce_authority_override("invalid", "mandatory") == "mandatory"
        assert _coerce_authority_override(None, "conditional") == "conditional"


class TestBuildSourceRegistry:
    """Test source registry construction from uploaded files and Confluence pages."""

    def test_build_registry_from_uploaded_files(self):
        uploaded = [
            {"id": "upload-1", "filename": "drawing.pdf", "customer": "ACME"},
            {"id": "upload-2", "filename": "PO_1001.pdf", "customer": "ACME"},
        ]
        sources = build_source_registry(uploaded, [])

        assert len(sources) == 2
        assert sources[0].kind == "drawing"
        assert sources[0].authority == "mandatory"
        assert sources[0].precedence_rank == 1
        assert sources[0].customer == "ACME"

        assert sources[1].kind == "po"
        assert sources[1].authority == "mandatory"
        assert sources[1].precedence_rank == 1

    def test_build_registry_from_confluence_pages(self):
        confluence = [
            {"id": "CONF-42", "title": "Customer Spec 9001", "labels": ["customer_spec"]},
            {"id": "CONF-99", "title": "Lessons Learned", "labels": ["lessons_learned"]},
        ]
        sources = build_source_registry([], confluence)

        assert len(sources) == 2
        assert sources[0].kind == "customer_spec"
        assert sources[0].authority == "mandatory"
        assert sources[0].precedence_rank == 3

        assert sources[1].kind == "lessons_learned"
        assert sources[1].authority == "internal"
        assert sources[1].precedence_rank == 6

    def test_build_registry_with_user_metadata_override(self):
        uploaded = [
            {"id": "upload-1", "filename": "document.pdf"},
        ]
        files_meta = {
            "document.pdf": {
                "doc_type": "itp",
                "authority": "mandatory",
                "precedence_rank": 1,
            }
        }
        sources = build_source_registry(uploaded, [], files_meta=files_meta)

        assert len(sources) == 1
        # User override should win
        assert sources[0].kind == "itp"
        assert sources[0].authority == "mandatory"
        assert sources[0].precedence_rank == 1

    def test_build_registry_case_insensitive_metadata(self):
        """Metadata keys should match case-insensitively."""
        uploaded = [
            {"id": "upload-1", "filename": "Drawing.PDF"},
        ]
        files_meta = {
            "drawing.pdf": {"doc_type": "customer_spec"}  # lowercase key
        }
        sources = build_source_registry(uploaded, [], files_meta=files_meta)

        # Should match despite case difference
        assert sources[0].kind == "customer_spec"


class TestFactConflictResolution:
    """Test canonical fact selection with precedence rules."""

    def test_drawing_beats_quote_same_topic(self, make_fact, sample_sources, sample_project):
        """Drawing (precedence=1) should override quote (precedence=2)."""
        facts = [
            make_fact("Material", "304 SS from quote", "QUOTE-500", "conditional", 2),
            make_fact("Material", "316L SS from drawing", "DWG-001", "mandatory", 1),
        ]

        pack = freeze_context_pack(sample_sources, facts, sample_project)

        material_facts = [f for f in pack.facts if f.topic == "Material"]
        assert len(material_facts) == 2

        canonical = next(f for f in material_facts if f.status == "canonical")
        assert canonical.claim == "316L SS from drawing"
        assert canonical.precedence_rank == 1

        superseded = next(f for f in material_facts if f.status == "superseded")
        assert superseded.claim == "304 SS from quote"

    def test_po_beats_customer_spec(self, make_fact, sample_sources, sample_project):
        """PO (precedence=1) beats customer spec (precedence=3)."""
        facts = [
            make_fact("Delivery", "30 days per spec", "SPEC-9001", "mandatory", 3),
            make_fact("Delivery", "45 days per PO", "PO-1001", "mandatory", 1),
        ]

        pack = freeze_context_pack(sample_sources, facts, sample_project)

        canonical = next(f for f in pack.facts if f.status == "canonical")
        assert canonical.claim == "45 days per PO"
        assert canonical.precedence_rank == 1

    def test_mandatory_beats_reference_authority(self, make_fact, sample_sources, sample_project):
        """Mandatory authority wins even with higher precedence number."""
        facts = [
            make_fact("Weld Method", "TIG per spec", "SPEC-9001", "mandatory", 3),
            make_fact("Weld Method", "MIG suggested", "LL-42", "internal", 99),
        ]

        pack = freeze_context_pack(sample_sources, facts, sample_project)

        canonical = next(f for f in pack.facts if f.status == "canonical")
        assert canonical.claim == "TIG per spec"
        assert canonical.authority == "mandatory"

    def test_reference_promoted_when_no_mandatory(self, make_fact, sample_sources, sample_project):
        """If only reference/internal sources exist, promote the highest precedence."""
        facts = [
            make_fact("Best Practice", "Suggestion from lessons", "LL-42", "internal", 99),
        ]

        pack = freeze_context_pack(sample_sources, facts, sample_project)

        # Should be promoted to canonical since it's the only one
        canonical = next(f for f in pack.facts if f.status == "canonical")
        assert canonical.claim == "Suggestion from lessons"

    def test_multiple_superseded_facts(self, make_fact, sample_sources, sample_project):
        """All non-canonical mandatory/conditional facts become superseded."""
        facts = [
            make_fact("CTQ", "Dimension A from drawing", "DWG-001", "mandatory", 1),
            make_fact("CTQ", "Dimension A from quote", "QUOTE-500", "conditional", 2),
            make_fact("CTQ", "Dimension A from spec", "SPEC-9001", "mandatory", 3),
        ]

        pack = freeze_context_pack(sample_sources, facts, sample_project)

        canonical_count = sum(1 for f in pack.facts if f.status == "canonical")
        superseded_count = sum(1 for f in pack.facts if f.status == "superseded")

        assert canonical_count == 1
        assert superseded_count == 2

        canonical = next(f for f in pack.facts if f.status == "canonical")
        assert canonical.claim == "Dimension A from drawing"

    def test_reference_marked_proposed_when_mandatory_exists(self, make_fact, sample_sources, sample_project):
        """Reference/internal facts stay 'proposed' when mandatory exists."""
        facts = [
            make_fact("Process", "Method A from drawing", "DWG-001", "mandatory", 1),
            make_fact("Process", "Method B from lessons", "LL-42", "internal", 99),
        ]

        pack = freeze_context_pack(sample_sources, facts, sample_project)

        canonical = next(f for f in pack.facts if f.status == "canonical")
        assert canonical.authority == "mandatory"

        proposed = next(f for f in pack.facts if f.status == "proposed")
        assert proposed.authority == "internal"
        assert proposed.claim == "Method B from lessons"


class TestScopeFiltering:
    """Test applies_if conditional fact filtering."""

    def test_fact_applies_to_matching_project(self, make_fact, sample_sources):
        """Fact with applies_if should be included when project matches."""
        fact = make_fact(
            "Pricing", "Special discount", "QUOTE-500",
            applies_if={"customer": "ACME"}
        )

        project = {"customer": "ACME", "family": "Bracket"}
        assert _fact_in_scope(fact, project) is True

    def test_fact_excluded_when_project_doesnt_match(self, make_fact, sample_sources):
        """Fact with applies_if should be excluded when project doesn't match."""
        fact = make_fact(
            "Pricing", "Special discount", "QUOTE-500",
            applies_if={"customer": "ACME"}
        )

        project = {"customer": "TechCorp", "family": "Bracket"}
        assert _fact_in_scope(fact, project) is False

    def test_fact_without_applies_if_always_included(self, make_fact, sample_sources):
        """Facts without applies_if should always be in scope."""
        fact = make_fact("General", "Always applies", "DWG-001")

        project = {"customer": "Anyone"}
        assert _fact_in_scope(fact, project) is True

    def test_freeze_context_pack_filters_out_of_scope(self, make_fact, sample_sources):
        """freeze_context_pack should exclude facts that don't match project."""
        facts = [
            make_fact("In Scope", "Should be included", "DWG-001",
                     applies_if={"customer": "ACME"}),
            make_fact("Out of Scope", "Should be excluded", "QUOTE-500",
                     applies_if={"customer": "TechCorp"}),
        ]

        project = {"customer": "ACME"}
        pack = freeze_context_pack(sample_sources, facts, project)

        assert len(pack.facts) == 1
        assert pack.facts[0].claim == "Should be included"

    def test_multiple_applies_if_conditions(self, make_fact, sample_sources):
        """All applies_if conditions must match."""
        fact = make_fact(
            "Specific", "Very specific fact", "QUOTE-500",
            applies_if={"customer": "ACME", "family": "Bracket"}
        )

        # Both match
        assert _fact_in_scope(fact, {"customer": "ACME", "family": "Bracket"}) is True

        # Only one matches
        assert _fact_in_scope(fact, {"customer": "ACME", "family": "Widget"}) is False
        assert _fact_in_scope(fact, {"customer": "TechCorp", "family": "Bracket"}) is False


class TestContextPackStructure:
    """Test overall ContextPack construction."""

    def test_context_pack_includes_project_metadata(self, sample_sources, sample_project):
        pack = freeze_context_pack(sample_sources, [], sample_project)

        assert pack.project == sample_project
        assert pack.project["customer"] == "ACME"
        assert pack.project["family"] == "Bracket"

    def test_context_pack_includes_sources(self, sample_sources, sample_project):
        pack = freeze_context_pack(sample_sources, [], sample_project)

        assert len(pack.sources) == len(sample_sources)
        assert pack.sources[0].kind == "drawing"

    def test_context_pack_precedence_policy(self, sample_sources, sample_project):
        pack = freeze_context_pack(sample_sources, [], sample_project)

        assert pack.precedence_policy == "lower rank overrides higher"

    def test_context_pack_serialization(self, sample_sources, sample_project, make_fact):
        """ContextPack should serialize to dict for JSON transmission."""
        facts = [
            make_fact("Test", "Test claim", "DWG-001")
        ]
        pack = freeze_context_pack(sample_sources, facts, sample_project)

        # Should be able to convert to dict
        pack_dict = pack.model_dump()
        assert isinstance(pack_dict, dict)
        assert "project" in pack_dict
        assert "sources" in pack_dict
        assert "facts" in pack_dict
        assert "precedence_policy" in pack_dict

        # Should be able to reconstruct
        pack2 = ContextPack.model_validate(pack_dict)
        assert pack2.project == pack.project
        assert len(pack2.sources) == len(pack.sources)
        assert len(pack2.facts) == len(pack.facts)


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_sources_and_facts(self):
        """Should handle empty inputs gracefully."""
        pack = freeze_context_pack([], [], {})

        assert pack.sources == []
        assert pack.facts == []
        assert pack.project == {}

    def test_facts_without_matching_sources(self, make_fact):
        """Facts referencing non-existent sources should still be processed."""
        facts = [
            make_fact("Topic", "Claim", "NONEXISTENT-SOURCE")
        ]
        pack = freeze_context_pack([], facts, {})

        # Should not crash
        assert len(pack.facts) == 1

    def test_duplicate_source_ids(self):
        """Should handle duplicate source IDs (unlikely but possible)."""
        sources = [
            Source(
                kind="drawing", authority="mandatory", precedence_rank=1,
                scope=[], applies_if=None, rev=None, effective_date=None,
                id="DUP-1", title="First", customer=None, family=None
            ),
            Source(
                kind="po", authority="mandatory", precedence_rank=1,
                scope=[], applies_if=None, rev=None, effective_date=None,
                id="DUP-1", title="Second", customer=None, family=None
            ),
        ]

        # Should not crash
        pack = freeze_context_pack(sources, [], {})
        assert len(pack.sources) == 2

    def test_malformed_labels(self):
        """Should handle various label formats."""
        entries = [
            {"filename": "test1.pdf", "labels": None},  # None
            {"filename": "test2.pdf", "labels": []},  # Empty list
            {"filename": "test3.pdf", "labels": {"a": "b"}},  # Dict
            {"filename": "test4.pdf", "labels": [{"name": "drawing"}]},  # Structured
        ]

        # Should not crash
        for entry in entries:
            kind = _detect_kind(entry)
            assert isinstance(kind, str)
