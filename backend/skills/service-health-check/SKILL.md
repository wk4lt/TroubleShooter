---
name: service-health-check
description: 服务健康巡检:检查核心服务运行状态并生成诊断报告。
---

# 服务健康巡检

## 步骤

1. 调用 `get_time` 工具获取当前时间,作为巡检时间点。
2. 对每个核心服务(订单服务、支付网关、用户中心),分别调用 `search_database` 工具查询其运行状态。
3. 若某服务状态为 `degraded` 或 `down`,标记为异常并说明。
4. 汇总所有结果,调用 `generate_file` 工具生成一份 Markdown 报告(文件名 `health_report.md`,file_type=`markdown`)。
5. 输出巡检结论:哪些服务正常、哪些异常,异常服务给出建议。

## 输出格式

按服务逐一列出状态,异常服务重点说明,最后附上报告下载信息。
