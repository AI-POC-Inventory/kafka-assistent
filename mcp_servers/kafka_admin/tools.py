"""
Implementation of Kafka admin tools
"""
from typing import Dict, Any, Optional, List
from kafka.admin import KafkaAdminClient, NewTopic, ConfigResource, ConfigResourceType
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
import json
import logging

logger = logging.getLogger(__name__)


class KafkaAdminTools:
    def __init__(self, kafka_config: Dict[str, Any]):
        self.config = kafka_config
        self.admin_client = KafkaAdminClient(
            bootstrap_servers=kafka_config['bootstrap_servers'],
            security_protocol=kafka_config.get('security_protocol', 'PLAINTEXT'),
            sasl_mechanism=kafka_config.get('sasl_mechanism'),
            sasl_plain_username=kafka_config.get('sasl_username'),
            sasl_plain_password=kafka_config.get('sasl_password'),
        )
        self.producer = None
        self.consumer = None

    async def create_topic(
        self, 
        name: str, 
        partitions: int = 3, 
        replication_factor: int = 1,
        config: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Create a new Kafka topic"""
        topic = NewTopic(
            name=name,
            num_partitions=partitions,
            replication_factor=replication_factor,
            topic_configs=config or {}
        )
        
        try:
            result = self.admin_client.create_topics([topic])
            return {"created": True, "topic": name}
        except Exception as e:
            logger.error(f"Failed to create topic {name}: {e}")
            raise

    async def delete_topic(self, name: str) -> Dict[str, Any]:
        """Delete a Kafka topic"""
        try:
            result = self.admin_client.delete_topics([name])
            return {"deleted": True, "topic": name}
        except Exception as e:
            logger.error(f"Failed to delete topic {name}: {e}")
            raise

    async def list_topics(self) -> List[str]:
        """List all Kafka topics"""
        metadata = self.admin_client.list_topics()
        return list(metadata)

    async def update_topic_config(
        self, 
        topic: str, 
        config: Dict[str, str]
    ) -> Dict[str, Any]:
        """Update topic configuration"""
        resource = ConfigResource(ConfigResourceType.TOPIC, topic)
        configs = {resource: config}
        
        try:
            result = self.admin_client.alter_configs(configs)
            return {"updated": True, "topic": topic, "config": config}
        except Exception as e:
            logger.error(f"Failed to update config for topic {topic}: {e}")
            raise

    async def publish_message(
        self,
        topic: str,
        value: str,
        key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> int:
        """Publish a message to Kafka topic"""
        if not self.producer:
            self.producer = KafkaProducer(
                bootstrap_servers=self.config['bootstrap_servers'],
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None
            )
        
        try:
            future = self.producer.send(
                topic,
                value=value,
                key=key,
                headers=[(k, v.encode('utf-8')) for k, v in (headers or {}).items()]
            )
            record_metadata = future.get(timeout=10)
            return record_metadata.offset
        except KafkaError as e:
            logger.error(f"Failed to publish message: {e}")
            raise

    async def consume_messages(
        self,
        topic: str,
        group_id: str,
        max_messages: int = 10,
        timeout_ms: int = 5000
    ) -> List[Dict[str, Any]]:
        """Consume messages from Kafka topic"""
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=self.config['bootstrap_servers'],
            group_id=group_id,
            auto_offset_reset='latest',
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            consumer_timeout_ms=timeout_ms
        )
        
        messages = []
        try:
            for message in consumer:
                messages.append({
                    'topic': message.topic,
                    'partition': message.partition,
                    'offset': message.offset,
                    'key': message.key.decode('utf-8') if message.key else None,
                    'value': message.value,
                    'timestamp': message.timestamp
                })
                if len(messages) >= max_messages:
                    break
        finally:
            consumer.close()
        
        return messages

    async def create_user(
        self, 
        username: str, 
        password: str, 
        groups: List[str]
    ) -> Dict[str, Any]:
        """Create a new Kafka user (implementation depends on your Kafka setup)"""
        # This would integrate with your Kafka security setup
        # Could be SASL/SCRAM, LDAP, etc.
        # Placeholder implementation
        return {
            "created": True,
            "username": username,
            "groups": groups
        }

    async def create_acl(
        self,
        principal: str,
        resource_type: str,
        resource_name: str,
        operation: str,
        permission_type: str = "ALLOW"
    ) -> Dict[str, Any]:
        """Create Kafka ACL"""
        # Implementation would use kafka-python's ACL management
        # or integrate with your Kafka ACL system
        return {
            "created": True,
            "principal": principal,
            "resource": f"{resource_type}:{resource_name}",
            "operation": operation,
            "permission": permission_type
        }

    async def list_acls(self, resource_type: Optional[str] = None) -> List[Dict]:
        """List Kafka ACLs"""
        # Implementation would query Kafka ACLs
        return []
