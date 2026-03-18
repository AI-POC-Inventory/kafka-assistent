# agent.py (modify get_tools_async and other parts as needed)
# ./adk_agent_samples/mcp_agent/agent.py
import os
import asyncio
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
logging.getLogger().setLevel(logging.ERROR)
os.environ["GOOGLE_API_KEY"] = "AIzaSyDs1INsiDMOqeAgxIUiEsPik-NAUoKuW9U"
#"AIzaSyAuZdO93rvHdxbYtAXs_cNZM9bfeYqh1oE"
#AIzaSyDs1INsiDMOqeAgxIUiEsPik-NAUoKuW9U
# --- Step 1: Agent Definition ---

import warnings

# Suppress ADK experimental warning
warnings.filterwarnings(
    "ignore",
    message=".*BASE_AUTHENTICATED_TOOL.*"
)

# Suppress function_call warning
warnings.filterwarnings(
    "ignore",
    message=".*non-text parts in the response.*"
)

async def get_agent_async():
  """Creates an ADK Agent equipped with tools from the MCP Server."""
  toolset = McpToolset(
      connection_params=StreamableHTTPConnectionParams(
          url = "https://kafka-mcp-989713142030.asia-south1.run.app/mcp", 
      ),
  )

  # Use in an agent
  root_agent = LlmAgent(
      model='gemini-2.5-flash', 
      name='enterprise_assistant',
      instruction="""
            You are a Kafka operations assistant.
            Always use MCP tools for Kafka operations.
            Do not guess responses.
            """,
      tools=[toolset], 
  )
  return root_agent, toolset

# --- Step 2: Main Execution Logic ---
async def async_main():
  session_service = InMemorySessionService()
  artifacts_service = InMemoryArtifactService()

  session = await session_service.create_session(
      state={}, app_name='mcp_kafka_app', user_id='user_fs'
  )

  query = "list all topicsr"
  print(f"User Query: '{query}'")
  content = types.Content(role='user', parts=[types.Part(text=query)])

  root_agent, toolset = await get_agent_async()

  runner = Runner(
      app_name='mcp_kafka_app',
      agent=root_agent,
      artifact_service=artifacts_service, 
      session_service=session_service,
  )

  print("Running agent...")
  events_async = runner.run_async(
      session_id=session.id, user_id=session.user_id, new_message=content
  )

  final_response = ""

  async for event in events_async:
    if event.content and event.content.parts:
        for part in event.content.parts:
            if hasattr(part, "text") and part.text:
                final_response += part.text
  
  print(final_response)

  # Cleanup is handled automatically by the agent framework
  # But you can also manually close if needed:
  print("Closing MCP server connection...")
  await toolset.close()
  print("Cleanup complete.")

if __name__ == '__main__':
  try:
    asyncio.run(async_main())
  except Exception as e:
    print(f"An error occurred: {e}")