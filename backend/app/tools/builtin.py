from app.tools.registry import registry

_DB_ROWS = [
    {"id": 1, "name": "订单服务", "status": "normal"},
    {"id": 2, "name": "支付网关", "status": "degraded"},
    {"id": 3, "name": "用户中心", "status": "down"},
]


@registry.tool(
    name="search_database",
    description=(
        "查询内部服务数据库,获取指定服务的运行状态。"
        "当用户询问某个服务的状态、健康度或是否正常时,必须调用此工具获取真实数据。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "keyword": {
                "type": "string",
                "description": "服务名称关键字,例如:支付网关、订单服务、用户中心",
            }
        },
        "required": ["keyword"],
    },
)
def search_database(keyword: str):
    matches = [row for row in _DB_ROWS if keyword in row["name"] or keyword in row["status"]]
    return {"total": len(matches), "rows": matches}


@registry.tool(
    name="get_time",
    description="获取当前时间。",
    parameters={"type": "object", "properties": {}},
)
def get_time():
    from datetime import datetime

    return {"now": datetime.now().isoformat()}
