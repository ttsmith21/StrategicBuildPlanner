"""Integration tests for specialist agents with mocked OpenAI responses.

These tests verify agent behavior without hitting the live OpenAI API.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from server.agents.coordinator import coordinator_run_specialists
from server.lib.schema import ContextPack


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI assistant response."""
    def _make_response(json_data):
        mock_response = MagicMock()
        mock_response.status = "completed"

        # Mock message with JSON content
        mock_message = MagicMock()
        mock_content = MagicMock()
        mock_text = MagicMock()
        mock_text.value = json_data
        mock_content.text = mock_text
        mock_message.content = [mock_content]

        mock_messages = MagicMock()
        mock_messages.data = [mock_message]

        return mock_response, mock_messages
    return _make_response


class TestAgentCoordinatorMocked:
    """Test agent coordinator with mocked OpenAI calls."""

    @pytest.mark.skip(reason="Requires complex mocking of OpenAI SDK - implement when needed")
    def test_coordinator_with_mocked_agents(self, mock_openai_response):
        """Test coordinator orchestration with mocked agent responses."""
        # This is a placeholder for future implementation
        # Would mock each specialist agent's OpenAI calls
        pass

    def test_coordinator_normalizes_plan_structure(self):
        """Test that coordinator creates proper plan structure."""
        from server.agents.coordinator import _normalize_plan

        # Test with None
        result = _normalize_plan(None)
        assert isinstance(result, dict)
        assert "project" in result
        assert "customer" in result
        assert "quality_plan" in result

        # Test with partial plan
        partial = {"project": "Test", "customer": "ACME"}
        result = _normalize_plan(partial)
        assert result["project"] == "Test"
        assert result["customer"] == "ACME"
        assert isinstance(result["quality_plan"], dict)
        assert isinstance(result["purchasing"], dict)

    def test_context_pack_coercion(self):
        """Test context pack validation and coercion."""
        from server.agents.coordinator import _coerce_context_pack

        # Test with dict
        pack_dict = {
            "project": {"name": "Test"},
            "sources": [],
            "facts": []
        }
        result = _coerce_context_pack(pack_dict)
        assert isinstance(result, ContextPack)

        # Test with None
        result = _coerce_context_pack(None)
        assert isinstance(result, ContextPack)
        assert result.project == {}
        assert result.sources == []
        assert result.facts == []


class TestAgentPatching:
    """Test applying agent patches to plan."""

    def test_apply_patch_respects_ownership(self):
        """Test that patches only update authorized sections."""
        from server.agents.coordinator import _apply_patch
        from server.lib.schema import AgentPatch

        plan = {
            "quality_plan": {"ctqs": ["Old CTQ"]},
            "purchasing": {"long_leads": []},
        }

        # QMA should only modify quality_plan
        patch = AgentPatch(patch={"quality_plan": {"ctqs": ["New CTQ"]}})
        allowed_keys = {"quality_plan"}

        _apply_patch(plan, patch, allowed_keys)

        assert plan["quality_plan"]["ctqs"] == ["New CTQ"]
        assert plan["purchasing"]["long_leads"] == []  # Unchanged

    def test_apply_patch_rejects_unauthorized_sections(self):
        """Test that patches to unauthorized sections are ignored."""
        from server.agents.coordinator import _apply_patch
        from server.lib.schema import AgentPatch

        plan = {
            "quality_plan": {"ctqs": ["Original"]},
            "purchasing": {"long_leads": []},
        }

        # QMA trying to modify purchasing (not allowed)
        patch = AgentPatch(patch={
            "quality_plan": {"ctqs": ["Updated"]},
            "purchasing": {"long_leads": [{"item": "Unauthorized"}]},  # Should be ignored
        })
        allowed_keys = {"quality_plan"}  # Only quality_plan allowed

        _apply_patch(plan, patch, allowed_keys)

        assert plan["quality_plan"]["ctqs"] == ["Updated"]
        assert plan["purchasing"]["long_leads"] == []  # Unchanged due to no authorization


class TestTaskFingerprinting:
    """Test Asana task fingerprinting for deduplication."""

    def test_task_to_dict_includes_fingerprint(self):
        """Test that tasks get fingerprints for deduplication."""
        from server.agents.coordinator import _task_to_dict
        from server.lib.schema import AgentTask

        task = AgentTask(
            name="Order material",
            notes="316L SS plate",
            owner_hint="Purchasing",
            due_date="2025-11-01",
            source_hint="DWG-001"
        )

        result = _task_to_dict(task)

        assert result["name"] == "Order material"
        assert result["owner_hint"] == "Purchasing"
        assert result["due_on"] == "2025-11-01"
        assert "fingerprint" in result
        assert isinstance(result["fingerprint"], str)
        assert len(result["fingerprint"]) > 0

    def test_identical_tasks_have_same_fingerprint(self):
        """Test that identical tasks generate same fingerprint."""
        from server.agents.coordinator import _task_to_dict
        from server.lib.schema import AgentTask

        task1 = AgentTask(
            name="Order material",
            notes="Any notes",
            owner_hint="Purchasing",
            due_date=None,
            source_hint="DWG-001"
        )

        task2 = AgentTask(
            name="Order material",
            notes="Different notes",  # Notes don't affect fingerprint
            owner_hint="Purchasing",
            due_date="2025-12-01",  # Due date doesn't affect fingerprint
            source_hint="DWG-001"
        )

        result1 = _task_to_dict(task1)
        result2 = _task_to_dict(task2)

        # Same name, source, owner → same fingerprint
        assert result1["fingerprint"] == result2["fingerprint"]

    def test_different_tasks_have_different_fingerprints(self):
        """Test that different tasks generate different fingerprints."""
        from server.agents.coordinator import _task_to_dict
        from server.lib.schema import AgentTask

        task1 = AgentTask(
            name="Order material",
            notes="",
            owner_hint="Purchasing",
            due_date=None,
            source_hint="DWG-001"
        )

        task2 = AgentTask(
            name="Review design",  # Different name
            notes="",
            owner_hint="Engineering",
            due_date=None,
            source_hint="DWG-001"
        )

        result1 = _task_to_dict(task1)
        result2 = _task_to_dict(task2)

        assert result1["fingerprint"] != result2["fingerprint"]
