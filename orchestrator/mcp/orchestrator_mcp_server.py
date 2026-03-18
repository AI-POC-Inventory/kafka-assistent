# orchestrator_mcp_server.py
from mcp import MCPServer
from mcp.types import Request, Response
import requests

ADK_ORCHESTRATOR_URL = "http://localhost:8010/route"

server = MCPServer("orchestrator-mcp")

@server.method("route")
def route(req: Request):
    payload = {
        "user_id": req.params.get("user_id"),
        "intent": req.params.get("intent"),
        "input": req.params.get("input")
    }
    r = requests.post(ADK_ORCHESTRATOR_URL, json=payload)
    return Response(result=r.json())

if __name__ == "__main__":
    server.run(port=8005)
