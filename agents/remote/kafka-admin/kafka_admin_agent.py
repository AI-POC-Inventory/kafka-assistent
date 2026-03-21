# ./adk_agent_samples/mcp_agent/agent.py
import os
import asyncio
import logging
import warnings
from dotenv import load_dotenv

from google.genai import types
from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from google.adk.a2a.utils.agent_to_a2a import to_a2a
import uvicorn


import os

port = int(os.environ.get("PORT", 8080))
os.environ["GOOGLE_API_KEY"] = ""

logging.getLogger().setLevel(logging.INFO)

warnings.filterwarnings("ignore", message=".*BASE_AUTHENTICATED_TOOL.*")
warnings.filterwarnings("ignore", message=".*non-text parts in the response.*")

load_dotenv()

def getAgent():
    """Creates a Kafka operations ADK agent equipped with MCP tools."""
    toolset = McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url="https://kafka-admin-mcp-989713142030.asia-south1.run.app/mcp",
        ),
    )

    agent = LlmAgent(
        model="gemini-2.5-flash",
        name="enterprise_kafka_assistant",
        instruction="""
            You are a Kafka operations assistant for kafka admin operation.
            Always use MCP tools for Kafka operations.
            Extract relevant parameters from user queries to determine
            which Kafka MCP tool to use.
            Please ask the user for any missing parameters required for the tools.
            Do not guess results—only respond with actual tool output.

        """,
        tools=[toolset],
    )

    return agent,toolset

agent,toolset = getAgent()

app = to_a2a(agent,port=int(os.environ.get("PORT", 8080))) 
# --- Main entrypoint ---
def main():
    print(f"🚀 Starting A2A agent on port {port}")

    uvicorn.run(
        "kafka_admin_agent:app",  # module:app
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        reload=False
    )

# --- Run ---
if __name__ == "__main__":
    main()


