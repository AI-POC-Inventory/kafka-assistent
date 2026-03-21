import asyncio
import json
from typing import Dict, Any

from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH
from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.genai import types

import os
import re
import json

os.environ["GOOGLE_API_KEY"] = ""
# =============================
# CONFIG
# =============================
MAX_RETRIES = 1

def extract_json(text: str):
    if not text or text.strip() == "":
        raise ValueError("Empty LLM response")

    # Remove markdown ```json blocks
    text = re.sub(r"```json|```", "", text).strip()

    # Extract first JSON object
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON found in response: {text}")
    print(f"📝 Extracted JSON: {match.group()}")
    return json.loads(match.group())

# =============================
# SUB AGENTS (FIXED NAMES)
# =============================
kafka_admin_agent = RemoteA2aAgent(
    name="kafka_admin_agent",
    description="Kafka admin operations",
    agent_card=f"http://localhost:8080{AGENT_CARD_WELL_KNOWN_PATH}",
)

kafka_user_agent = RemoteA2aAgent(
    name="kafka_user_agent",
    description="Kafka read operations",
    agent_card=f"http://localhost:8000{AGENT_CARD_WELL_KNOWN_PATH}",
)

# =============================
# PLANNER AGENT
# =============================
PLANNER_PROMPT = """
You are a PLANNER.

Return ONLY valid JSON.

Rules:
- Break task into steps
- Check agent card descriptions for kafka_admin_agent and kafka_user_agent to understand capabilities
- Do not assign steps to agents that cannot perform them. The agent card descriptions are the source of truth for what each agent can do.
- Map each step to one tool from agentcard of kafka_admin_agent and kafka_user_agent
- Assign step to agent based on tool
- Add dependencies
- Add conditions if needed

Output format:
{
  "steps": [
    {
      "id": 1,
      "description": "...",
      "agent": "...",
      "message": "...",
      "depends_on": [],
      "condition": null
    }
  ]
}
"""

planner = LlmAgent(
    model="gemini-2.5-flash",
    name="planner",
    instruction=PLANNER_PROMPT,
    sub_agents=[kafka_admin_agent, kafka_user_agent]
)

# =============================
# VERIFIER AGENT
# =============================
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

verifier = LlmAgent(
    model="gemini-2.5-flash",
    name="verifier",
    instruction=VERIFIER_PROMPT,
)

# =============================
# ORCHESTRATOR ENGINE
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
            print(f"🎬 Created new session: {self.session.id}")          

        return self.session
            
    async def run(self, query: str):
        session = await self.get_session()
        print(f"run session: {session.id}")
        plan = await self.create_plan(session, query)
        state = {"results": {}, "retries": {}}

        for step in plan["steps"]:
            await self.execute_step(session, step, state)

        verification = await self.verify(session, plan, state)

        if verification["status"] != "SUCCESS":
            print("⚠️ Replanning triggered...")
            return await self.run(query)

        return state

    # =============================
    # PLAN
    # =============================
    async def create_plan(self, session, query):
        runner = Runner(
            app_name=self.app_name,
            agent=planner,
            artifact_service=self.artifacts_service,
            session_service=self.session_service,
        )

        content = types.Content(role="user", parts=[types.Part(text=query)])
        print(f"🎬 Creating plan for session: {session.id} ")
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

    # =============================
    # EXECUTION
    # =============================
    async def execute_step(self, session, step, state):
        agent_name = step["agent"]
        message = step["message"]

        print(f"\n🚀 Step {step['id']} → {agent_name}")

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

        content = types.Content(role="user", parts=[types.Part(text=message)])


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

        print(f"✅ Result: {result}")

        state["results"][f"step_{step['id']}"] = result

    # =============================
    # VERIFY
    # =============================
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

# =============================
# MAIN
# =============================
async def main():
    orch = Orchestrator()

    query = "Create topic 'test_from_agent_11' if not exists with 10 partitions and RF=1 and print all topics to verify creation"

    result = await orch.run(query)

    print("\n🎯 FINAL STATE:")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())