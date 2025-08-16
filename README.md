# Scenario Generator (Multi‑Agent + Interactive Tree UI)

## Overview
This project generates outcomes for a user‑provided scenario using four experts (geo, economy, tech, social) and visualizes a 2‑round tree in a React UI. Each leaf also includes a concrete investment suggestion.

- Agents (round 1): each expert suggests 1 outcome → 4 nodes
- Agents (round 2): for each of those 4, all experts suggest 1 child → 16 leaves
- Profit mapper: adds a single "Invest in {TICKER/ETF/company}" idea with a short explanation to every leaf
- Output saved to `data/final.json` and displayed as a clickable tree UI

## Tech Stack
- Python (LangChain) with OpenAI‑compatible clients (Grok/xAI preferred, OpenAI/Azure supported)
- FastAPI + Uvicorn (serves `/api/tree` and built UI)
- React (Vite) + `react-d3-tree` for visualization

## Setup
1) Create and activate venv (Git Bash)
```bash
python -m venv .venv
source .venv/Scripts/activate
unalias python 2>/dev/null || true
```

2) Install backend deps
```bash
pip install -r requirements.txt
```

3) Environment variables
- Preferred: Grok (xAI OpenAI‑compatible)
```env
GROK_API_KEY=your_xai_api_key
# optional
GROK_BASE_URL=https://api.x.ai/v1
```
- Or OpenAI
```env
OPENAI_API_KEY=your_openai_key
MODEL_NAME=gpt-4o-mini
```
- Or Azure OpenAI
```env
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_API_KEY=...
OPENAI_API_VERSION=...
GPT_4O_MINI_DEPLOYMENT_NAME=...
```

## Generate the tree JSON
Run the scenario builder (uses Grok first if `GROK_API_KEY` is set):
```bash
python main.py --debug
# When prompted: Insert scenario:
# type your scenario, e.g. "US formally recognizes Taiwan as independent"
```
This writes the result to `data/final.json`.

## Run the servers
Option A: Live dev with Vite (recommended)
```bash
# Terminal 1: FastAPI for API only
uvicorn server.server:app --reload --port 8000

# Terminal 2: Vite dev server (auto reloads UI)
cd ui
npm install
npm run dev
```
Open `http://localhost:5173`. The UI proxies `/api` calls to `http://localhost:8000`.

Option B: Serve built UI via FastAPI
```bash
cd ui && npm install && npm run build && cd ..
uvicorn server.server:app --reload --port 8000
```
Open `http://localhost:8000`.

## UI controls
- Zoom: mouse wheel (now allows deep zoom)
- Pan: drag canvas
- Node clicks:
  - Click any node to see its full details in the left panel (outcome, explanation, profit idea & explanation)
- Label placement rules:
  - Root text centered above the node
  - Level‑1 children: two labels to the left, two labels to the right
  - Leaves: labels below; leftmost below‑left, rightmost below‑right, middle two centered below

## Output format
`data/final.json` shape:
```json
{
  "scenario": "...",
  "children": [
    {
      "expert": "geo|econ|tech|social",
      "outcome": "...",
      "explanation": "...",
      "profit": null,
      "children": [
        {
          "expert": "geo|econ|tech|social",
          "outcome": "...",
          "explanation": "...",
          "profit": {"idea": "Invest in ...", "explanation": "..."},
          "children": []
        }
      ]
    }
  ]
}
```

## Notes on prompts & constraints
- Outcomes: single short sentence (≤ 14 words & ≤ 120 chars), present tense, simple words
- Explanation: one sentence (18–40 words), plain language
- Profit mapper: idea must be exactly "Invest in {TICKER/ETF/company}", no diversify/short/hedge

## Troubleshooting
- Python alias: ensure venv python is used
```bash
which python
# should point to .venv/Scripts/python
```
- If you change the UI and don’t see updates: use Vite (`npm run dev`) or rebuild (`npm run build`) and hard refresh
- If Azure filters block content, Grok is recommended (`GROK_API_KEY`) for fewer policy issues