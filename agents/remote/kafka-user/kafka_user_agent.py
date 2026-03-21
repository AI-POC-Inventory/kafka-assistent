import os
import uvicorn
from dotenv import load_dotenv
from google.genai import types
from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService # Optional
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from mcp import StdioServerParameters
import logging
from google.adk.a2a.utils.agent_to_a2a import to_a2a

logging.getLogger().setLevel(logging.ERROR)


import warnings

os.environ["GOOGLE_API_KEY"] = ""

port = int(os.environ.get("PORT", 8080))

warnings.filterwarnings(
    "ignore",
    message=".*BASE_AUTHENTICATED_TOOL.*"
)

warnings.filterwarnings(
    "ignore",
    message=".*non-text parts in the response.*"
)

def get_agent():
  """Creates an ADK Agent equipped with tools from the MCP Server."""
  toolset = McpToolset(
      connection_params=StreamableHTTPConnectionParams(
          url = "https://kafka-user-mcp-989713142030.asia-south1.run.app/mcp", 
      ),
  )

  # Use in an agent
  root_agent = LlmAgent(
      model='gemini-2.5-flash', 
      name='enterprise_assistant',
      instruction="""
            You are a Kafka operations assistant for kafka user only.
            You are not allowed to perform any administrative tasks or provide information about Kafka cluster configuration, security settings, or any other sensitive information.
            You can only perform operations 
                Kafka topics - such as listing topics, describing topics, and providing information about topic configurations.
                Kafka consumer groups - such as listing consumer groups, describing consumer groups, and providing information about consumer group offsets.
                Kafka producers - such as providing information about producer performance and troubleshooting producer issues.
                 Kafka consumers - such as providing information about consumer performance and troubleshooting consumer issues.
            Always use MCP tools for Kafka operations.
            Do not guess responses.
            """,
      tools=[toolset], 
  )
  return root_agent

  

root_agen = get_agent()


app = to_a2a(root_agen,port=int(os.environ.get("PORT", 8000)), host="localhost", protocol="http") 

def main():
    print(f"🚀 Starting A2A agent on port {port}")

    uvicorn.run(
        "kafka_user_agent:app",  # module:app
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        reload=False
    )

# --- Run ---
if __name__ == "__main__":
    main()