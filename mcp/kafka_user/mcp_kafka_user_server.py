import os
import logging
from confluent_kafka.admin import AdminClient
from mcp.server.fastmcp import FastMCP
from fastapi import FastAPI

# --------------------------------------------
# Logging
# --------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kafka-admin")

# --------------------------------------------
# FastAPI app
# --------------------------------------------
app = FastAPI(redirect_slashes=False)

@app.get("/")
def health():
    return {"status": "ok"}

# --------------------------------------------
# MCP Server
# --------------------------------------------
mcp = FastMCP(
    "kafka-admin-server",
    host="0.0.0.0",
    port=int(os.environ.get("PORT", 8000)),
    mount_path="/kafka-admin"
)

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "54.225.1.215:9092")

# --------------------------------------------
# Kafka Admin Client
# --------------------------------------------
def get_admin():
    return AdminClient({
        "bootstrap.servers": KAFKA_BROKER
    })

# --------------------------------------------
# MCP Tools
# --------------------------------------------
@mcp.tool()
def list_topics():
    """List Kafka topics"""
    try:
        admin = get_admin()

        # Fetch metadata
        metadata = admin.list_topics(timeout=10)

        topics = list(metadata.topics.keys())

        logger.info(f"Fetched {len(topics)} topics")

        return {
            "status": "success",
            "topics": topics,
            "count": len(topics)
        }

    except Exception as e:
        logger.exception("Error fetching topics")
        return {
            "status": "failed",
            "error": str(e)
        }

# --------------------------------------------
# ENTRYPOINT
# --------------------------------------------
if __name__ == "__main__":
    logger.info("Starting MCP server...")
    mcp.run(transport="streamable-http")