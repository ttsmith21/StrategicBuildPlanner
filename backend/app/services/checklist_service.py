"""
Checklist Service - Pre-Meeting Checklist Generation with Parallel AI Calls
"""

import os
import json
import asyncio
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path

from openai import OpenAI

logger = logging.getLogger(__name__)

# Path to prompts JSON file
PROMPTS_FILE = Path(__file__).parent.parent / "data" / "checklist_prompts.json"


class ChecklistService:
    """Service for generating pre-meeting checklists using parallel AI calls"""

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        # Assistants API only supports certain models (gpt-4o, gpt-4-turbo, etc.)
        # Use separate env var for Assistants, fall back to gpt-4o
        self.model = os.getenv("OPENAI_MODEL_ASSISTANTS", "gpt-4o")
        self.prompts_data = self._load_prompts()
        # Control parallelism - OpenAI has rate limits
        self.max_concurrent = int(os.getenv("CHECKLIST_MAX_CONCURRENT", "10"))

    def _load_prompts(self) -> Dict:
        """Load prompts from JSON file"""
        try:
            with open(PROMPTS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load prompts: {e}")
            return {"categories": []}

    def get_prompts(self) -> Dict:
        """Get all prompts for admin interface"""
        return self.prompts_data

    def get_active_prompts(self) -> List[Dict]:
        """Get flat list of all active prompts with category info"""
        prompts = []
        for category in self.prompts_data.get("categories", []):
            for prompt in category.get("prompts", []):
                if prompt.get("active", True):
                    prompts.append(
                        {
                            "category_id": category["id"],
                            "category_name": category["name"],
                            **prompt,
                        }
                    )
        return prompts

    async def _run_single_prompt(
        self,
        prompt_data: Dict,
        vector_store_id: str,
        semaphore: asyncio.Semaphore,
        assistant_id: str,
    ) -> Dict:
        """
        Run a single prompt against the vector store using Assistants API

        Uses semaphore to limit concurrent API calls
        """
        async with semaphore:
            try:
                user_prompt = f"""Question: {prompt_data['question']}

Search guidance: {prompt_data['prompt']}

Search the uploaded documents and provide the answer. If you find relevant requirements, quote the specific text. If no requirements are found, respond with exactly: "No requirements found."
"""

                # Create a thread with the prompt
                thread = self.client.beta.threads.create()

                # Add the message
                self.client.beta.threads.messages.create(
                    thread_id=thread.id, role="user", content=user_prompt
                )

                # Run the assistant
                run = self.client.beta.threads.runs.create_and_poll(
                    thread_id=thread.id, assistant_id=assistant_id, timeout=60
                )

                if run.status != "completed":
                    raise Exception(f"Run failed with status: {run.status}")

                # Get the response
                messages = self.client.beta.threads.messages.list(thread_id=thread.id)
                answer = messages.data[0].content[0].text.value

                # Clean up thread
                self.client.beta.threads.delete(thread.id)

                # Determine status based on response
                if "no requirements found" in answer.lower():
                    status = "no_requirement"
                    source = None
                else:
                    status = "requirement_found"
                    # Try to extract source from response
                    source = self._extract_source(answer)

                logger.info(f"Completed prompt: {prompt_data['id']} - {status}")

                return {
                    "prompt_id": prompt_data["id"],
                    "question": prompt_data["question"],
                    "prompt": prompt_data["prompt"],
                    "answer": answer,
                    "source": source,
                    "status": status,
                    "error": None,
                }

            except Exception as e:
                logger.error(f"Error on prompt {prompt_data['id']}: {str(e)}")
                return {
                    "prompt_id": prompt_data["id"],
                    "question": prompt_data["question"],
                    "prompt": prompt_data["prompt"],
                    "answer": None,
                    "source": None,
                    "status": "error",
                    "error": str(e),
                }

    def _extract_source(self, answer: str) -> Optional[str]:
        """Try to extract source citation from answer"""
        # Look for common citation patterns
        import re

        patterns = [
            r"Section\s+[\d.]+",
            r"Page\s+\d+",
            r"Document:\s*[^,\n]+",
            r"Spec-\d+",
            r"per\s+[^,\n]+specification",
        ]

        for pattern in patterns:
            match = re.search(pattern, answer, re.IGNORECASE)
            if match:
                return match.group(0)

        return None

    async def generate_checklist(
        self,
        vector_store_id: str,
        project_name: str,
        customer: Optional[str] = None,
        category_ids: Optional[List[str]] = None,
    ) -> Dict:
        """
        Generate a complete pre-meeting checklist by running all prompts in parallel

        Args:
            vector_store_id: OpenAI Vector Store ID containing project documents
            project_name: Name of the project
            customer: Optional customer name
            category_ids: Optional list of category IDs to filter (None = all)

        Returns:
            Complete checklist with all prompt results organized by category
        """
        logger.info(f"Generating checklist for project: {project_name}")
        logger.info(f"Using vector store: {vector_store_id}")

        # Get active prompts, optionally filtered by category
        active_prompts = self.get_active_prompts()
        if category_ids:
            active_prompts = [
                p for p in active_prompts if p["category_id"] in category_ids
            ]

        logger.info(
            f"Running {len(active_prompts)} prompts with max {self.max_concurrent} concurrent"
        )

        # Create an assistant with file_search tool for this checklist run
        assistant = self.client.beta.assistants.create(
            name=f"Checklist Assistant - {project_name}",
            instructions="""You are an expert manufacturing requirements analyst.
Your task is to search the provided documents and answer specific questions about requirements.

IMPORTANT RULES:
1. If you find relevant requirements, quote the specific text and cite the source
2. If no requirements are found, respond with exactly: "No requirements found."
3. Be concise - extract only what directly answers the question
4. Include section numbers, page references, or document names when available""",
            model=self.model,
            tools=[{"type": "file_search"}],
            tool_resources={"file_search": {"vector_store_ids": [vector_store_id]}},
        )
        logger.info(f"Created assistant: {assistant.id}")

        try:
            # Create semaphore for rate limiting
            semaphore = asyncio.Semaphore(self.max_concurrent)

            # Run all prompts in parallel
            tasks = [
                self._run_single_prompt(
                    prompt, vector_store_id, semaphore, assistant.id
                )
                for prompt in active_prompts
            ]

            start_time = datetime.now()
            results = await asyncio.gather(*tasks)
            elapsed = (datetime.now() - start_time).total_seconds()

            logger.info(f"Completed {len(results)} prompts in {elapsed:.1f} seconds")
        finally:
            # Clean up assistant
            self.client.beta.assistants.delete(assistant.id)
            logger.info(f"Deleted assistant: {assistant.id}")

        # Organize results by category
        categories_result = self._organize_by_category(results)

        # Calculate summary stats
        stats = self._calculate_stats(results)

        return {
            "project_name": project_name,
            "customer": customer,
            "vector_store_id": vector_store_id,
            "created_at": datetime.utcnow().isoformat(),
            "generation_time_seconds": elapsed,
            "categories": categories_result,
            "statistics": stats,
        }

    def _organize_by_category(self, results: List[Dict]) -> List[Dict]:
        """Organize flat results into category structure"""
        # Build category lookup from prompts data
        categories = {}
        for cat in self.prompts_data.get("categories", []):
            categories[cat["id"]] = {
                "id": cat["id"],
                "name": cat["name"],
                "order": cat.get("order", 99),
                "items": [],
            }

        # Assign results to categories
        for result in results:
            # Find which category this prompt belongs to
            for cat in self.prompts_data.get("categories", []):
                for prompt in cat.get("prompts", []):
                    if prompt["id"] == result["prompt_id"]:
                        if cat["id"] in categories:
                            categories[cat["id"]]["items"].append(result)
                        break

        # Sort categories by order and return as list
        sorted_cats = sorted(categories.values(), key=lambda x: x["order"])
        return sorted_cats

    def _calculate_stats(self, results: List[Dict]) -> Dict:
        """Calculate summary statistics for the checklist"""
        total = len(results)
        found = sum(1 for r in results if r["status"] == "requirement_found")
        not_found = sum(1 for r in results if r["status"] == "no_requirement")
        errors = sum(1 for r in results if r["status"] == "error")

        return {
            "total_prompts": total,
            "requirements_found": found,
            "no_requirements": not_found,
            "errors": errors,
            "coverage_percentage": round((found / total) * 100, 1) if total > 0 else 0,
        }

    def save_prompts(self, prompts_data: Dict) -> bool:
        """Save updated prompts to JSON file (for admin interface)"""
        try:
            with open(PROMPTS_FILE, "w") as f:
                json.dump(prompts_data, f, indent=2)
            self.prompts_data = prompts_data
            logger.info("Prompts saved successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to save prompts: {e}")
            return False
