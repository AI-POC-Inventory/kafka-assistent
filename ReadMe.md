AI-Powered Kafka Assistant

An AI-driven assistant for Apache Kafka operations that allows users to interact with Kafka clusters using natural language via chat.

The system integrates:

LibreChat for conversational UI

Google ADK Agents for intelligent orchestration

MCP Servers to expose operational tools

RAG (Retrieval Augmented Generation) for schema intelligence

Prometheus for metrics monitoring

Apache Ranger for RBAC and governance

Architecture Overview
System Components
1. Chat Interface Layer
LibreChat

The user interacts with the system through a conversational interface.

Example user queries:

Create topic payments with 6 partitions
Show Kafka broker CPU usage
List schemas for topic orders
Join topic A with topic B

LibreChat sends the request to the Orchestrator MCP Server.

2. Orchestrator Layer
Orchestrator ADK Agent

The orchestrator is responsible for:

Routing requests to the correct agent

Aggregating responses

Applying security policies

Managing inter-agent communication

Key responsibilities:

Request routing

RBAC enforcement

Response aggregation

Data masking enforcement

The orchestrator is exposed via:

MCP Server #5

which allows LibreChat to communicate using MCP protocol.

3. ADK Agent Layer

Two specialized AI agents perform system operations.

Kafka Admin Agent (Agent #1)

Responsible for Kafka operational tasks.

Connected MCP servers:

MCP Server #1 — Kafka Admin Tools

MCP Server #4 — Streaming Queries

Capabilities:

Create topics

Manage ACLs

Manage users

Publish messages

Consume messages

Delete topics

Manage streaming queries

Schema & Metrics Agent (Agent #2)

Responsible for observability and schema intelligence.

Connected services:

MCP Server #3 — Metrics

RAG Pipeline

Capabilities:

Schema semantic search

Kafka cluster health monitoring

Broker metrics analysis

Topic metrics monitoring

PII detection through schema tags

4. MCP Server Layer

MCP servers expose operational tools to AI agents.

MCP Server #1 — Kafka Admin

Provides administration APIs.

Available tools:

Create User

Create Topic

Create ACL

Update Topic Configuration

Publish Messages

Consume Messages

Delete Topic

View ACLs

View Users

MCP Server #3 — Kafka Metrics

Provides observability via Prometheus.

Capabilities:

Query JMX metrics

Cluster health checks

Broker performance metrics

Topic throughput metrics

MCP Server #4 — Streaming Queries

Provides stream processing operations.

Capabilities:

Topic joins

Stream-stream joins

Stream-table joins

Streaming query management

RAG Pipeline

Provides schema intelligence using embeddings.

Capabilities:

Semantic schema search

Field metadata lookup

PII tag detection

Schema metadata retrieval

Uses a vector database such as:

ChromaDB

Pinecone

Weaviate

5. Infrastructure Layer
Kafka Cluster

Core streaming platform containing:

Brokers

Topics

Consumer Groups

Connected components:

Schema Registry

Kafka Streams

Kafka Admin APIs

Schema Registry

Stores schemas used by Kafka topics.

Supported formats:

Avro

Protobuf

JSON Schema

Prometheus

Collects Kafka metrics including:

Broker metrics

Topic throughput

Consumer lag

JMX metrics

Vector Database

Stores schema embeddings and metadata.

Contains:

Schema embeddings

Field metadata

PII sensitivity tags

Example databases:

ChromaDB

Pinecone

Apache Ranger

Provides security and governance.

Capabilities:

RBAC policy management

Resource level access control

User and group permissions

Agents query Ranger before executing actions.

Schema Sync Pipeline

A scheduled Python job periodically syncs schemas to the vector database.

Workflow
Schema Registry
      ↓
Python Schema Fetcher (Cron Job)
      ↓
Extract Field Metadata
      ↓
Add PII / Sensitivity Tags
      ↓
Generate Embeddings
      ↓
Upsert into Vector Database
Request Flow
User
  ↓
LibreChat
  ↓
MCP Server #5 (Orchestrator)
  ↓
Orchestrator ADK Agent
  ↓
A2A Communication
  ↓
Agent #1 → Kafka Admin MCP → Kafka Cluster
Agent #2 → Metrics MCP → Prometheus
Agent #2 → RAG Pipeline → Vector Database
Security Flow
Agent Request
     ↓
Apache Ranger
     ↓
RBAC Policy Check
     ↓
Allow / Deny

For schema responses:

Schema Fields
     ↓
Vector Store Tag Lookup
     ↓
Mask Sensitive Fields
Technology Stack
Layer	Technology
UI	LibreChat
Agents	Google ADK
Protocol	MCP
Messaging	Apache Kafka
Monitoring	Prometheus
Schema	Schema Registry
Vector DB	ChromaDB / Pinecone
Security	Apache Ranger
