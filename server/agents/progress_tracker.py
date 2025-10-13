"""
Progress tracking for specialist agent execution.

Provides real-time status updates during agent workflow using callbacks.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

LOGGER = logging.getLogger(__name__)


class AgentStatus(str, Enum):
    """Agent execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentProgress:
    """Track progress for a single agent"""
    agent_name: str
    status: AgentStatus = AgentStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "agent_name": self.agent_name,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "metadata": self.metadata,
        }


class ProgressTracker:
    """Track progress of specialist agent execution"""

    def __init__(self):
        self.agents: Dict[str, AgentProgress] = {}
        self.callbacks: list[Callable[[Dict[str, Any]], None]] = []
        self.overall_status: AgentStatus = AgentStatus.PENDING
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None

    def add_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Add a callback to be notified of progress updates"""
        self.callbacks.append(callback)

    def initialize_agents(self, agent_names: list[str]) -> None:
        """Initialize tracking for all agents"""
        self.agents = {name: AgentProgress(agent_name=name) for name in agent_names}
        self.overall_status = AgentStatus.RUNNING
        self.started_at = datetime.now()
        self._notify()

    def start_agent(self, agent_name: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Mark an agent as started"""
        if agent_name not in self.agents:
            self.agents[agent_name] = AgentProgress(agent_name=agent_name)

        agent = self.agents[agent_name]
        agent.status = AgentStatus.RUNNING
        agent.started_at = datetime.now()
        if metadata:
            agent.metadata.update(metadata)

        LOGGER.info(f"Progress: {agent_name} started")
        self._notify()

    def complete_agent(
        self,
        agent_name: str,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Mark an agent as completed or failed"""
        if agent_name not in self.agents:
            LOGGER.warning(f"Attempting to complete untracked agent: {agent_name}")
            return

        agent = self.agents[agent_name]
        agent.status = AgentStatus.FAILED if error else AgentStatus.COMPLETED
        agent.completed_at = datetime.now()
        agent.error = error
        if metadata:
            agent.metadata.update(metadata)

        status_str = "failed" if error else "completed"
        LOGGER.info(f"Progress: {agent_name} {status_str}")
        self._notify()

        # Check if all agents are done
        if all(a.status in (AgentStatus.COMPLETED, AgentStatus.FAILED) for a in self.agents.values()):
            self._finalize()

    def _finalize(self) -> None:
        """Mark overall execution as complete"""
        self.overall_status = AgentStatus.COMPLETED
        self.completed_at = datetime.now()

        # Check if any agents failed
        failed = [a for a in self.agents.values() if a.status == AgentStatus.FAILED]
        if failed:
            LOGGER.warning(f"Progress: Complete with {len(failed)} failures")
        else:
            LOGGER.info("Progress: All agents completed successfully")

        self._notify()

    def _notify(self) -> None:
        """Notify all callbacks of current state"""
        state = self.get_state()
        for callback in self.callbacks:
            try:
                callback(state)
            except Exception as e:
                LOGGER.error(f"Progress callback error: {e}")

    def get_state(self) -> Dict[str, Any]:
        """Get current state as dictionary"""
        return {
            "overall_status": self.overall_status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "agents": {name: agent.to_dict() for name, agent in self.agents.items()},
        }


# Global tracker instance (one per process)
_tracker: Optional[ProgressTracker] = None


def get_tracker() -> ProgressTracker:
    """Get or create the global progress tracker"""
    global _tracker
    if _tracker is None:
        _tracker = ProgressTracker()
    return _tracker


def reset_tracker() -> None:
    """Reset the global tracker"""
    global _tracker
    _tracker = None
