"""
Schema Registry fetcher for periodic sync
"""
import asyncio
import json
from typing import Dict, List, Any
from datetime import datetime
import logging
from confluent_schema_registry import SchemaRegistryClient
from rag_pipeline.vector_store import VectorStore
from .tagger import PIITagger

logger = logging.getLogger(__name__)


class SchemaFetcher:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.sr_client = SchemaRegistryClient({
            'url': config['schema_registry_url'],
            'basic.auth.user.info': f"{config.get('username', '')}:{config.get('password', '')}"
        })
        self.vector_store = VectorStore(config['vector_store'])
        self.pii_tagger = PIITagger()
        
    async def fetch_all_schemas(self) -> List[Dict[str, Any]]:
        """Fetch all schemas from Schema Registry"""
        schemas = []
        
        try:
            # Get all subjects
            subjects = self.sr_client.list_subjects()
            
            for subject in subjects:
                # Get latest schema version
                schema_info = self.sr_client.get_latest_version(subject)
                schema = schema_info.schema
                
                # Parse schema based on type
                if schema.schema_type == 'AVRO':
                    parsed_schema = json.loads(schema.schema_str)
                elif schema.schema_type == 'PROTOBUF':
                    # Parse protobuf schema
                    parsed_schema = self._parse_protobuf(schema.schema_str)
                elif schema.schema_type == 'JSON':
                    parsed_schema = json.loads(schema.schema_str)
                else:
                    logger.warning(f"Unsupported schema type: {schema.schema_type}")
                    continue
                
                schemas.append({
                    'subject': subject,
                    'id': schema_info.schema_id,
                    'version': schema_info.version,
                    'type': schema.schema_type,
                    'schema': parsed_schema
                })
                
        except Exception as e:
            logger.error(f"Failed to fetch schemas: {e}")
            raise
            
        return schemas

    def _parse_protobuf(self, proto_str: str) -> Dict[str, Any]:
        """Parse protobuf schema string"""
        # Implement protobuf parsing logic
        # This is a placeholder - actual implementation would use protobuf parser
        return {}

    async def extract_fields(self, schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract fields from schema"""
        fields = []
        
        if schema['type'] == 'AVRO':
            avro_schema = schema['schema']
            if avro_schema.get('type') == 'record':
                for field in avro_schema.get('fields', []):
                    fields.append({
                        'name': field['name'],
                        'type': str(field['type']),
                        'description': field.get('doc', ''),
                        'default': field.get('default')
                    })
        
        # Add similar logic for other schema types
        
        return fields

    async def sync_schemas(self):
        """Main sync process"""
        logger.info("Starting schema sync process")
        
        try:
            # Fetch all schemas
            schemas = await self.fetch_all_schemas()
            logger.info(f"Fetched {len(schemas)} schemas")
            
            for schema in schemas:
                # Extract fields
                fields = await self.extract_fields(schema)
                
                # Tag PII fields
                tagged_fields = await self.pii_tagger.tag_fields(fields)
                
                # Generate metadata
                metadata = {
                    'schema_version': schema['version'],
                    'schema_type': schema['type'],
                    'last_synced': datetime.utcnow().isoformat(),
                    'subject': schema['subject']
                }
                
                # Upsert to vector store
                await self.vector_store.upsert_schema(
                    schema_id=str(schema['id']),
                    schema_name=schema['subject'],
                    fields=tagged_fields,
                    metadata=metadata
                )
                
                logger.info(f"Synced schema: {schema['subject']}")
            
            logger.info("Schema sync completed successfully")
            
        except Exception as e:
            logger.error(f"Schema sync failed: {e}")
            raise


class PIIDetector:
    """Detect PII fields based on patterns and rules"""
    
    PII_PATTERNS = {
        'email': ['email', 'email_address', 'emailaddress'],
        'phone': ['phone', 'phone_number', 'phonenumber', 'mobile'],
        'ssn': ['ssn', 'social_security', 'socialsecurity'],
        'credit_card': ['credit_card', 'creditcard', 'card_number'],
        'ip_address': ['ip_address', 'ipaddress', 'ip'],
        'name': ['first_name', 'last_name', 'full_name', 'firstname', 'lastname'],
        'address': ['address', 'street', 'city', 'state', 'zip', 'postal_code'],
        'dob': ['date_of_birth', 'dob', 'birth_date', 'birthdate']
    }
    
    def detect_pii(self, field_name: str, field_type: str) -> Dict[str, Any]:
        """Detect if a field contains PII"""
        field_lower = field_name.lower()
        
        for pii_type, patterns in self.PII_PATTERNS.items():
            for pattern in patterns:
                if pattern in field_lower:
                    return {
                        'is_pii': True,
                        'pii_type': pii_type,
                        'sensitivity_level': 'high'
                    }
        
        return {
            'is_pii': False,
            'pii_type': None,
            'sensitivity_level': 'public'
        }
