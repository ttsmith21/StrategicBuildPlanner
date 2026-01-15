"""
Quote Comparison Service - Compare vendor quotes against customer requirements

Workflow:
1. Upload vendor quote document (PDF) with "Important Notes and Assumptions"
2. Extract quote assumptions using OpenAI
3. Compare against checklist requirements (from customer documents)
4. Identify:
   - Matches: Quote assumptions that align with customer requirements
   - Conflicts: Quote assumptions that contradict customer requirements
   - Quote-only: Assumptions in quote not covered by customer docs
   - Customer-only: Requirements from customer not in quote
"""

import os
import json
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

from openai import OpenAI

logger = logging.getLogger(__name__)


class QuoteComparisonService:
    """Service for comparing vendor quotes against customer requirements"""

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_MODEL_PLAN", "gpt-4o")

    async def extract_quote_assumptions(
        self, quote_text: str, project_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract assumptions and notes from a vendor quote document

        Args:
            quote_text: Plain text content from the quote PDF
            project_name: Optional project name for context

        Returns:
            Structured extraction with categorized assumptions
        """
        logger.info(f"Extracting assumptions from quote for project: {project_name}")

        prompt = f"""Analyze this vendor quote document and extract all important notes, assumptions,
and requirements stated by the vendor.

Project: {project_name or 'Unknown'}

QUOTE DOCUMENT:
{quote_text}

Extract and categorize all vendor assumptions into these categories:
1. Material Standards - specifications, country of origin, certifications
2. Fabrication Process - welding codes, ASME stamps, process requirements
3. Dimensional Tolerances - machining, GD&T, surface finish
4. Finishing Requirements - painting, passivation, plating
5. Quality Inspections - testing requirements, NDE, inspections
6. Trial Fits & Functional Tests - assembly, functional testing
7. Packaging & Shipping - crating, protection, handling
8. Documentation - data packages, traceability, certifications

Respond in this JSON format:
{{
  "vendor_name": "<extracted vendor name or 'Unknown'>",
  "quote_number": "<quote/RFQ number if found>",
  "assumptions": [
    {{
      "category_id": "<category from list above, e.g. 'material_standards'>",
      "category_name": "<full category name>",
      "text": "<exact assumption text from quote>",
      "implication": "<what this means for the project>",
      "confidence": <0.0-1.0 how clearly stated>
    }}
  ],
  "general_notes": ["<any other important notes not in categories>"]
}}

Be thorough - capture ALL assumptions, even implied ones. If the quote states
specific standards (AWS, ASME, ASTM, etc.), include those."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)
            result["extracted_at"] = datetime.utcnow().isoformat()
            result["project_name"] = project_name

            logger.info(
                f"Extracted {len(result.get('assumptions', []))} assumptions from quote"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to extract quote assumptions: {str(e)}")
            raise

    async def compare_with_checklist(
        self,
        quote_assumptions: Dict[str, Any],
        checklist: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Compare quote assumptions against checklist requirements

        Args:
            quote_assumptions: Output from extract_quote_assumptions()
            checklist: Checklist result from checklist service

        Returns:
            Comparison results with matches, conflicts, and gaps
        """
        logger.info("Comparing quote assumptions against checklist requirements")

        # Build context from checklist
        checklist_items = []
        for category in checklist.get("categories", []):
            for item in category.get("items", []):
                if item.get("status") == "requirement_found":
                    checklist_items.append(
                        {
                            "category_id": category["id"],
                            "category_name": category["name"],
                            "prompt_id": item["prompt_id"],
                            "question": item["question"],
                            "answer": item["answer"],
                            "source": item.get("source"),
                        }
                    )

        # Build context from quote
        quote_items = quote_assumptions.get("assumptions", [])

        if not checklist_items and not quote_items:
            return {
                "project_name": checklist.get("project_name"),
                "comparison_status": "no_data",
                "message": "No requirements found in checklist and no assumptions in quote",
                "matches": [],
                "conflicts": [],
                "quote_only": quote_items,
                "checklist_only": [],
            }

        # Use AI to find matches and conflicts
        prompt = f"""Compare these vendor quote assumptions against customer requirements.

CUSTOMER REQUIREMENTS (from specification documents):
{json.dumps(checklist_items, indent=2)}

VENDOR QUOTE ASSUMPTIONS:
{json.dumps(quote_items, indent=2)}

Analyze each pair and identify:
1. MATCHES - Quote assumption aligns with customer requirement
2. CONFLICTS - Quote assumption contradicts customer requirement (CRITICAL!)
3. QUOTE_ONLY - Assumption in quote not covered by customer requirements
4. CHECKLIST_ONLY - Customer requirement not addressed in quote

For conflicts, be specific about what's different and why it matters.

Respond in this JSON format:
{{
  "matches": [
    {{
      "quote_assumption": "<text from quote>",
      "checklist_requirement": "<text from checklist>",
      "category": "<category name>",
      "alignment_notes": "<how they align>"
    }}
  ],
  "conflicts": [
    {{
      "quote_assumption": "<text from quote>",
      "checklist_requirement": "<text from checklist>",
      "category": "<category name>",
      "conflict_description": "<what's different>",
      "severity": "high" | "medium" | "low",
      "resolution_suggestion": "<how to resolve>"
    }}
  ],
  "quote_only": [
    {{
      "assumption": "<text from quote>",
      "category": "<category>",
      "recommendation": "<should we add this requirement?>"
    }}
  ],
  "checklist_only": [
    {{
      "requirement": "<text from checklist>",
      "prompt_id": "<id>",
      "category": "<category>",
      "action_needed": "<what vendor should confirm>"
    }}
  ]
}}

Focus especially on:
- Welding codes (AWS D1.1 vs D1.6, etc.)
- Material specifications and country of origin
- Testing requirements (NDT, PMI, hydro)
- Dimensional tolerances
- Documentation requirements"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            comparison = json.loads(response.choices[0].message.content)

            # Add metadata
            comparison["project_name"] = checklist.get("project_name")
            comparison["vendor_name"] = quote_assumptions.get("vendor_name")
            comparison["quote_number"] = quote_assumptions.get("quote_number")
            comparison["compared_at"] = datetime.utcnow().isoformat()
            comparison["statistics"] = {
                "total_matches": len(comparison.get("matches", [])),
                "total_conflicts": len(comparison.get("conflicts", [])),
                "quote_only_count": len(comparison.get("quote_only", [])),
                "checklist_only_count": len(comparison.get("checklist_only", [])),
                "high_severity_conflicts": sum(
                    1
                    for c in comparison.get("conflicts", [])
                    if c.get("severity") == "high"
                ),
            }

            logger.info(
                f"Comparison complete: {comparison['statistics']['total_matches']} matches, "
                f"{comparison['statistics']['total_conflicts']} conflicts "
                f"({comparison['statistics']['high_severity_conflicts']} high severity)"
            )

            return comparison

        except Exception as e:
            logger.error(f"Failed to compare quote with checklist: {str(e)}")
            raise

    async def generate_merge_preview(
        self,
        checklist: Dict[str, Any],
        quote_assumptions: Dict[str, Any],
        comparison: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate a preview of how checklist would look after merging quote info

        Args:
            checklist: Original checklist
            quote_assumptions: Extracted quote assumptions
            comparison: Comparison results

        Returns:
            Merged checklist with conflict highlights
        """
        logger.info("Generating merge preview")

        # Deep copy checklist structure
        merged = {
            "project_name": checklist.get("project_name"),
            "customer": checklist.get("customer"),
            "vendor_name": quote_assumptions.get("vendor_name"),
            "quote_number": quote_assumptions.get("quote_number"),
            "merge_preview": True,
            "created_at": datetime.utcnow().isoformat(),
            "categories": [],
        }

        # Build lookup for conflicts by category
        conflicts_by_category = {}
        for conflict in comparison.get("conflicts", []):
            cat = conflict.get("category", "unknown").lower().replace(" ", "_")
            if cat not in conflicts_by_category:
                conflicts_by_category[cat] = []
            conflicts_by_category[cat].append(conflict)

        # Build lookup for quote-only by category
        quote_only_by_category = {}
        for item in comparison.get("quote_only", []):
            cat = item.get("category", "unknown").lower().replace(" ", "_")
            if cat not in quote_only_by_category:
                quote_only_by_category[cat] = []
            quote_only_by_category[cat].append(item)

        # Process each category
        for category in checklist.get("categories", []):
            cat_id = category["id"]
            merged_category = {
                "id": cat_id,
                "name": category["name"],
                "order": category.get("order", 99),
                "items": [],
                "conflicts": conflicts_by_category.get(cat_id, []),
                "quote_additions": quote_only_by_category.get(cat_id, []),
            }

            # Copy items with merge annotations
            for item in category.get("items", []):
                merged_item = {**item}

                # Check if this item has a conflict
                for conflict in comparison.get("conflicts", []):
                    if conflict.get("checklist_requirement") == item.get("answer"):
                        merged_item["has_conflict"] = True
                        merged_item["conflict"] = conflict
                        break

                # Check if this item has a match
                for match in comparison.get("matches", []):
                    if match.get("checklist_requirement") == item.get("answer"):
                        merged_item["has_match"] = True
                        merged_item["quote_alignment"] = match.get("alignment_notes")
                        break

                merged_category["items"].append(merged_item)

            merged["categories"].append(merged_category)

        # Add summary statistics
        total_conflicts = len(comparison.get("conflicts", []))
        high_severity = sum(
            1 for c in comparison.get("conflicts", []) if c.get("severity") == "high"
        )

        merged["merge_summary"] = {
            "total_conflicts": total_conflicts,
            "high_severity_conflicts": high_severity,
            "total_matches": len(comparison.get("matches", [])),
            "quote_additions": len(comparison.get("quote_only", [])),
            "unaddressed_requirements": len(comparison.get("checklist_only", [])),
            "ready_to_merge": total_conflicts == 0,
            "requires_review": high_severity > 0,
        }

        logger.info(
            f"Merge preview generated: {total_conflicts} conflicts, "
            f"ready_to_merge={merged['merge_summary']['ready_to_merge']}"
        )

        return merged
