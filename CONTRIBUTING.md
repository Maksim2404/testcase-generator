# Contributing

Thanks for your interest in improving Test Case Generator! 🎉

## How to contribute

1. **Fork** the repository and create your branch from `main`.
2. Use a clear branch name, e.g.:
   - `feat/ui-dark-mode-toggle`
   - `fix/lint-front-matter`
   - `docs/readme-quickstart`
3. Make focused commits (Conventional Commits encouraged):
   - `feat: add boundary-case section`
   - `fix: correct YAML front-matter key`
   - `docs: update docker quickstart`

4. **Run locally** before opening a PR:
   - Backend: `uvicorn backend.main:app --reload`
   - Frontend: `cd frontend && npm install && npm run dev`
   - Or Docker: `docker compose up --build`

5. **Tests**
   - If you change backend logic, add/adjust tests under `backend/tests/`.
   - Keep CI green (`.github/workflows/ci.yml` runs on push/PR).

6. **Open a Pull Request**
   - Describe what/why.
   - Include screenshots for UI changes.
   - Link any related issues.

## Code style
- Python: keep it simple; follow PEP8 (Black/ruff welcome but not required).
- JS/TS: keep `npm run build` clean; avoid breaking the dev proxy.
- Keep public repo **generic** (no company-specific code/names/URLs).

## Security / secrets
- Never commit API keys or tokens.
- For GitLab/OpenAI integrations, use env vars only.

Thanks again! 🙌
