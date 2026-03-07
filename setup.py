from setuptools import setup, find_packages

setup(
    name="kafka-assistant",
    version="0.1.0",
    description="AI-Powered Kafka Assistant with MCP and ADK integration",
    author="Your Team",
    packages=find_packages(),
    install_requires=[
        # List from requirements.txt
    ],
    entry_points={
        "console_scripts": [
            "kafka-assistant=main:main",
            "schema-sync=schema_sync.scheduler:main",
        ],
    },
    python_requires=">=3.9",
)
