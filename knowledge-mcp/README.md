# TroubleShooter Knowledge MCP

该服务是独立于 Agent Runtime 的 Python 3.11+ MCP Server。它使用 LlamaIndex 创建文档与分层节点，并通过
Streamable HTTP 在 `http://127.0.0.1:8010/mcp` 提供受控知识检索能力。

## 启动

```bash
./knowledge-mcp/dev.sh setup
./knowledge-mcp/dev.sh fetch-datasets
./knowledge-mcp/dev.sh ingest
./knowledge-mcp/dev.sh serve
```

`setup` 要求本机有 Python 3.11 或更高版本。它只创建 `knowledge-mcp/.venv`，不会改变现有 Agent Runtime 的
Python 3.9 环境。通过 `backend/mcp_servers.example.json` 配置 Agent Runtime 后，工具会以
`search_knowledge`、`search_runbook`、`get_document`、`get_context` 和 `list_knowledge_bases` 暴露。
`fetch-datasets` 会下载指定公开仓库，并将 Incident-response-on-call-agent 的 runbooks 与
opentelemetry-skill 的 references 规范化为 `COMMON` 知识库。

## 数据和边界

把 Markdown 文档放在 `knowledge/<SUBSYSTEM>/<knowledge_type>/`。支持的类型是 `design_doc`、`runbook`、
`issue`、`fault_case`、`reference` 与 `manual`。Runbook 必须为 `trust_level: curated`；普通文档只作为证据。

服务不会提供 ingest、delete、reindex 或 rebuild MCP Tool。这些仅能由 CLI 管理。Agent Runtime 也不导入
LlamaIndex、向量数据库或文档解析代码。

## 检索与评测

默认管线为 metadata router → LlamaIndex Vector Retriever → BM25 → RRF → exact identifier boost →
NoOp reranker → parent context merge。所有参数集中在 `config.yaml`；开发样本默认 `mock` embedding，可在离线环境
运行。准备好模型后，将 `embedding.provider` 改为 `huggingface`，模型保持可配置。

```bash
./knowledge-mcp/dev.sh eval
```

评测输出 Router Accuracy、Recall@1/5/10 和 MRR。`scripts/eval_retrieval.py --agent-predictions <jsonl>`
还会计算 First Tool、Next Tool 和 Final Decision Accuracy。
