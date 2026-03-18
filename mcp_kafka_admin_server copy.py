import os
import logging
from typing import Union
from fastapi import FastAPI, HTTPException
from kafka.admin import KafkaAdminClient, NewTopic
from mcp.server.fastmcp import FastMCP

# --------------------------------------------
# Setup Logging
# --------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kafka-admin")

# --------------------------------------------
# App + MCP Server
# --------------------------------------------
app = FastAPI(title="Kafka Admin Server")
mcp = FastMCP("kafka-admin-server")

# Environment variable for broker address
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "13.223.75.210:9092")

# --------------------------------------------
# Internal Kafka Utility
# --------------------------------------------
def get_admin_client() -> KafkaAdminClient:
    """Create and return a KafkaAdminClient instance."""
    return KafkaAdminClient(
        bootstrap_servers=KAFKA_BROKER,
        request_timeout_ms=5000
    )

# --------------------------------------------
# MCP Tool Definition
# --------------------------------------------
@mcp.tool()
def list_topics() -> Union[list, dict]:
    """Return list of Kafka topics (for MCP clients)."""
    admin = None
    try:
        print("Listing Kafka topics...")
        admin = get_admin_client()
        return list(admin.list_topics())
    except Exception as e:
        logger.error("Error listing Kafka topics: %s", e)
        return {"error": str(e)}
    finally:
        if admin:
            admin.close()

# --------------------------------------------
# REST Endpoints for Testing
# --------------------------------------------

@app.get("/topics")
def list_topics_rest() -> list:
    """List all Kafka topics (REST endpoint)."""
    admin = None
    try:
        admin = get_admin_client()
        topics = list(admin.list_topics())
        return topics
    except Exception as e:
        logger.error("Error listing Kafka topics: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if admin:
            admin.close()

if __name__ == "__main__":
    logger.info(f"Starting MCP server (broker={KAFKA_BROKER})")

    # This is REQUIRED
    mcp.run(transport="streamable-http")
