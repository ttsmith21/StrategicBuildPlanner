"""
Checkpoint system for agent execution.

Saves intermediate results to allow resuming from failures.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

LOGGER = logging.getLogger(__name__)


class CheckpointManager:
    """Manage checkpoints for agent execution"""

    def __init__(self, checkpoint_dir: str = "outputs/checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def save_checkpoint(
        self,
        session_id: str,
        agent_name: str,
        plan: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Save a checkpoint after an agent completes.

        Args:
            session_id: Session identifier
            agent_name: Name of the agent that just completed
            plan: Current plan state
            metadata: Optional metadata (tasks, conflicts, etc.)

        Returns:
            Path to checkpoint file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        checkpoint_file = self.checkpoint_dir / f"{session_id}_{agent_name}_{timestamp}.json"

        checkpoint_data = {
            "session_id": session_id,
            "agent_name": agent_name,
            "timestamp": datetime.now().isoformat(),
            "plan": plan,
            "metadata": metadata or {},
        }

        try:
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)

            LOGGER.info(f"Checkpoint saved: {checkpoint_file.name}")
            return str(checkpoint_file)

        except Exception as e:
            LOGGER.error(f"Failed to save checkpoint: {e}")
            return ""

    def load_latest_checkpoint(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Load the most recent checkpoint for a session.

        Args:
            session_id: Session identifier

        Returns:
            Checkpoint data or None if no checkpoint found
        """
        try:
            # Find all checkpoints for this session
            checkpoints = sorted(
                self.checkpoint_dir.glob(f"{session_id}_*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )

            if not checkpoints:
                LOGGER.info(f"No checkpoints found for session {session_id}")
                return None

            latest = checkpoints[0]
            with open(latest, 'r', encoding='utf-8') as f:
                data = json.load(f)

            LOGGER.info(f"Loaded checkpoint: {latest.name}")
            return data

        except Exception as e:
            LOGGER.error(f"Failed to load checkpoint: {e}")
            return None

    def list_checkpoints(self, session_id: str) -> list[Dict[str, Any]]:
        """
        List all checkpoints for a session.

        Args:
            session_id: Session identifier

        Returns:
            List of checkpoint metadata
        """
        try:
            checkpoints = []
            for checkpoint_file in sorted(
                self.checkpoint_dir.glob(f"{session_id}_*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            ):
                try:
                    with open(checkpoint_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        checkpoints.append({
                            "file": checkpoint_file.name,
                            "agent_name": data.get("agent_name"),
                            "timestamp": data.get("timestamp"),
                        })
                except Exception:
                    pass

            return checkpoints

        except Exception as e:
            LOGGER.error(f"Failed to list checkpoints: {e}")
            return []

    def cleanup_old_checkpoints(self, session_id: str, keep_latest: int = 5):
        """
        Clean up old checkpoints, keeping only the most recent ones.

        Args:
            session_id: Session identifier
            keep_latest: Number of checkpoints to keep (default: 5)
        """
        try:
            checkpoints = sorted(
                self.checkpoint_dir.glob(f"{session_id}_*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )

            # Delete old checkpoints
            for checkpoint in checkpoints[keep_latest:]:
                try:
                    checkpoint.unlink()
                    LOGGER.debug(f"Deleted old checkpoint: {checkpoint.name}")
                except Exception as e:
                    LOGGER.warning(f"Failed to delete checkpoint {checkpoint.name}: {e}")

        except Exception as e:
            LOGGER.error(f"Failed to cleanup checkpoints: {e}")


# Global checkpoint manager
_manager: Optional[CheckpointManager] = None


def get_checkpoint_manager() -> CheckpointManager:
    """Get or create the global checkpoint manager"""
    global _manager
    if _manager is None:
        _manager = CheckpointManager()
    return _manager
