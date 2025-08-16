# Scenario Generator (Multi-Agent System)

## Overview
This project is a **multi-agent system** that generates plausible global scenarios and explores their possible outcomes.  
It is designed as a portfolio project to showcase **agent orchestration with LangChain, OpenAI models, and FastAPI**.  

The system runs locally, outputs results in the terminal, and saves runs as JSON.  

---

## Key Features
- **Multi-Agent Workflow**
  1. **Seed Generator Agent** – creates 2–3 big seed scenarios (e.g. *“China invades Taiwan”*, *“New pandemic emerges”*).  
  2. **Outcome Generator Agent** – expands each seed with 3–4 possible outcomes.  
  3. **Plausibility Checker Agent** – validates outcomes, replaces unrealistic ones.  
  4. **Profit Mapper Agent** – suggests how to make profit from each outcome, with a short explanation.  

- **Scenario Tree**  
  Scenarios expand level by level (3–4 hops deep), forming a branching tree of outcomes.  

- **JSON Data Storage**  
  Each run is saved as JSON for later analysis or visualization.  

- **Terminal Output**  
  Results are printed as an indented tree with profit ideas attached.  

---


### Example terminal output
```text
Seed: China invades Taiwan
 ├─ Outcome: US–Japan announce joint force posture
 │    ↳ Profit: Invest in defense stocks
 │       Explanation: Military build-ups usually benefit defense contractors.
 ├─ Outcome: Semiconductor supply crisis as TSMC halts production
 │    ↳ Profit: Invest in Samsung and Intel stocks
 │       Explanation: TSMC disruption shifts demand to competitors.
 └─ Outcome: Coordinated export controls on China
      ↳ Profit: Short Chinese tech ETFs
         Explanation: Export restrictions weaken Chinese semiconductor firms.
```

### Example saved JSON
```json
{
  "seed": "China invades Taiwan",
  "nodes": [
    {
      "id": "n1",
      "parent_id": null,
      "text": "China invades Taiwan",
      "type": "seed"
    },
    {
      "id": "n2",
      "parent_id": "n1",
      "text": "Semiconductor supply crisis as TSMC halts production",
      "type": "outcome",
      "profit": {
        "idea": "Invest in Samsung and Intel stocks",
        "explanation": "TSMC disruption would shift demand to its competitors."
      }
    }
  ]
}
```

## Tech Stack
- Python + LangChain + LangGraph
- OpenAI (gpt-4o-mini)
- FastAPI (optional local API)
- JSON files

## Project Structure
```text
senario-generator/
├── agents/
│   ├── seed_generator.py
│   ├── outcome_generator.py
│   ├── plausibility_checker.py
│   └── profit_mapper.py
├── core/
│   ├── orchestrator.py   # agent flow logic
│   └── schema.py         # JSON schema definitions
├── main.py               # CLI entry point
├── requirements.txt      # dependencies
└── data/                 # saved JSON runs
```

## Tasks
- [ ] Implement agents in `agents/`
- [ ] Orchestrate flow in `core/orchestrator.py`
- [ ] Define schema in `core/schema.py`
- [ ] CLI flags: `--depth`, `--seed`, `--output`
- [ ] Persist runs to `data/` as JSON
- [ ] Tests (pytest) and sample E2E run
- [ ] Optional FastAPI endpoint