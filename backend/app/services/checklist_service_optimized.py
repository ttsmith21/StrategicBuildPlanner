"""
Optimized Checklist Service - Category-Batched Assistants API with file_search

Optimization Strategy (Option D - Hybrid):
1. Uses Assistants API with file_search (required for vector store access)
2. Batches prompts by category (37 prompts -> ~9 API calls)
3. Splits large categories (Quality Inspections 15 -> 2 batches of 7-8)
4. Runs all batches in parallel threads
5. Uses structured JSON output for reliable parsing
6. Concise responses to reduce tokens/latency
"""

import os
import json
import asyncio
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from openai import OpenAI

logger = logging.getLogger(__name__)

# Path to prompts JSON file
PROMPTS_FILE = Path(__file__).parent.parent / "data" / "checklist_prompts.json"

# Maximum prompts per batch (to avoid context overflow and accuracy degradation)
MAX_PROMPTS_PER_BATCH = 8


class OptimizedChecklistService:
    """
    Optimized service for generating pre-meeting checklists.

    Key optimizations:
    - Assistants API with file_search for vector store access
    - Category-based batching reduces 37 calls to ~9
    - Parallel execution of all batches using thread pool
    - Structured JSON output for reliability
    """

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_MODEL_ASSISTANTS", "gpt-4o")
        self.prompts_data = self._load_prompts()
        # Max concurrent batches (each batch is one category or sub-category)
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

    def _prepare_batches(
        self, category_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Prepare batches of prompts grouped by category.

        Large categories (>MAX_PROMPTS_PER_BATCH) are split into sub-batches.

        Returns list of batch objects:
        {
            "category_id": str,
            "category_name": str,
            "batch_index": int,  # 0, 1, 2... for split categories
            "prompts": [...]
        }
        """
        batches = []

        for category in self.prompts_data.get("categories", []):
            # Filter by category_ids if specified
            if category_ids and category["id"] not in category_ids:
                continue

            # Get active prompts for this category
            active_prompts = [
                p for p in category.get("prompts", []) if p.get("active", True)
            ]

            if not active_prompts:
                continue

            # Split into sub-batches if too large
            for i in range(0, len(active_prompts), MAX_PROMPTS_PER_BATCH):
                batch_prompts = active_prompts[i : i + MAX_PROMPTS_PER_BATCH]
                batch_index = i // MAX_PROMPTS_PER_BATCH

                batches.append(
                    {
                        "category_id": category["id"],
                        "category_name": category["name"],
                        "batch_index": batch_index,
                        "prompts": batch_prompts,
                    }
                )

        return batches

    def _build_batch_prompt(self, batch: Dict[str, Any]) -> str:
        """
        Build a single prompt that asks all questions in the batch.

        Uses structured format for reliable JSON parsing.
        """
        prompts = batch["prompts"]
        category_name = batch["category_name"]
        num_questions = len(prompts)

        # Build list of IDs for emphasis
        prompt_ids = [p["id"] for p in prompts]
        ids_list = ", ".join(prompt_ids)

        questions_text = "\n".join(
            [
                f"{i+1}. [{p['id']}] {p['question']}\n   Search for: {p['prompt']}"
                for i, p in enumerate(prompts)
            ]
        )

        return f"""You are analyzing manufacturing specification documents for a pre-meeting checklist.

CATEGORY: {category_name}

CRITICAL: You MUST provide exactly {num_questions} results in your response - one for EACH of these prompt IDs: {ids_list}

For each question below, search the uploaded documents:
- If requirements found: Quote specific text (max 2 sentences) and note the source
- If NO requirements found: Set status to "no_requirement" and answer to "No requirements found"

QUESTIONS:
{questions_text}

REQUIRED JSON FORMAT - You MUST include ALL {num_questions} prompt IDs listed above:
{{
  "results": [
    {{
      "prompt_id": "<EXACT id from brackets - e.g. {prompt_ids[0]}>",
      "status": "requirement_found" | "no_requirement",
      "answer": "<quoted text OR 'No requirements found'>",
      "source": "<section/page/document name if found, null if not>"
    }}
  ]
}}

IMPORTANT: Your results array MUST contain exactly {num_questions} objects, one for each prompt ID: {ids_list}
Do NOT skip any prompts. If nothing found, use status "no_requirement"."""

    def _run_batch_sync(
        self,
        batch: Dict[str, Any],
        assistant_id: str,
    ) -> List[Dict]:
        """
        Run a single batch of prompts using Assistants API with file_search.
        This is a synchronous method that runs in a thread pool.

        Returns list of result objects for each prompt in the batch.
        """
        batch_id = f"{batch['category_id']}_{batch['batch_index']}"
        prompt_count = len(batch["prompts"])

        logger.info(f"Running batch {batch_id} with {prompt_count} prompts")
        start_time = datetime.now()

        thread = None
        try:
            user_prompt = self._build_batch_prompt(batch)

            # Create a thread for this batch
            thread = self.client.beta.threads.create()

            # Add the message
            self.client.beta.threads.messages.create(
                thread_id=thread.id, role="user", content=user_prompt
            )

            # Run the assistant
            run = self.client.beta.threads.runs.create_and_poll(
                thread_id=thread.id, assistant_id=assistant_id, timeout=120
            )

            if run.status != "completed":
                raise Exception(f"Run failed with status: {run.status}")

            # Get the response
            messages = self.client.beta.threads.messages.list(thread_id=thread.id)
            response_text = messages.data[0].content[0].text.value

            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"Batch {batch_id} completed in {elapsed:.1f}s")

            # Parse JSON response
            # Try to extract JSON from the response (may have markdown code blocks)
            json_text = response_text
            if "```json" in response_text:
                json_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_text = response_text.split("```")[1].split("```")[0].strip()

            # Debug: log first 500 chars of response if parsing might fail
            logger.debug(
                f"Batch {batch_id} raw response (first 500): {response_text[:500]}"
            )

            parsed = json.loads(json_text)
            results = parsed.get("results", [])

            # Always log what we got vs expected for debugging
            expected_count = len(batch["prompts"])
            expected_ids = [p["id"] for p in batch["prompts"]]
            returned_ids_list = [r.get("prompt_id") for r in results]

            logger.info(
                f"Batch {batch_id}: Expected IDs {expected_ids}, got IDs {returned_ids_list}"
            )

            # Enrich results with original prompt data
            prompt_lookup = {p["id"]: p for p in batch["prompts"]}
            enriched_results = []

            for result in results:
                prompt_id = result.get("prompt_id")
                original_prompt = prompt_lookup.get(prompt_id, {})

                enriched_results.append(
                    {
                        "prompt_id": prompt_id,
                        "question": original_prompt.get("question", ""),
                        "prompt": original_prompt.get("prompt", ""),
                        "answer": result.get("answer"),
                        "source": result.get("source"),
                        "status": result.get("status", "error"),
                        "error": None,
                    }
                )

            # Check for any prompts that weren't in the response
            returned_ids = {r.get("prompt_id") for r in results}
            for prompt in batch["prompts"]:
                if prompt["id"] not in returned_ids:
                    logger.warning(f"Prompt {prompt['id']} missing from batch response")
                    enriched_results.append(
                        {
                            "prompt_id": prompt["id"],
                            "question": prompt.get("question", ""),
                            "prompt": prompt.get("prompt", ""),
                            "answer": None,
                            "source": None,
                            "status": "error",
                            "error": "Missing from batch response",
                        }
                    )

            return enriched_results

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error in batch {batch_id}: {e}")
            # Return error results for all prompts in batch
            return [
                {
                    "prompt_id": p["id"],
                    "question": p.get("question", ""),
                    "prompt": p.get("prompt", ""),
                    "answer": None,
                    "source": None,
                    "status": "error",
                    "error": f"JSON parse error: {str(e)}",
                }
                for p in batch["prompts"]
            ]

        except Exception as e:
            logger.error(f"Error in batch {batch_id}: {str(e)}")
            return [
                {
                    "prompt_id": p["id"],
                    "question": p.get("question", ""),
                    "prompt": p.get("prompt", ""),
                    "answer": None,
                    "source": None,
                    "status": "error",
                    "error": str(e),
                }
                for p in batch["prompts"]
            ]

        finally:
            # Clean up thread
            if thread:
                try:
                    self.client.beta.threads.delete(thread.id)
                except Exception:
                    pass

    async def generate_checklist(
        self,
        vector_store_id: str,
        project_name: str,
        customer: Optional[str] = None,
        category_ids: Optional[List[str]] = None,
    ) -> Dict:
        """
        Generate a complete pre-meeting checklist using optimized batch processing.

        Args:
            vector_store_id: OpenAI Vector Store ID containing project documents
            project_name: Name of the project
            customer: Optional customer name
            category_ids: Optional list of category IDs to filter (None = all)

        Returns:
            Complete checklist with all prompt results organized by category
        """
        logger.info(f"[OPTIMIZED] Generating checklist for project: {project_name}")
        logger.info(f"Using vector store: {vector_store_id}")

        # Prepare batches (categories, split if needed)
        batches = self._prepare_batches(category_ids)
        total_prompts = sum(len(b["prompts"]) for b in batches)

        logger.info(
            f"Prepared {len(batches)} batches for {total_prompts} prompts "
            f"(max {self.max_concurrent} concurrent)"
        )

        # Create an assistant with file_search tool for this checklist run
        assistant = self.client.beta.assistants.create(
            name=f"Checklist Assistant - {project_name}",
            instructions="""You are an expert manufacturing requirements analyst.
Your task is to search the provided documents and answer questions about requirements.

IMPORTANT: Always respond in valid JSON format with the structure specified in the user message.
Search documents thoroughly and quote specific text when requirements are found.""",
            model=self.model,
            tools=[{"type": "file_search"}],
            tool_resources={"file_search": {"vector_store_ids": [vector_store_id]}},
        )
        logger.info(f"Created assistant: {assistant.id}")

        start_time = datetime.now()

        try:
            # Run all batches in parallel using thread pool
            # (Assistants API is synchronous, so we use threads)
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
                futures = [
                    loop.run_in_executor(
                        executor, self._run_batch_sync, batch, assistant.id
                    )
                    for batch in batches
                ]
                batch_results = await asyncio.gather(*futures)

        finally:
            # Clean up assistant
            self.client.beta.assistants.delete(assistant.id)
            logger.info(f"Deleted assistant: {assistant.id}")

        # Flatten results from all batches
        all_results = []
        for results in batch_results:
            all_results.extend(results)

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"[OPTIMIZED] Completed {len(all_results)} prompts in {elapsed:.1f} seconds"
        )

        # Organize results by category
        categories_result = self._organize_by_category(all_results)

        # Calculate summary stats
        stats = self._calculate_stats(all_results)

        return {
            "project_name": project_name,
            "customer": customer,
            "vector_store_id": vector_store_id,
            "created_at": datetime.utcnow().isoformat(),
            "generation_time_seconds": elapsed,
            "optimization": {
                "method": "category_batching",
                "total_batches": len(batches),
                "total_prompts": total_prompts,
            },
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
