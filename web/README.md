# Strategic Build Planner Web Client

Interactive Vite + React single-page app that drives the Strategic Build Planner API with ChatKit-inspired actions for drafting, iterating, and publishing manufacturing plans.

## Prerequisites

- Node.js 18.17+ (recommended: use the same Node runtime as your automation environment)
- FastAPI backend running locally (default: `http://localhost:8001`) with `OPENAI_API_KEY`, Confluence, and Asana credentials configured.

## Setup

1. Install dependencies:

```powershell
cd web
npm install
```

2. Configure the API endpoint:

```powershell
Copy-Item .env.example .env
# edit .env if your FastAPI server runs on a different host/port
```

## Development

```powershell
npm run dev
```

Runs the Vite dev server at <http://localhost:5173>. Requests are proxied directly to the FastAPI service defined in `VITE_API_BASE_URL`.

## Production Build

```powershell
npm run build
```

Outputs a static bundle in `web/dist`. Preview locally with:

```powershell
npm run preview
```

## User Flow

1. **Upload panel** (left): provide project metadata and ingest one or more source files. The API returns a `session_id` used for subsequent drafts.
2. **Plan preview** (center): shows Markdown and JSON representations of the latest plan along with QA metrics and Asana task summaries.
3. **ChatKit panel** (right): send natural-language updates, then trigger actions using the ChatKit-styled buttons:
   - Draft → `/agents/run` (specialist agents; `/draft` is deprecated)
   - Apply Meeting Notes → `/meeting/apply`
   - Publish → `/publish`
   - Create Asana Tasks → `/asana/tasks`
   - QA Grade → `/qa/grade`
   - Browse to Page → opens Confluence URL returned by `/publish`

Acceptance walkthrough:

1. Upload documents and metadata.
2. Click **Draft** to generate the first plan.
3. Iterate via chat messages (Apply Meeting Notes) to refine sections.
4. Publish and open the Confluence page.
5. Provide an Asana project ID and create tasks.
6. Grade the plan quality and review metrics.

## Troubleshooting

- Ensure the backend `.env` is populated with valid OpenAI/Confluence/Asana credentials.
- The browser must allow access to `VITE_API_BASE_URL`; configure CORS on the FastAPI side if you deploy to separate origins.
- Check the browser console for network errors; unsuccessful actions will surface toast banners within the ChatKit panel.
