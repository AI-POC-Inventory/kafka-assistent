import asyncio
import json
import re
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.genai import types

load_dotenv()

app = FastAPI()

# =============================
# REQUEST MODEL
# =============================
class QueryRequest(BaseModel):
    query: str


# =============================
# UTILS
# =============================
def extract_json(text: str):
    if not text or text.strip() == "":
        raise ValueError("Empty LLM response")

    text = re.sub(r"```json|```", "", text).strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    print("Extracted JSON string:", match.group() if match else "No JSON found")
    if not match:
        raise ValueError("No JSON found")

    return json.loads(match.group())


# =============================
# AGENTS
# =============================
kafka_admin_agent = RemoteA2aAgent(
    name="kafka_admin_agent",
    description="Kafka admin operations",
    agent_card="kafka_admin_agent_card.json",
)

kafka_user_agent = RemoteA2aAgent(
    name="kafka_user_agent",
    description="Kafka read operations",
    agent_card="kafka_user_agent_card.json",
)

def load_agent_capabilities():
    agents = {
        "kafka_admin_agent": "kafka_admin_agent_card.json",
        "kafka_user_agent": "kafka_user_agent_card.json"
    }

    capabilities = {}

    for agent_name, path in agents.items():
        with open(path) as f:
            card = json.load(f)

        tools_list = card.get("capabilities", {}).get("tools", [])

        tools = []
        for tool in tools_list:
            tools.append({
                "name": tool.get("name"),
                "description": tool.get("description", ""),
                "parameters": tool.get("parameters", {})
            })

        capabilities[agent_name] = tools

    print("Loaded agent capabilities:", capabilities)
    return capabilities

def format_capabilities(capabilities: dict) -> str:
    text = ""

    for agent, tools in capabilities.items():
        text += f"\nAgent: {agent}\n"
        for tool in tools:
            text += f"- {tool['name']}"
            if tool.get("description"):
                text += f": {tool['description']}"
            text += "\n"

    return text
all_agent_capabilities = format_capabilities(load_agent_capabilities())

def build_planner_prompt():
    capabilities = load_agent_capabilities()
    formatted_caps = format_capabilities(capabilities)

    return f"""
You are a PLANNER.

Return ONLY valid JSON.

RULES:
- Break task into steps
- Assign correct agent and tool based on {formatted_caps} 
- Use ONLY the tools listed above
- DO NOT hallucinate tools

OUTPUT FORMAT (STRICT):
{{
  "steps": [
    {{
      "id": 1,
      "description": "...",
      "agent": "...",
      "message": {{
        "tool": "...",
        "kwargs": {{}}
      }},
      "depends_on": [],
      "condition": null
    }}
  ]
}}
"""

VERIFIER_PROMPT = """
You are a VERIFIER.

Input:
- Plan
- Execution Results

Decide:
- SUCCESS
- RETRY
- REPLAN

Return JSON:
{
  "status": "SUCCESS | RETRY | REPLAN",
  "reason": "...",
  "failed_step": optional step id
}
"""
planner = LlmAgent(
    model="gemini-2.5-flash",
    name="planner",
    instruction=build_planner_prompt(),
)

verifier = LlmAgent(
    model="gemini-2.5-flash",
    name="verifier",
    instruction=VERIFIER_PROMPT,
)


# =============================
# ORCHESTRATOR
# =============================
class Orchestrator:
    def __init__(self):
        self.session_service = InMemorySessionService()
        self.artifacts_service = InMemoryArtifactService()
        self.session = None
        self.app_name = "orchestrator"

    async def get_session(self):
        if not self.session:
            self.session = await self.session_service.create_session(
                state={},
                app_name=self.app_name,
                user_id="user"
            )
        return self.session

    async def run(self, query: str):
        session = await self.get_session()
        print("Creating execution plan...")
        plan = await self.create_plan(session, query)
        print("Execution plan created:", plan)
        state = {"results": {}}
        print("Execution plan created:", plan)

        for step in plan["steps"]:
            print(f"Executing step {step['id']} with agent {step['agent']}...")    
            await self.execute_step(session, step, state)
        print("All steps executed. Verifying results...")
        verification = await self.verify(session, plan, state)

        if verification["status"] != "SUCCESS":
            raise Exception("Execution failed after verification")

        return state["results"]

    async def create_plan(self, session, query):
        print("Creating execution plan...")
        runner = Runner(
            app_name=self.app_name,
            agent=planner,
            artifact_service=self.artifacts_service,
            session_service=self.session_service,
        )

        print("Running planner agent...")    
        content = types.Content(role="user", parts=[types.Part(text=query)])
        print("Content for planner:", content)
        events = runner.run_async(
            session_id=session.id,
            user_id=session.user_id,
            new_message=content,
        )
        print("Running planner agent...")    
        content = types.Content(role="user", parts=[types.Part(text=query)])
        events = runner.run_async(
            session_id=session.id,
            user_id=session.user_id,
            new_message=content,
        )
        response = ""
        async for event in events:
            if event.content:
                for p in event.content.parts:
                    if hasattr(p, "text"):
                        response += p.text

        return extract_json(response)

    async def execute_step(self, session, step, state):
        agent_name = step["agent"]

        target_agent = (
            kafka_admin_agent if agent_name == "kafka_admin_agent"
            else kafka_user_agent
        )

        runner = Runner(
            app_name=self.app_name,
            agent=target_agent,
            artifact_service=self.artifacts_service,
            session_service=self.session_service,
        )
        print(f"Executing step {step['id']} with agent {agent_name} and message: {step['message']}")
        content = types.Content(
            role="user",
            parts=[types.Part(text=json.dumps(step["message"]))]
        )
        print(f"Content for step {step['id']}:", content)

        events = runner.run_async(
            session_id=session.id,
            user_id=session.user_id,
            new_message=content,
        )

        result = ""
        async for event in events:
            if event.content:
                for p in event.content.parts:
                    if hasattr(p, "text"):
                        result += p.text

        state["results"][f"step_{step['id']}"] = result

    async def verify(self, session, plan, state):
        runner = Runner(
            app_name=self.app_name,
            agent=verifier,
            artifact_service=self.artifacts_service,
            session_service=self.session_service,
        )

        payload = {
            "plan": plan,
            "results": state["results"]
        }

        content = types.Content(
            role="user",
            parts=[types.Part(text=json.dumps(payload))]
        )

        events = runner.run_async(
            session_id=session.id,
            user_id=session.user_id,
            new_message=content,
        )

        response = ""
        async for event in events:
            if event.content:
                for p in event.content.parts:
                    if hasattr(p, "text"):
                        response += p.text

        return extract_json(response)


orch = Orchestrator()

# =============================
# API ENDPOINT
# =============================
@app.post("/run")
async def run_query(req: QueryRequest):
    try:
        print("Received query:", req.query)
        result = await orch.run(req.query)
        return {
            "query": req.query,
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))