# OpenViking Demo Questions

Prerequisite: start CodeGraph with the OpenViking checkout as its `--root`, import the checkout's
documentation with `backend/scripts/import_openviking_demo.py`, and select the
`code-repository-analyzer` Skill. Tool names below are the default names from
`backend/mcp_servers.example.json`; discovered schemas remain authoritative.

| Test question | Expected tool calls | Evidence expected in answer |
| --- | --- | --- |
| `OpenViking Retrieval 模块的入口在哪里？` | `mcp__codegraph__orient`, `mcp__codegraph__search`, `mcp__codegraph__goto` | entry file and symbol |
| `Hierarchical Retrieval 是如何实现的？` | `mcp__codegraph__search`, `mcp__codegraph__get_symbol`, `mcp__codegraph__refs`, optionally `mcp__codegraph__get_file` | implementation symbols and call relationships |
| `find 和 search 的代码实现有什么区别？` | `mcp__codegraph__search`, `mcp__codegraph__get_symbol`, `mcp__codegraph__get_file` | both implementations and behavioral differences grounded in code |
| `Resource 导入最终经过哪些模块？` | `mcp__codegraph__search`, `mcp__codegraph__path`, `mcp__codegraph__refs` | entry-to-storage call chain |
| `Session commit 的调用链是什么？` | `mcp__codegraph__search`, `mcp__codegraph__path`, `mcp__codegraph__refs` | caller/callee chain |
| `Rerank 在代码哪个位置执行？` | `mcp__codegraph__search`, `mcp__codegraph__goto`, `mcp__codegraph__refs` | reranker symbol and invocation point |
| `Vector Index 在系统中由哪个模块负责？` | `mcp__codegraph__search`, `mcp__codegraph__deps`, `mcp__codegraph__goto` | responsible module and dependency evidence |
| `Retrieval 的实际实现是否符合 Architecture 文档？` | `search_knowledge`, `mcp__codegraph__search`, `mcp__codegraph__path`, `mcp__codegraph__goto` | requirements-to-code comparison table |
| `ResourceService 的职责是否符合设计文档？` | `search_knowledge`, `mcp__codegraph__search`, `mcp__codegraph__refs`, `mcp__codegraph__get_file` | responsibility comparison table |
| `Session 的实际实现是否符合文档描述的生命周期？` | `search_knowledge`, `mcp__codegraph__search`, `mcp__codegraph__path`, `mcp__codegraph__refs` | lifecycle stages mapped to implementation calls |
| `Parser → TreeBuilder → Storage 的处理流程在代码中是否真实存在？` | `search_knowledge`, `mcp__codegraph__search`, `mcp__codegraph__path` | documented flow and actual call-chain evidence |
| `文档声明的模块边界在代码中是否被破坏？` | `search_knowledge`, `mcp__codegraph__deps`, `mcp__codegraph__rdeps`, `mcp__codegraph__refs`, `mcp__codegraph__goto` | boundary rule, dependency/reference evidence, and compliance table |

The table describes the expected routing, not a fabricated execution transcript. Capture the
runtime's `tool_call` / `tool_result` events as the actual tool-call record for a run.
