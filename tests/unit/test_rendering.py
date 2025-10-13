"""Unit tests for server.lib.rendering module.

Tests cover:
- Markdown rendering from plan JSON
- Template variable substitution
- None-value handling (_nn filter)
- Date injection
"""

import pytest
from server.lib.rendering import render_plan_md, _nn


class TestNoneHandling:
    """Test the _nn (none-normalizing) filter."""

    def test_none_returns_none_found(self):
        assert _nn(None) == "None found"

    def test_empty_string_returns_none_found(self):
        assert _nn("") == "None found"
        assert _nn("   ") == "None found"

    def test_unknown_variations_return_none_found(self):
        assert _nn("UNKNOWN") == "None found"
        assert _nn("TBD") == "None found"
        assert _nn("T.B.D.") == "None found"
        assert _nn("NA") == "None found"
        assert _nn("N/A") == "None found"

    def test_valid_string_passes_through(self):
        assert _nn("316L Stainless Steel") == "316L Stainless Steel"
        assert _nn("Material: 304 SS") == "Material: 304 SS"

    def test_numbers_converted_to_string(self):
        assert _nn(42) == "42"
        assert _nn(3.14) == "3.14"


class TestBasicRendering:
    """Test basic markdown rendering."""

    def test_minimal_plan_renders_without_error(self):
        plan = {
            "project": "Test Project",
            "customer": "Test Customer",
            "revision": "A",
            "keys": ["Key 1", "Key 2"],
            "risks": [],
            "open_questions": [],
            "cost_levers": [],
        }
        result = render_plan_md(plan)

        assert "Test Project" in result
        assert "Test Customer" in result
        assert "Rev:** A" in result
        assert "Key 1" in result
        assert "Key 2" in result

    def test_date_is_injected(self):
        plan = {
            "project": "Test",
            "customer": "ACME",
            "keys": [],
            "risks": [],
        }
        result = render_plan_md(plan)

        # Should contain YYYY-MM-DD formatted date
        import re
        assert re.search(r"\*\*Date:\*\* \d{4}-\d{2}-\d{2}", result)

    def test_quality_plan_renders(self):
        plan = {
            "project": "Test",
            "customer": "ACME",
            "keys": [],
            "risks": [],
            "quality_plan": {
                "hold_points": ["FAI", "Final Inspection"],
                "ctqs": ["Dimension A", "Flatness"],
                "passivation": "Nitric acid per AMS 2700",
                "cleanliness": "Wipe test per spec",
                "required_tests": ["Leak test", "Pressure test"],
                "documentation": ["Material certs", "Test reports"],
                "metrology": ["Faro for large parts"],
            },
        }
        result = render_plan_md(plan)

        assert "FAI, Final Inspection" in result
        assert "Dimension A, Flatness" in result
        assert "Nitric acid per AMS 2700" in result
        assert "Leak test, Pressure test" in result

    def test_purchasing_with_long_leads(self):
        plan = {
            "project": "Test",
            "customer": "ACME",
            "keys": [],
            "risks": [],
            "purchasing": {
                "coo_mtr": "USA, Material certs required",
                "long_leads": [
                    {"item": "Titanium plate", "lead_time": "16 weeks", "vendor_hint": "Supplier X"},
                    {"item": "Custom fasteners", "lead_time": "8 weeks", "vendor_hint": None},
                ],
                "alternates": [],
                "rfqs": [],
            },
        }
        result = render_plan_md(plan)

        assert "USA, Material certs required" in result
        assert "Titanium plate" in result
        assert "16 weeks" in result
        assert "Supplier X" in result
        assert "Custom fasteners" in result

    def test_risks_section(self):
        plan = {
            "project": "Test",
            "customer": "ACME",
            "keys": [],
            "risks": [
                {
                    "risk": "Weld porosity",
                    "impact": "High",
                    "mitigation": "Pre-weld cleaning and qualified welders",
                    "owner": "Weld Engineer",
                    "due_date": "2025-01-15",
                },
                {
                    "risk": "Late material delivery",
                    "impact": "Medium",
                    "mitigation": "Order 2 weeks early",
                    "owner": None,
                    "due_date": None,
                },
            ],
        }
        result = render_plan_md(plan)

        assert "Weld porosity" in result
        assert "Pre-weld cleaning and qualified welders" in result
        assert "Weld Engineer" in result
        assert "2025-01-15" in result
        assert "Late material delivery" in result
        # Should show TBD for missing owner/date
        assert "TBD" in result

    def test_engineering_instructions_with_routing(self):
        plan = {
            "project": "Test",
            "customer": "ACME",
            "keys": [],
            "risks": [],
            "engineering_instructions": {
                "routing": [
                    {
                        "workcenter": "Laser Cut",
                        "input": "4x8 sheet",
                        "program": "PROG-001",
                        "notes": ["Check nesting", "Verify material thickness"],
                        "qc": ["Visual inspection"],
                        "sources": [],
                    },
                    {
                        "workcenter": "Forming",
                        "input": "Cut parts",
                        "program": None,
                        "notes": [],
                        "qc": ["Check angles with template"],
                        "sources": [],
                    },
                ],
                "fixtures": [
                    {"id": "FIX-001", "name": "Weld Fixture", "type": "V-block", "status": "Available"},
                ],
                "programs": [
                    {"machine": "Laser 1", "file": "PROG-001.nc", "rev": "B"},
                ],
                "quality_routing": [
                    {
                        "workcenter": "After Weld",
                        "quality_operation": "Weld inspection per WPS",
                        "notes": ["Check for porosity", "Visual + dye penetrant"],
                        "sources": [],
                    },
                ],
                "dfm_actions": [
                    {
                        "action": "Add weld access holes",
                        "target": "Design phase",
                        "rationale": "Improve weld quality",
                        "sources": [],
                    },
                ],
                "exceptional_steps": [],
                "ctqs_for_routing": ["Hole spacing", "Flatness"],
                "open_items": ["Confirm fixture availability", "Get customer approval on material"],
            },
        }
        result = render_plan_md(plan)

        assert "Laser Cut" in result
        assert "PROG-001" in result
        assert "Check nesting" in result
        assert "Forming" in result
        assert "FIX-001" in result
        assert "Weld Fixture" in result
        assert "After Weld" in result
        assert "Weld inspection per WPS" in result
        assert "Add weld access holes" in result
        assert "Hole spacing, Flatness" in result
        assert "Confirm fixture availability" in result

    def test_context_sources_rendered(self):
        plan = {
            "project": "Test",
            "customer": "ACME",
            "keys": [],
            "risks": [],
            "context_pack": {
                "sources": [
                    {"id": "DWG-001", "title": "Main Assembly", "kind": "drawing", "authority": "mandatory"},
                    {"id": "PO-1001", "title": "Purchase Order", "kind": "po", "authority": "mandatory"},
                ],
            },
        }
        result = render_plan_md(plan)

        assert "DWG-001" in result
        assert "Main Assembly" in result
        assert "drawing" in result
        assert "PO-1001" in result

    def test_empty_sections_show_defaults(self):
        plan = {
            "project": "Minimal Plan",
            "customer": "ACME",
            "keys": [],
            "risks": [],
        }
        result = render_plan_md(plan)

        # Empty quality plan should show "None found"
        assert "None found" in result
        # Should have default/placeholder text for missing sections
        assert "TBD" in result


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_missing_keys_uses_summary_fallback(self):
        plan = {
            "project": "Test",
            "customer": "ACME",
            "summary": "1. Key one\n2. Key two\n3. Key three",
            "risks": [],
        }
        result = render_plan_md(plan)

        # Should parse summary into enumerated list
        assert "1. Key one" in result or "1. 1. Key one" in result  # May have double numbering

    def test_no_keys_no_summary_shows_default(self):
        plan = {
            "project": "Test",
            "customer": "ACME",
            "risks": [],
        }
        result = render_plan_md(plan)

        assert "Manufacturing priorities to be synthesized" in result

    def test_handles_none_values_gracefully(self):
        plan = {
            "project": None,
            "customer": None,
            "revision": None,
            "keys": None,
            "risks": None,
        }
        # Should not crash
        result = render_plan_md(plan)
        assert isinstance(result, str)
        assert len(result) > 0
