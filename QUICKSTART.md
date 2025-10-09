# Quick Start Guide - Strategic Build Planner

## ✅ Setup Complete!

Your native Windows environment is ready. Here's what we've set up:

### Environment
- ✅ Python 3.13 virtual environment (`.venv`)
- ✅ All dependencies installed (OpenAI, Jinja2, Requests, etc.)
- ✅ Production-ready code using OpenAI Responses API
- ✅ VS Code configuration with tasks and debugger

### What You Need Now

**1. Get your OpenAI API Key**
   - Visit: https://platform.openai.com/api-keys
   - Create a new secret key
   - Copy it (you'll only see it once!)

**2. Configure `.env`**
   ```powershell
   notepad .env
   ```
   
   Edit these lines:
   ```env
   OPENAI_API_KEY=sk-proj-YOUR_ACTUAL_KEY_HERE
   ```
   
   **Confluence is optional** - if you don't have it set up yet, the tool will still work with just local PDF files!

**3. Add Test Files**
   - Place any PDF files (POs, quotes, drawings) in the `inputs/` folder
   - The tool can read PDF, DOCX, TXT, and more

**4. Run Your First Plan**
   ```powershell
   # Activate venv (if not already active)
   .\.venv\Scripts\Activate.ps1
   
   # Run with your test files
   python apqp_starter.py --project "Test Project" --files .\inputs\*.pdf
   ```

---

## 📝 Example Workflow

### Scenario: New ACME Bracket Project

1. **Gather Documents**
   ```
   inputs/
   ├── ACME_PO_12345.pdf
   ├── ACME_Quote_Rev_B.pdf
   └── Bracket_Drawing_v3.pdf
   ```

2. **Run the Planner**
   ```powershell
   python apqp_starter.py `
     --project "ACME Bracket Rev B" `
     --files .\inputs\ACME_*.pdf
   ```

3. **Review Output**
   ```
   outputs/
   ├── Strategic_Build_Plan__ACME_Bracket_Rev_B.md    # Human-readable
   └── Strategic_Build_Plan__ACME_Bracket_Rev_B.json  # Machine-readable
   ```

4. **Check Results**
   - Open the Markdown file in VS Code
   - Review extracted requirements, risks, CTQs
   - Verify open questions are captured

---

## 🔧 Confluence Setup (Optional)

If you want to integrate with your Knowledge Base:

1. **Get API Token**
   - Visit: https://id.atlassian.com/manage-profile/security/api-tokens
   - Create token for "Strategic Build Planner"

2. **Find Parent Page ID**
   - Go to the Confluence page where you want plans published
   - Look at URL: `...pages/123456789/...` ← that's your parent ID

3. **Update `.env`**
   ```env
   CONFLUENCE_BASE_URL=https://northernmfg.atlassian.net
   CONFLUENCE_EMAIL=your-email@northernmfg.com
   CONFLUENCE_API_TOKEN=your-token-here
   CONFLUENCE_SPACE_KEY=KB
   CONFLUENCE_PARENT_PAGE_ID=123456789
   ```

4. **Test CQL Query**
   ```powershell
   python apqp_starter.py `
     --project "Test" `
     --files .\inputs\test.pdf `
     --cql 'space = KB AND label = "customer-acme" AND type = page'
   ```

5. **Publish to Confluence**
   ```powershell
   python apqp_starter.py `
     --project "ACME Bracket" `
     --files .\inputs\*.pdf `
     --cql 'space = KB AND label = "customer-acme"' `
     --publish
   ```

---

## 🎯 VS Code Shortcuts

### Run via Tasks (Ctrl+Shift+P → "Tasks: Run Task")
- **Full Setup (All Steps)** - Complete environment setup
- **Setup: Install Dependencies** - Reinstall packages
- **Run: APQP Assistant (Demo)** - Quick demo run

### Debug
- Press **F5** to run with debugger
- Set breakpoints in `apqp_starter.py`
- Inspect variables and execution flow

---

## 🧪 Testing Without API Key

Want to test the structure without OpenAI costs?

1. Comment out the actual API call (lines 362-376 in `apqp_starter.py`)
2. Add mock JSON response for testing
3. Verify file processing, Confluence queries, output generation

---

## 📚 What the AI Does

### Analyzes
- **Contract**: PO vs Quote deltas, pricing, terms
- **Materials**: Stainless grades (304/316/321), thickness, finish
- **Processes**: Welding specs, bend allowances, GD&T
- **Quality**: CTQs, inspection points, PPAP requirements
- **Risks**: Manufacturing challenges and mitigations

### Outputs
- **Structured JSON** with confidence scores
- **Markdown Report** ready for review
- **Open Questions** for missing information
- **Cost Levers** for optimization opportunities

### Example Output Sections
1. Executive Summary
2. Key Requirements (with source citations)
3. Process Flow
4. Tooling & Fixturing Strategy
5. Materials & Finishes
6. Quality Plan (CTQs, inspection)
7. Risk Register (with mitigations)
8. Open Questions (what's missing)
9. Cost Optimization Levers
10. Pack & Ship Requirements

---

## ❓ Troubleshooting

### "OPENAI_API_KEY not set"
→ Edit `.env` and add your API key

### "No inputs found"
→ Add PDF files to `inputs/` folder or check file paths

### "Confluence error"
→ Confluence is optional - remove `--cql` flag to run without it

### "Import jinja2 could not be resolved"
→ Run: `pip install -r requirements.txt`

### PowerShell execution policy error
→ Run: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

---

## 🚀 Next Steps

1. ✅ Get OpenAI API key
2. ✅ Edit `.env` file
3. ✅ Add test PDFs to `inputs/`
4. ✅ Run first plan: `python apqp_starter.py --project "Test" --files .\inputs\*.pdf`
5. ✅ Review output in `outputs/` folder
6. 🔄 (Optional) Set up Confluence integration
7. 🔄 (Optional) Add meeting transcripts support

---

## 💡 Pro Tips

### Label Your Confluence Pages
Add labels like:
- `customer-acme`
- `family-of-parts-brackets`
- `apqp-lessons-learned`

Then query with CQL:
```sql
space = KB AND label = "customer-acme" AND type = page
```

### Use Wildcards for Files
```powershell
# All PDFs in inputs
--files .\inputs\*.pdf

# Specific customer
--files .\inputs\ACME_*.pdf

# All file types
--files .\inputs\*.*
```

### Save Common Commands
Create a `run_acme.ps1`:
```powershell
.\.venv\Scripts\Activate.ps1
python apqp_starter.py `
  --project "ACME Bracket Rev B" `
  --files .\inputs\ACME_*.pdf `
  --cql 'space = KB AND label = "customer-acme"' `
  --publish
```

---

**You're all set! 🎉**

No WSL needed - this is 100% native Windows and works great with:
- GitHub Copilot
- Cursor
- Claude Code
- Any AI coding assistant

The Responses API with Vector Stores handles all the heavy lifting!
