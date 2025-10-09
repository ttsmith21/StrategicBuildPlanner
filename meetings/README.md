# Meeting Transcripts

Place meeting transcripts here (plain text files).

The application can incorporate meeting notes and discussions into the Strategic Build Plan using the `--meeting` flag.

## Usage

```powershell
python apqp_starter.py `
  --project "Project Name" `
  --files .\inputs\*.pdf `
  --meeting .\meetings\kickoff-transcript.txt
```

## Format

Any plain text format works. The AI will extract relevant information about:
- Customer requirements discussed
- Technical decisions made
- Action items and open questions
- Risk concerns raised
- Timeline commitments
