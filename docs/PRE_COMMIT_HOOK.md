# Pre-Commit Hook Installation

## What It Does

This pre-commit hook prevents accidentally committing sensitive project files from:
- `inputs/` - Customer project documents (PDFs, DOCX, etc.)
- `outputs/` - Generated Strategic Build Plans
- `meetings/` - Meeting transcripts and notes

## Allowed Exceptions

The hook allows these specific files to be committed:
- `inputs/README.md`
- `inputs/README_TEST.md`
- `inputs/sample_project_test.txt`
- `outputs/.gitkeep`
- `meetings/README.md`

## Installation (Windows)

The hook is already installed at `.git/hooks/pre-commit`

### Verify Installation

```powershell
# Check if hook exists
Test-Path .git/hooks/pre-commit

# Test the hook manually
.\.git\hooks\pre-commit
```

## How It Works

When you run `git commit`:
1. The hook checks all staged files
2. If any files from blocked directories are staged (except allowed files)
3. The commit is rejected with an error message
4. You'll see which files need to be unstaged

## Example Output

### Successful Commit (No Blocked Files)
```
Running pre-commit checks...
✅ Pre-commit checks passed!
```

### Blocked Commit
```
Running pre-commit checks...

❌ COMMIT BLOCKED!
The following files should not be committed:
   - inputs/customer_rfq.pdf
   - outputs/Strategic_Build_Plan_ACME.json

These directories contain sensitive project data:
   - inputs/  (project documents)
   - outputs/ (generated plans)
   - meetings/ (meeting transcripts)

Please unstage these files with:
   git reset HEAD <file>
```

## Bypassing the Hook (Emergency Only)

If you absolutely must commit a file (NOT RECOMMENDED):

```powershell
git commit --no-verify -m "Your message"
```

**⚠️ WARNING:** Only use `--no-verify` if you're certain the files don't contain sensitive customer data.

## Testing the Hook

```powershell
# Create a test file in a blocked directory
echo "test" > inputs/test.pdf

# Stage it
git add inputs/test.pdf

# Try to commit (should be blocked)
git commit -m "Test commit"

# Clean up
git reset HEAD inputs/test.pdf
Remove-Item inputs/test.pdf
```

## Troubleshooting

### Hook Not Running

Make sure the file is executable and in the correct location:
```powershell
# Windows - the file should have no extension
Get-Item .git/hooks/pre-commit
```

### PowerShell Execution Policy

If you get execution policy errors:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## Maintenance

To update the hook, edit `.git/hooks/pre-commit` directly.

To add more allowed files, update the `$allowedFiles` array in the script.
