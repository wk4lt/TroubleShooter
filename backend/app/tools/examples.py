from app.tools.registry import registry


# 数值参数:计算两个数的和
@registry.tool(
    name="add_numbers",
    description="计算两个数的和。",
    parameters={
        "type": "object",
        "properties": {
            "a": {"type": "number", "description": "第一个数"},
            "b": {"type": "number", "description": "第二个数"},
        },
        "required": ["a", "b"],
    },
)
def add_numbers(a: float, b: float):
    return {"result": a + b}


# 枚举参数:限制可选值
@registry.tool(
    name="get_service_status",
    description="获取单个服务的运行状态。",
    parameters={
        "type": "object",
        "properties": {
            "service": {
                "type": "string",
                "enum": ["订单服务", "支付网关", "用户中心"],
                "description": "服务名称",
            },
        },
        "required": ["service"],
    },
)
def get_service_status(service: str):
    status_map = {"订单服务": "normal", "支付网关": "degraded", "用户中心": "down"}
    return {"service": service, "status": status_map.get(service, "unknown")}


# 异步工具:async def 也支持
@registry.tool(
    name="summarize",
    description="对一段文本做字数统计。",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "要统计的文本"},
        },
        "required": ["text"],
    },
)
async def summarize(text: str):
    return {"chars": len(text), "words": len(text.split())}
