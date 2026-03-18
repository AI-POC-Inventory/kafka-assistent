from pydantic import BaseSettings

class Settings(BaseSettings):
    KAFKA_BOOTSTRAP_SERVERS: str
    PROMETHEUS_URL: str

    ADK_API_KEY: str

    ADMIN_MCP_URL: str
    METRICS_MCP_URL: str

    ADMIN_AGENT_URL: str
    METRICS_AGENT_URL: str

    class Config:
        env_file = ".env"

settings = Settings()
