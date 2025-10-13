"""Northern Standards Library for comparison-based prompts.

Provides a DEFAULT_STANDARDS and a get_standards() helper that can be
overridden via environment variable SBP_STANDARDS_JSON (JSON string).
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

DEFAULT_STANDARDS: Dict[str, Any] = {
    "materials": ["304L", "316L"],
    "weld_codes": ["AWS D1.6"],
    "finishes": ["2B", "#4 optional"],
    "tolerances": ["ISO 2768-mk", "ISO 13920-BF"],
    "inspection": ["Visual inspection", "Internal ITP only"],
    "traceability": ["MTR per PO line"],
    "coatings": ["None", "Pickle/Passivate per A967"],
    "capabilities": {
        "press_brake_max_thickness_in": 0.5,
        "laser_table_envelope_in": [157, 80, 1],
        "robotic_weld_suitable_min_length_in": 8,
    },
}


def get_standards() -> Dict[str, Any]:
    """Return standards dict, allowing env override via SBP_STANDARDS_JSON."""
    raw = os.getenv("SBP_STANDARDS_JSON")
    if not raw:
        return dict(DEFAULT_STANDARDS)
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            merged = dict(DEFAULT_STANDARDS)
            merged.update(data)
            return merged
    except Exception:
        pass
    return dict(DEFAULT_STANDARDS)
