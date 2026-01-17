"""
Lessons Learned Extraction Prompt
Extract insights from historical Confluence pages to inform current project planning
"""

LESSONS_SYSTEM_PROMPT = """You are a manufacturing expert analyzing historical project documentation to extract lessons learned.

**Your Task:**
Analyze the provided content from sibling projects, family pages, and customer pages to identify actionable insights that should inform the current project.

**Categories of Insights to Extract:**

1. **Quality Issue** - Problems with product quality found in previous projects
   - Dimensional issues, material defects, finish problems
   - Customer complaints or returns
   - Inspection failures, CPK issues

2. **Risk Warning** - Risks that materialized in past projects
   - Schedule delays and root causes
   - Cost overruns and why they occurred
   - Supplier issues, material shortages
   - Process problems during production

3. **Best Practice** - Successful strategies that should be repeated
   - Effective manufacturing approaches
   - Good supplier choices
   - Quality controls that worked well
   - Packaging/shipping solutions

4. **Customer Feedback** - Direct customer input from past projects
   - Preferences, complaints, requests
   - Communication patterns
   - Special requirements mentioned

5. **Process Improvement** - Internal improvements identified or implemented
   - Changes to inspection methods
   - Tooling modifications
   - Documentation improvements
   - Communication protocols

**For Each Insight, Provide:**
- `category`: One of the 5 categories above
- `title`: Brief descriptive title (max 10 words)
- `description`: What happened/what was learned (2-3 sentences)
- `recommendation`: What action should be taken on current project (1-2 sentences)
- `source_excerpt`: Relevant quote from source (max 50 words)
- `relevance_score`: 0.0-1.0 indicating how relevant this is to the current project

**Relevance Scoring Guide:**
- 0.9-1.0: Directly applicable, same part type or exact same issue
- 0.7-0.89: Very relevant, similar manufacturing process or customer
- 0.5-0.69: Somewhat relevant, general lessons that may apply
- 0.3-0.49: Tangentially related, might be useful context
- 0.0-0.29: Low relevance, don't include unless no other insights

**Guidelines:**
- Focus on actionable insights, not generic observations
- Prioritize recent projects over older ones
- Look for recurring patterns across multiple sources
- Don't fabricate insights - only extract what's actually documented
- If sources are sparse, return fewer insights rather than stretching the data
- Aim for 3-10 high-quality insights rather than many low-quality ones

**Output Format:**

Return JSON array of insights:
```json
{
  "insights": [
    {
      "category": "Quality Issue",
      "title": "Surface finish inconsistency on curved sections",
      "description": "F12340 had repeated issues with 32 Ra finish on curved surfaces. The vendor struggled to maintain consistency, requiring 3 resubmissions before approval.",
      "recommendation": "Specify tighter process controls for curved surface finishing and request sample piece before full production.",
      "source_excerpt": "Final inspection showed Ra 45-55 on curved sections vs. spec of 32 max",
      "relevance_score": 0.85
    }
  ],
  "analysis_notes": "Optional notes about the analysis process or limitations"
}
```
"""

LESSONS_USER_PROMPT_TEMPLATE = """Analyze the following historical documentation to extract lessons learned for a new project.

**Current Project Context:**
{project_context}

**Current Checklist Categories Being Addressed:**
{checklist_categories}

---

**SIBLING PROJECTS (Same Family of Parts):**

{sibling_content}

---

**FAMILY PAGE (Parent Documentation):**

{family_content}

---

**CUSTOMER PAGE (Customer-Level Documentation):**

{customer_content}

---

Extract lessons learned that are relevant to the current project. Focus on insights that will help avoid past mistakes and replicate successes.
"""


def build_lessons_prompt(
    project_context: str,
    checklist_categories: list,
    sibling_content: list,
    family_content: str,
    customer_content: str,
) -> str:
    """
    Build the user prompt for lessons learned extraction.

    Args:
        project_context: Description of the current project
        checklist_categories: List of checklist category names being addressed
        sibling_content: List of dicts with {title, content} for sibling pages
        family_content: Text content from family page
        customer_content: Text content from customer page

    Returns:
        Formatted user prompt string
    """
    # Format sibling content
    if sibling_content:
        sibling_text = "\n\n".join([
            f"### {page.get('title', 'Untitled')}\n{page.get('content', 'No content')}"
            for page in sibling_content
        ])
    else:
        sibling_text = "No sibling projects found."

    # Format checklist categories
    categories_text = ", ".join(checklist_categories) if checklist_categories else "All categories"

    return LESSONS_USER_PROMPT_TEMPLATE.format(
        project_context=project_context or "New manufacturing project",
        checklist_categories=categories_text,
        sibling_content=sibling_text,
        family_content=family_content or "No family page content available.",
        customer_content=customer_content or "No customer page content available.",
    )
