"""
OpenAI Vector Store and file management
"""

import time
from pathlib import Path
from typing import BinaryIO

from openai import OpenAI  # type: ignore


def _get_vector_store_client(client: OpenAI):
    """Return the vector store API accessor for the installed OpenAI SDK."""

    beta = getattr(client, "beta", None)
    if beta is not None and hasattr(beta, "vector_stores"):
        return beta.vector_stores

    direct = getattr(client, "vector_stores", None)
    if direct is not None:
        return direct

    raise RuntimeError("OpenAI client does not expose vector_stores API; upgrade openai package.")


def create_vector_store(client: OpenAI, project_name: str, file_paths: list[str]) -> tuple[str, list[str]]:
    """
    Create OpenAI Vector Store with uploaded files
    
    Returns:
        tuple: (vector_store_id, source_file_names)
    """
    print(f"[OpenAI] Preparing file streams...")

    file_handles: list[tuple[str, BinaryIO]] = []
    for fpath in file_paths:
        p = Path(fpath)
        try:
            fh = open(p, 'rb')
            # Normalize file extension to lowercase for OpenAI API compatibility
            name_parts = p.name.rsplit('.', 1)
            if len(name_parts) == 2:
                normalized_name = f"{name_parts[0]}.{name_parts[1].lower()}"
            else:
                normalized_name = p.name
            file_handles.append((normalized_name, fh))
            size_kb = max(p.stat().st_size // 1024, 1)
            print(f"  ✓ Ready: {normalized_name} (~{size_kb} KB)")
        except Exception as e:
            print(f"  ⚠ Error opening {p.name}: {e}")

    if not file_handles:
        raise ValueError("No files could be opened for upload")
    
    # Create vector store
    vector_stores = _get_vector_store_client(client)

    vs = vector_stores.create(name=f"Strategic Build Plan — {project_name}")
    print(f"[OpenAI] Created vector store: {vs.id}")
    
    # Upload files to vector store
    file_batches = getattr(vector_stores, "file_batches", None)
    if file_batches is None:
        raise RuntimeError("OpenAI vector store client does not provide file_batches helper")

    try:
        batch = file_batches.upload_and_poll(
            vector_store_id=vs.id,
            files=[fh for _, fh in file_handles]
        )
    finally:
        for _, fh in file_handles:
            try:
                fh.close()
            except Exception:
                pass
    
    print(f"[OpenAI] Uploaded {batch.file_counts.completed} files to vector store")
    
    # Wait for files to be processed
    while vs.file_counts.in_progress > 0:
        time.sleep(1)
        vs = vector_stores.retrieve(vs.id)
    
    source_file_names = [fname for fname, _ in file_handles]
    return vs.id, source_file_names


# Note: generate_plan has been removed. Plan generation is handled by the
# StrategicBuildPlannerAgent in agent/agent.py and specialist agents in server/agents/.


def delete_vector_store(client: OpenAI, vector_store_id: str):
    """Delete a vector store"""
    try:
        vector_stores = _get_vector_store_client(client)
        vector_stores.delete(vector_store_id)
        print(f"[OpenAI] Deleted vector store: {vector_store_id}")
    except Exception as e:
        print(f"[OpenAI] Warning: Could not delete vector store {vector_store_id}: {e}")


def append_files_to_vector_store(client: OpenAI, vector_store_id: str, file_paths: list[str]) -> list[str]:
    """Append files to an existing vector store and wait until processed.

    Returns a list of file names appended.
    """
    if not file_paths:
        return []
    vector_stores = _get_vector_store_client(client)
    file_batches = getattr(vector_stores, "file_batches", None)
    if file_batches is None:
        raise RuntimeError("OpenAI vector store client does not provide file_batches helper")

    file_handles: list[tuple[str, BinaryIO]] = []
    for fpath in file_paths:
        p = Path(fpath)
        try:
            fh = open(p, 'rb')
            # Normalize file extension to lowercase for OpenAI API compatibility
            name_parts = p.name.rsplit('.', 1)
            if len(name_parts) == 2:
                normalized_name = f"{name_parts[0]}.{name_parts[1].lower()}"
            else:
                normalized_name = p.name
            file_handles.append((normalized_name, fh))
        except Exception as e:
            print(f"  ⚠ Error opening {p.name}: {e}")
    if not file_handles:
        return []
    try:
        batch = file_batches.upload_and_poll(
            vector_store_id=vector_store_id,
            files=[fh for _, fh in file_handles]
        )
        print(f"[OpenAI] Appended files: completed={batch.file_counts.completed}")
    finally:
        for _, fh in file_handles:
            try:
                fh.close()
            except Exception:
                pass

    # Wait for processing to finish
    vs = vector_stores.retrieve(vector_store_id)
    while vs.file_counts.in_progress > 0:
        time.sleep(1)
        vs = vector_stores.retrieve(vector_store_id)
    return [fname for fname, _ in file_handles]
