"""Confluence tool adapters for Strategic Build Planner agent."""

from __future__ import annotations

import os
from typing import Dict, Optional

from server.lib.confluence import (
    cql_search,
    create_confluence_page,
    extract_page_url,
    get_space_id_by_key,
)


class ConfluenceConfigError(RuntimeError):
    """Raised when Confluence configuration is incomplete."""


def _load_confluence_config() -> Dict[str, str]:
    base = os.getenv("CONFLUENCE_BASE_URL")
    email = os.getenv("CONFLUENCE_EMAIL")
    token = os.getenv("CONFLUENCE_API_TOKEN")
    space = os.getenv("CONFLUENCE_SPACE_KEY")

    if not all([base, email, token, space]):
        raise ConfluenceConfigError(
            "CONFLUENCE_BASE_URL, CONFLUENCE_EMAIL, CONFLUENCE_API_TOKEN, "
            "and CONFLUENCE_SPACE_KEY must be set in the environment."
        )
    assert base and email and token and space

    return {
        "base": base,
        "email": email,
        "token": token,
        "space": space,
    }


def confluence_search_family(slug_or_cql: str, limit: int = 5) -> Optional[Dict[str, str]]:
    """Search for a Confluence family page by slug or custom CQL.

    Args:
        slug_or_cql: Friendly slug (e.g., "family-of-parts-brackets") or raw CQL.
        limit: Maximum number of results to return.

    Returns:
        The first matching page as a dict with {page_id, title, url}, or None if not found.
    """
    cfg = _load_confluence_config()

    if " " not in slug_or_cql and "=" not in slug_or_cql:
        # Treat as slug/label lookup within the configured space.
        cql = f'space = "{cfg["space"]}" AND label = "{slug_or_cql}" AND type = page'
    else:
        cql = slug_or_cql

    results = cql_search(cfg["base"], cfg["email"], cfg["token"], cql, limit=limit)
    if not results:
        return None

    first = results[0]
    url = f"{cfg['base']}/wiki/spaces/{cfg['space']}/pages/{first['id']}"
    return {
        "page_id": first["id"],
        "title": first["title"],
        "url": url,
    }


def confluence_create_child(
    parent_id: Optional[str],
    title: str,
    storage_html: str,
) -> Dict[str, str]:
    """Create a child page under the given parent using Confluence v2 API.

    Args:
        parent_id: ID of the parent page; if None, creates at the space home level.
        title: Title for the new page.
        storage_html: HTML content in Confluence storage representation.

    Returns:
        Dict with keys {page_id, url, title} for the newly created page.
    """
    cfg = _load_confluence_config()

    response = create_confluence_page(
        cfg["base"],
        cfg["email"],
        cfg["token"],
        cfg["space"],
        parent_id,
        title,
        storage_html,
    )

    page_id = response.get("id", "?")
    url = extract_page_url(cfg["base"], cfg["space"], response)
    return {
        "page_id": page_id,
        "url": url,
        "title": response.get("title", title),
    }


__all__ = [
    "confluence_search_family",
    "confluence_create_child",
    "ConfluenceConfigError",
]
