# OpenViking Code Repository Analyzer Demo

This Skill composes two existing services. It does not index source, parse code, or build a RAG
store itself:

- CodeGraph indexes the OpenViking checkout and supplies source facts.
- OpenViking imports the checkout's documentation and supplies design/document facts.

## 1. Prepare the official repository

```bash
git clone https://github.com/volcengine/OpenViking.git /opt/src/OpenViking
```

Pin a commit or tag before evidence-sensitive reviews, and record it in the analysis result. The
repository URL is the official `volcengine/OpenViking` project.

## 2. Configure CodeGraph

Copy `backend/mcp_servers.example.json` to `backend/mcp_servers.json`, replace the placeholder
after `--root` with `/opt/src/OpenViking`, then start the TroubleShooter backend. The runtime
discovers the configured MCP tools at startup and exposes them with the `mcp__codegraph__` prefix.

Equivalent standalone command:

```bash
codegraph mcp serve --root /opt/src/OpenViking --stdio
```

The configuration's `skill_tools.code-repository-analyzer` allowlist keeps the Skill on the
read-only CodeGraph operations: `orient`, `packet_get`, `search`, `get_file`, `get_symbol`,
`goto`, `refs`, `deps`, `rdeps`, `path`, `impact`, and `refresh_index`.

## 3. Import documentation into OpenViking

Start the official OpenViking service, then point both the importer and the Runtime query tool at
the same resource URI:

```bash
export OPENVIKING_RESOURCE_URI=viking://resources/openviking-demo
PYTHONPATH=backend backend/.venv/bin/python backend/scripts/import_openviking_demo.py \
  --repo /opt/src/OpenViking
```

The importer deliberately selects `README.md` plus documentation-oriented top-level directories
(`docs`, `architecture`, `concepts`, `api`, `guides`, `design`, `adr`) when present. It delegates each import to the existing
official `OpenVikingAdapter`; it never imports source code as the primary code-analysis corpus.
Preview the selection without contacting OpenViking:

```bash
PYTHONPATH=backend backend/.venv/bin/python backend/scripts/import_openviking_demo.py \
  --repo /opt/src/OpenViking --dry-run
```

## 4. Run a question

Create a task with `skill` set to `code-repository-analyzer`, for example:

```bash
curl -X POST http://127.0.0.1:8000/api/task \
  -H 'Content-Type: application/json' \
  -H 'X-Session-Id: openviking-demo' \
  -d '{"skill":"code-repository-analyzer","input":"Retrieval 的实际实现是否符合 Architecture 文档？"}'
```

Use the task's SSE stream or `GET /api/task/{task_id}` events as the audit log of actual
`tool_call` and `tool_result` events. Ready-to-run question set and expected routing are in
`examples/openviking_questions.md`.

## Limits

- Results depend on the checked-out commit, CodeGraph index freshness, and imported document set.
- The Skill cannot prove a negative from an incomplete index; it reports `UNKNOWN` instead.
- A CodeGraph server's tool schema is discovered dynamically. Its schema/description overrides
  the default operation names in the examples.
- No live tool calls are possible until the two external services are configured and running.
