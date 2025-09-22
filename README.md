📋 Test Case Generator

Generate structured QA test cases from scratch — even when there’s no documentation.
Built to help teams bootstrap quality processes quickly, without wasting hours writing boilerplate.

🚀 What this app does (and why it matters)
Core features

AI/stub generation → structured Markdown test cases (front-matter + sections).

Auto-ID allocation (APP-TC-###) → prevents duplicates, keeps naming consistent.

Linting → enforces required YAML keys (owner, suite, priority, etc.).

GitLab MR creation → test cases land in version control, reviewable & auditable.

Simple UI → prevents double-submits, validates required fields, and links to the MR.

Dark mode toggle → for convenience during long QA sessions.

Practical value

⏱ Save time — trivial tests (search, filters, CRUD) can be generated in minutes.

🗂 Repository of record — version-controlled, searchable test cases instead of scattered docs.

🔍 Visibility — devs & PMs can see test design directly in GitLab.

💸 Cost-effective — no subscriptions; built on existing infra.

🧩 Flexible — choose between AI (OpenAI API) or stub mode (demo/local).

🖼️ Demo UI

<img width="3626" height="1135" alt="screenshot" src="https://github.com/user-attachments/assets/4bdfb694-1626-4893-96c8-aefb24466219" />


👉 The UI is intentionally simple — it’s not meant to be pretty, but to start helping right away.
You can run it locally or via Docker and see how test cases are generated and sent to GitLab.

⚡ Quickstart (Local Dev)
Backend
```bash
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
# -> http://localhost:8000

Frontend
cd frontend
npm install    # (first time to generate package-lock.json)
npm run dev
# -> http://localhost:5173

API examples
# Generate stub test case
curl -X POST "http://localhost:8000/api/generate?mode=stub" \
  -H "Content-Type: application/json" \
  -d '{"app":"APP1","area":"Work Orders > Time Logs","suite":"Regression","priority":"P2","notes":"User can add a time log with duration & comment"}'

# Create MR (stub fallback → writes to /app/out)
curl -X POST "http://localhost:8000/api/create-mr" \
  -H "Content-Type: application/json" \
  -d '{"app":"APP1","area":"Work Orders > Time Logs","markdown":"---\nid: APP1-TC-001\napp: APP1\narea: Work Orders > Time Logs\nsuite: Regression\npriority: P2\n---\n# Example"}'

🐳 Quickstart (Docker)
cp .env.example .env
docker compose up --build
# -> backend on http://localhost:8000, frontend on http://localhost:5173
```

⚙️ Configuration

Environment variables:
- LLM_PROVIDER=stub (default) or openai
- OPENAI_API_KEY=... (required if using OpenAI)
- OPENAI_MODEL=gpt-4o-mini (default)
- GITLAB_BASE_URL, GITLAB_PROJECT_ID, GITLAB_TOKEN → for real MR creation
(without these, MR drafts are written to /app/out/ for demo use)

📌 Roadmap

 Jira issue draft output
 Slack notification (stubbed → /app/out/slack.json)
 Custom templates per team
 UI polish (batch input, multi-case generation)

👩‍💻 Contributing

Yes, contributions are welcome!
This is public — outside contributors can fork the repo, submit pull requests, or open issues.
If you’d like to extend prompts, templates, or UI features, PRs are appreciated.

📊 Repo insights

This repo is structured for visibility:
CI/CD: GitHub Actions (backend, frontend, Docker) — badge at top.
Dependency graph / security scanning: enabled via GitHub settings.
Discussions: can be enabled if you want Q&A/community chat.
Insights (commits, code frequency): useful for recruiters to see activity.

📄 License

MIT — free to use, fork, and adapt.
