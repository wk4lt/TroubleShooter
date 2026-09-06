# Repository Guidelines

## Project Structure & Module Organization

The project is split into two applications:

- `backend/app/` contains the FastAPI service. Agent execution lives in `agent/`, HTTP endpoints in `api/`, model integration in `llm/`, built-in tools in `tools/`, and session/file/log persistence in `storage/`.
- `backend/skills/` contains user-facing skills, each normally in `<name>/SKILL.md` with frontmatter metadata.
- `frontend/react-app/src/` contains the React and TypeScript UI. Shared types and API access are in `types.ts` and `api.ts`; reusable views belong in `components/`.
- `dev.sh` manages both services. Runtime files, logs, generated data, and frontend build output are ignored by Git.

## Build, Test, and Development Commands

Install backend dependencies with `python3 -m pip install -r backend/requirements.txt` and frontend dependencies with `cd frontend/react-app && npm install`. Copy `backend/.env.example` to `backend/.env` and configure the LLM credentials.

Use `./dev.sh start` for local development, `./dev.sh status` to inspect services, `./dev.sh logs -f` to follow logs, and `./dev.sh stop` when finished. Build the UI with `./dev.sh build` or `cd frontend/react-app && npm run build`; run the production preview with `npm run preview`. Check both endpoints with `./dev.sh health`.

## Coding Style & Naming Conventions

Follow existing conventions: four spaces and type hints in Python; two spaces, strict TypeScript, semicolons, and single-purpose React components in the frontend. Use `snake_case` for Python modules/functions, `PascalCase` for React components, and `camelCase` for TypeScript variables and functions. Keep imports and public API payloads focused. The frontend build runs `tsc` with unused locals and parameters treated as errors.

## Testing Guidelines

No automated test suite is currently configured. Every change should at least pass `npm run build` for frontend work and `./dev.sh health` plus a focused API or UI smoke test for runtime changes. Add tests alongside new behavior when introducing a test framework; use descriptive names such as `test_session_cleanup_when_idle`.

## Commit & Pull Request Guidelines

Recent commits use short Conventional Commit prefixes, for example `feat: ...`; use `feat:`, `fix:`, `docs:`, or `refactor:` followed by a concise imperative summary. Pull requests should explain the behavior change, list validation commands, link the relevant issue when one exists, and include screenshots or short recordings for UI changes. Call out configuration or migration requirements explicitly.

## Security & Configuration Tips

Keep API keys in `backend/.env`; never commit secrets, session data, logs, or generated files. Preserve session isolation when changing file, task, or event handling, and avoid logging credentials or uploaded content unnecessarily.
