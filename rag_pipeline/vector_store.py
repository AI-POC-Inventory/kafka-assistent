"""
Vector store management for schema embeddings and semantic search
"""
import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client = chromadb.Client(
            ChromaSettings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=config.get('persist_directory', './chroma_db')
            )
        )
        
        # Initialize or get collection for schema embeddings
        self.collection = self.client.get_or_create_collection(
            name="kafka_schemas",
            metadata={"description": "Kafka schema embeddings with PII tags"}
        )
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer(
            config.get('embedding_model', 'all-MiniLM-L6-v2')
        )

    def embed_text(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for text"""
        embeddings = self.embedding_model.encode(texts)
        return embeddings.tolist()

    async def upsert_schema(
        self,
        schema_id: str,
        schema_name: str,
        fields: List[Dict[str, Any]],
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Upsert schema with field embeddings and metadata
        
        Args:
            schema_id: Unique identifier for the schema
            schema_name: Name of the schema
            fields: List of field definitions with names, types, and descriptions
            metadata: Additional metadata including PII tags, sensitivity levels
        """
        try:
            documents = []
            embeddings = []
            metadatas = []
            ids = []
            
            for field in fields:
                # Create searchable document from field
                field_doc = f"Schema: {schema_name}\n"
                field_doc += f"Field: {field['name']}\n"
                field_doc += f"Type: {field['type']}\n"
                field_doc += f"Description: {field.get('description', '')}"
                
                documents.append(field_doc)
                
                # Create metadata for the field
                field_metadata = {
                    'schema_id': schema_id,
                    'schema_name': schema_name,
                    'field_name': field['name'],
                    'field_type': field['type'],
                    'is_pii': field.get('is_pii', False),
                    'sensitivity_level': field.get('sensitivity_level', 'public'),
                    'tags': ','.join(field.get('tags', [])),
                    **metadata
                }
                metadatas.append(field_metadata)
                
                # Create unique ID for the field
                field_id = f"{schema_id}_{field['name']}"
                ids.append(field_id)
            
            # Generate embeddings
            embeddings = self.embed_text(documents)
            
            # Upsert to ChromaDB
            self.collection.upsert(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Successfully upserted schema {schema_name} with {len(fields)} fields")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upsert schema {schema_name}: {e}")
            raise

    async def search_schemas(
        self,
        query: str,
        filter_tags: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Semantic search for schemas based on query
        
        Args:
            query: Search query
            filter_tags: Optional tags to filter results (e.g., ['pii', 'sensitive'])
            limit: Maximum number of results
        """
        # Generate embedding for query
        query_embedding = self.embed_text([query])[0]
        
        # Build where clause for filtering
        where_clause = {}
        if filter_tags:
            where_clause = {
                "$or": [{"tags": {"$contains": tag}} for tag in filter_tags]
            }
        
        # Perform search
        results = self.collection.query(
            query_embeddings=[query_embedding],
            where=where_clause if where_clause else None,
            n_results=limit,
            include=['documents', 'metadatas', 'distances']
        )
        
        # Format results
        formatted_results = []
        for i in range(len(results['ids'][0])):
            formatted_results.append({
                'id': results['ids'][0][i],
                'document': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'similarity_score': 1 - results['distances'][0][i]  # Convert distance to similarity
            })
        
        return formatted_results

    async def get_pii_fields(self, schema_name: str) -> List[Dict[str, Any]]:
        """Get all PII fields for a given schema"""
        results = self.collection.get(
            where={
                "$and": [
                    {"schema_name": {"$eq": schema_name}},
                    {"is_pii": {"$eq": True}}
                ]
            },
            include=['metadatas']
        )
        
        return results['metadatas'] if results['metadatas'] else []

    async def get_field_sensitivity(
        self, 
        schema_name: str, 
        field_name: str
    ) -> Dict[str, Any]:
        """Get sensitivity information for a specific field"""
        field_id = f"{schema_name}_{field_name}"
        
        try:
            result = self.collection.get(
                ids=[field_id],
                include=['metadatas']
            )
            
            if result['metadatas']:
                metadata = result['metadatas'][0]
                return {
                    'is_pii': metadata.get('is_pii', False),
                    'sensitivity_level': metadata.get('sensitivity_level', 'public'),
                    'tags': metadata.get('tags', '').split(',') if metadata.get('tags') else []
                }
        except Exception as e:
            logger.error(f"Failed to get sensitivity for {schema_name}.{field_name}: {e}")
        
        return {
            'is_pii': False,
            'sensitivity_level': 'public',
            'tags': []
        }
