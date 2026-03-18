def make_tool(name: str, desc: str, schema: dict):
    return {
        "name": name,
        "description": desc,
        "input_schema": schema
    }

def make_schema(tools: list):
    return {
        "mcp_version": "0.1",
        "tools": tools
    }
