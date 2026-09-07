from app.tools.registry import registry

@registry.tool(
    name="get_time",
    description="获取当前时间。",
    parameters={"type": "object", "properties": {}},
)
def get_time():
    from datetime import datetime

    return {"now": datetime.now().isoformat()}
