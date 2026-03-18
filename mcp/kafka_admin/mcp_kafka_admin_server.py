import os
import logging
from confluent_kafka.admin import AdminClient, NewTopic
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
    port=int(os.environ.get("PORT", 8000))
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
def create_topics(
    topic_name: str,
    partitions: int = 1,
    replication_factor: int = 1
):
    """
    Create a Kafka topic.

    Args:
        topic_name (str): Name of the topic
        partitions (int): Number of partitions
        replication_factor (int): Replication factor

    Returns:
        dict: status or error
    """
    admin = None
    try:
        admin = get_admin()
        print(f"Creating topic '{topic_name}' with {partitions} partitions and replication factor {replication_factor}...")
        topic = NewTopic(
            topic=topic_name,
            num_partitions=partitions,
            replication_factor=replication_factor
        )

        futures = admin.create_topics([topic])

        results = {}

        for t_name, future in futures.items():
            try:
                future.result()  # wait for result
                results[t_name] = "created"
                logger.info(f"Topic created: {t_name}")
            except Exception as e:
                results[t_name] = str(e)
                logger.error(f"Error creating topic {t_name}: {e}")

        return {
            "status": "completed",
            "topics": results,
            "partitions": partitions,
            "replication_factor": replication_factor
        }

    except Exception as e:
        logger.exception("Kafka topic creation failed")
        return {"status": "failed", "error": str(e)}

    finally:
        if admin:
            admin = None  # no explicit close needed for confluent

# --------------------------------------------
# ENTRYPOINT
# --------------------------------------------
if __name__ == "__main__":
    mcp.run(transport="streamable-http")