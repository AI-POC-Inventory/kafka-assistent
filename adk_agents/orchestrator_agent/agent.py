"""
Orchestrator ADK Agent - Routes requests to sub-agents via A2A protocol
"""
import asyncio
from typing import Dict, Any, List, Optional
import logging
from dataclasses import dataclass
from enum import Enum

from .a2a_protocol import A2AProtocol
from security.rbac import RBACEnforcer

logger = logging.getLogger(__name__)


class AgentCapability(Enum):
    KAFKA_ADMIN = "kafka_admin"
    SCHEMA_SEARCH = "schema_search"
    METRICS = "metrics"
    STREAMING = "streaming"


@dataclass
class AgentRoute:
    agent_id: str
    capabilities: List[AgentCapability]
    endpoint: str
    priority: int = 0


class OrchestratorAgent:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.a2a_protocol = A2AProtocol()
        self.rbac = RBACEnforcer(config['ranger'])
        
        # Register sub-agents
        self.agents = {
            'kafka_admin_agent': AgentRoute(
                agent_id='kafka_admin_agent',
                capabilities=[
                    AgentCapability.KAFKA_ADMIN,
                    AgentCapability.STREAMING
                ],
                endpoint=config['agents']['kafka_admin']['endpoint'],
                priority=1
            ),
            'schema_metrics_agent': AgentRoute(
                agent_id='schema_metrics_agent',
                capabilities=[
                    AgentCapability.SCHEMA_SEARCH,
                    AgentCapability.METRICS
                ],
                endpoint=config['agents']['schema_metrics']['endpoint'],
                priority=1
            )
        }
        
        self.request_cache = {}

    async def route_request(
        self,
        request: Dict[str, Any],
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Route request to appropriate sub-agent based on capability
        """
        request_type = request.get('type')
        request_id = request.get('id')
        
        # Check RBAC permissions at orchestrator level
        if not await self._check_permissions(request, user_context):
            return {
                'status': 'error',
                'error': 'Permission denied',
                'request_id': request_id
            }
        
        # Determine target agent based on request type
        target_agent = await self._select_agent(request_type)
        
        if not target_agent:
            return {
                'status': 'error',
                'error': f'No agent available for request type: {request_type}',
                'request_id': request_id
            }
        
        # Add user context to request
        enriched_request = {
            **request,
            'user_context': user_context,
            'source_agent': 'orchestrator'
        }
        
        # Send request via A2A protocol
        try:
            response = await self.a2a_protocol.send_request(
                target_agent.endpoint,
                enriched_request
            )
            
            # Apply data masking if needed
            if response.get('data'):
                response['data'] = await self._apply_data_masking(
                    response['data'],
                    user_context
                )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to route request to {target_agent.agent_id}: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'request_id': request_id
            }

    async def _check_permissions(
        self,
        request: Dict[str, Any],
        user_context: Dict[str, Any]
    ) -> bool:
        """Check RBAC permissions for the request"""
        resource_type = request.get('resource_type')
        action = request.get('action')
        resource_name = request.get('resource_name', '*')
        
        return await self.rbac.check_permission(
            user_context,
            resource_type,
            action,
            resource_name
        )

    async def _select_agent(self, request_type: str) -> Optional[AgentRoute]:
        """Select the best agent for handling the request"""
        capability_map = {
            'create_topic': AgentCapability.KAFKA_ADMIN,
            'create_user': AgentCapability.KAFKA_ADMIN,
            'create_acl': AgentCapability.KAFKA_ADMIN,
            'publish_message': AgentCapability.KAFKA_ADMIN,
            'consume_message': AgentCapability.KAFKA_ADMIN,
            'search_schema': AgentCapability.SCHEMA_SEARCH,
            'get_metrics': AgentCapability.METRICS,
            'streaming_query': AgentCapability.STREAMING
        }
        
        required_capability = capability_map.get(request_type)
        
        if not required_capability:
            return None
        
        # Find agents with required capability
        capable_agents = [
            agent for agent in self.agents.values()
            if required_capability in agent.capabilities
        ]
        
        # Select agent with highest priority
        if capable_agents:
            return max(capable_agents, key=lambda a: a.priority)
        
        return None

    async def _apply_data_masking(
        self,
        data: Any,
        user_context: Dict[str, Any]
    ) -> Any:
        """Apply data masking based on user permissions and PII tags"""
        # Check if user has permission to view PII
        can_view_pii = await self.rbac.check_permission(
            user_context,
            'data',
            'view_pii',
            '*'
        )
        
        if can_view_pii:
            return data
        
        # Apply masking to PII fields
        if isinstance(data, dict):
            return await self._mask_dict(data)
        elif isinstance(data, list):
            return [await self._apply_data_masking(item, user_context) for item in data]
        
        return data

    async def _mask_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mask PII fields in dictionary"""
        masked_data = {}
        
        for key, value in data.items():
            # Check if field is PII (would query vector store in real implementation)
            if await self._is_pii_field(key):
                masked_data[key] = "***MASKED***"
            elif isinstance(value, dict):
                masked_data[key] = await self._mask_dict(value)
            elif isinstance(value, list):
                masked_data[key] = [await self._apply_data_masking(item, {}) for item in value]
            else:
                masked_data[key] = value
        
        return masked_data

    async def _is_pii_field(self, field_name: str) -> bool:
        """Check if field is PII (simplified implementation)"""
        pii_keywords = ['email', 'ssn', 'phone', 'address', 'name', 'dob']
        field_lower = field_name.lower()
        return any(keyword in field_lower for keyword in pii_keywords)

    async def aggregate_responses(
        self,
        responses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Aggregate responses from multiple agents"""
        if not responses:
            return {'status': 'error', 'error': 'No responses received'}
        
        # If single response, return as-is
        if len(responses) == 1:
            return responses[0]
        
        # Aggregate multiple responses
        aggregated = {
            'status': 'success',
            'data': {
                'responses': responses,
                'summary': {
                    'total_responses': len(responses),
                    'successful': sum(1 for r in responses if r.get('status') == 'success'),
                    'failed': sum(1 for r in responses if r.get('status') == 'error')
                }
            }
        }
        
        return aggregated
