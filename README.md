# Test Case Generator (Python + React)

Generate structured QA test cases from short feature notes. Supports AI (OpenAI) or a lightweight stub for demos. 
Optionally produces a GitLab Merge Request draft.

## Features
- 🧠 AI-assisted or stubbed generation
- 🧩 YAML front-matter + Markdown body
- 🐙 Optional GitLab MR draft output
- 🐳 One-line Docker compose

## Quickstart (Docker)
```bash
cp .env.example .env   
docker compose up --build
# Open http://localhost:8000

## Quickstart (Dev)

### Backend
```bash
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
# http://localhost:8000

### Frontend
cd frontend
npm ci
npm run dev
# http://localhost:5173

### API
POST /api/generate
Body: { "app": "APP1", "area": "Billing > Invoices", "suite": "Regression", "priority": "P2", "notes": "..." }

Mode: ?mode=ai or ?mode=stub (or env LLM_PROVIDER=openai|stub)
POST /api/create-mr

Requires: GITLAB_BASE_URL, GITLAB_PROJECT_ID, GITLAB_TOKEN
If not set, endpoint returns a friendly message (demo users can skip this).

Env Vars

LLM_PROVIDER=stub (default) or openai

OPENAI_API_KEY=... (required if openai)

OPENAI_MODEL=gpt-4o-mini (default)

Roadmap

Jira issue draft output

Slack notification

Custom templates per team


You can also add a **Docker** quickstart section:

```md