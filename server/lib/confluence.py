"""
Confluence Cloud REST API v1 + v2 helpers
"""

from typing import Optional, List, Dict

import requests
from requests.auth import HTTPBasicAuth


def get_space_id_by_key(base: str, email: str, token: str, space_key: str) -> str:
    """Get spaceId from space key using v2 API"""
    url = f"{base}/wiki/api/v2/spaces"
    resp = requests.get(url, params={"keys": space_key},
                        auth=HTTPBasicAuth(email, token))
    resp.raise_for_status()
    data = resp.json()
    results = data.get("results", [])
    if not results:
        raise ValueError(f"Space with key '{space_key}' not found")
    return results[0]["id"]


def cql_search(base: str, email: str, token: str, cql: str, limit: int = 50) -> list:
    """v1 search with CQL"""
    url = f"{base}/wiki/rest/api/search"
    resp = requests.get(url, params={"cql": cql, "limit": limit},
                        auth=HTTPBasicAuth(email, token))
    resp.raise_for_status()
    data = resp.json()
    results = []
    for it in data.get("results", []):
        content = it.get("content", {})
        if content.get("id"):
            results.append({
                "id": content["id"],
                "title": content.get("title", "Untitled")
            })
    return results


def search_pages(
    base: str,
    email: str,
    token: str,
    space_key: str,
    query: str,
    *,
    label: Optional[str] = None,
    parent_id: Optional[str] = None,
    limit: int = 8,
) -> List[Dict[str, str]]:
    """Search pages within a space optionally scoped by label or parent."""
    sanitized = query.replace('"', '\\"') if query else ""
    clauses = [f'space = "{space_key}"', "type = page"]
    if sanitized:
        clauses.append(f'title ~ "{sanitized}"')
    if label:
        clauses.append(f'label = "{label}"')
    if parent_id:
        clauses.append(f'parent = "{parent_id}"')

    cql = " AND ".join(clauses)
    results = cql_search(base, email, token, cql, limit=limit)
    summaries: List[Dict[str, str]] = []
    for item in results:
        summaries.append(
            {
                "id": item["id"],
                "title": item.get("title", "Untitled"),
                "url": extract_page_url(base, space_key, {"id": item["id"], "_links": {}}),
                "space_key": space_key,
            }
        )
    return summaries


def get_page_storage(base: str, email: str, token: str, page_id: str) -> dict:
    """Get page content using v2 API"""
    url = f"{base}/wiki/api/v2/pages/{page_id}"
    resp = requests.get(url, params={"body-format": "storage"},
                        auth=HTTPBasicAuth(email, token))
    resp.raise_for_status()
    return resp.json()


def get_page_summary(base: str, email: str, token: str, page_id: str) -> Dict[str, str]:
    """Retrieve a lightweight summary (title, url, spaceKey) for a page."""
    data = get_page_storage(base, email, token, page_id)
    space_id = data.get("spaceId")
    space_key = data.get("spaceKey")

    # When fetching via v2, response may not include spaceKey. Resolve if needed.
    if not space_key and space_id:
        space_resp = requests.get(
            f"{base}/wiki/api/v2/spaces/{space_id}",
            auth=HTTPBasicAuth(email, token),
        )
        space_resp.raise_for_status()
        space_key = space_resp.json().get("key")

    page_links = data.get("_links", {})
    web_ui = page_links.get("webui")
    url = f"{base}{web_ui}" if web_ui else f"{base}/wiki/spaces/{space_key or ''}/pages/{page_id}"

    return {
        "id": page_id,
        "title": data.get("title", "Untitled"),
        "url": url,
        "space_key": space_key or "",
    }


def create_confluence_page(base: str, email: str, token: str, space_key: str,
                          parent_id: Optional[str], title: str, storage_html: str) -> dict:
    """Create a new Confluence page using v2 API with spaceId (required)"""
    # Get spaceId from space key (required for v2 API)
    space_id = get_space_id_by_key(base, email, token, space_key)
    
    url = f"{base}/wiki/api/v2/pages"
    payload = {
        "spaceId": space_id,  # Required
        "status": "current",
        "title": title,
        "body": {
            "representation": "storage",
            "value": storage_html
        }
    }
    
    # Add parentId if provided
    if parent_id:
        payload["parentId"] = parent_id
    
    resp = requests.post(url, json=payload,
                         auth=HTTPBasicAuth(email, token))
    resp.raise_for_status()
    return resp.json()


def extract_page_url(base: str, space_key: str, response: dict) -> str:
    """Extract page URL from Confluence API response"""
    page_id = response.get('id', '?')
    page_links = response.get('_links', {})
    web_ui = page_links.get('webui', '')
    if web_ui:
        return f"{base}{web_ui}"
    else:
        # Fallback URL construction
        return f"{base}/wiki/spaces/{space_key}/pages/{page_id}"
