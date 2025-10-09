# Test Files

This directory contains sample documents for testing the Strategic Build Planner.

## File Types Supported

- **PDF** - Purchase orders, quotes, drawings, specifications
- **DOCX** - Meeting notes, requirements documents
- **TXT** - Plain text notes, transcripts

## Adding Test Files

Place your test documents here to use with the test scripts:

```bash
inputs/
├── RFQ_Sample.pdf
├── Drawing_123.pdf
├── Meeting_Notes.txt
└── Specifications.docx
```

## Privacy Note

⚠️ **Do not commit sensitive customer data to Git!**

The `.gitignore` file excludes all document files in this directory except this README.
