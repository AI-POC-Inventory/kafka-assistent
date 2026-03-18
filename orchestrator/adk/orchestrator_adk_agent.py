# orchestrator_adk_agent.py
from adk import ADKAgent, A2AClient
import requests

RANGER_URL = "http://ranger:6080/check"
AGENT1_URL = "http://localhost:8020/handle"
AGENT2_URL = "http://localhost:8030/handle"

agent = ADKAgent(name="orchestrator-agent")

def ranger_check(user_id, action, resource):
    r = requests.post(RANGER_URL, json={
        "user": user_id,
        "action": action,
        "resource": resource
    })
    result = r.json()
    return result.get("allowed", False)

@agent.skill("route")
def route(context):
    user = context["user_id"]
    intent = context["intent"]

    if not ranger_check(user, "execute", intent):
        return {"error": "Access denied by Ranger"}

    if intent in ["createTopic", "describeTopic", "publish", "streamJoin"]:
        response = requests.post(AGENT1_URL, json=context)
    else:
        response = requests.post(AGENT2_URL, json=context)

    return response.json()

agent.run(port=8010)
