"""
MCP Server #1: Kafka Admin Tools
Exposes CRUD operations for Kafka management
"""
import asyncio
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .tools import KafkaAdminTools
from security.rbac import RBACEnforcer
from config.settings import Settings

app = FastAPI(title="Kafka Admin MCP Server")
settings = Settings()
admin_tools = KafkaAdminTools(settings.kafka_config)
rbac = RBACEnforcer(settings.ranger_config)


class CreateTopicRequest(BaseModel):
    name: str
    partitions: int = 3
    replication_factor: int = 1
    config: Optional[Dict[str, str]] = None


class CreateUserRequest(BaseModel):
    username: str
    password: str
    groups: list[str] = []


class ACLRequest(BaseModel):
    principal: str
    resource_type: str
    resource_name: str
    operation: str
    permission_type: str = "ALLOW"


class PublishMessageRequest(BaseModel):
    topic: str
    key: Optional[str] = None
    value: str
    headers: Optional[Dict[str, str]] = None


@app.post("/tools/create_topic")
async def create_topic(request: CreateTopicRequest, user_context: Dict = None):
    """Tool 1: Create a new Kafka topic"""
    # Check RBAC permissions
    if not await rbac.check_permission(user_context, "topic", "create", request.name):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    result = await admin_tools.create_topic(
        name=request.name,
        partitions=request.partitions,
        replication_factor=request.replication_factor,
        config=request.config
    )
    return {"status": "success", "topic": request.name, "details": result}


@app.post("/tools/create_user")
async def create_user(request: CreateUserRequest, user_context: Dict = None):
    """Tool 2: Create a new Kafka user"""
    if not await rbac.check_permission(user_context, "user", "create", request.username):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    result = await admin_tools.create_user(
        username=request.username,
        password=request.password,
        groups=request.groups
    )
    return {"status": "success", "user": request.username}


@app.post("/tools/create_acl")
async def create_acl(request: ACLRequest, user_context: Dict = None):
    """Tool 3: Create Kafka ACLs"""
    if not await rbac.check_permission(user_context, "acl", "create", request.resource_name):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    result = await admin_tools.create_acl(
        principal=request.principal,
        resource_type=request.resource_type,
        resource_name=request.resource_name,
        operation=request.operation,
        permission_type=request.permission_type
    )
    return {"status": "success", "acl": result}


@app.get("/tools/view_acls")
async def view_acls(resource_type: Optional[str] = None, user_context: Dict = None):
    """Tool 8: View ACLs"""
    if not await rbac.check_permission(user_context, "acl", "read", "*"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    acls = await admin_tools.list_acls(resource_type)
    return {"acls": acls}


@app.post("/tools/publish_message")
async def publish_message(request: PublishMessageRequest, user_context: Dict = None):
    """Tool 5: Publish messages to Kafka"""
    if not await rbac.check_permission(user_context, "topic", "write", request.topic):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    result = await admin_tools.publish_message(
        topic=request.topic,
        key=request.key,
        value=request.value,
        headers=request.headers
    )
    return {"status": "success", "offset": result}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
