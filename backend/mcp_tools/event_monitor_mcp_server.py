"""
Event Monitor Agent MCP Server

Wraps the Event Monitor in an MCP server for distributed processing
Exposes event monitoring and Pub/Sub operations as MCP tools
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any

from .base_mcp_server import BaseMCPServer, MCPServerConfig
from .utils import log_operation

logger = logging.getLogger(__name__)


class EventMonitorMCPServer(BaseMCPServer):
    """
    MCP server for Event Monitor
    Provides distributed event monitoring and Pub/Sub capabilities
    """

    def __init__(self, config: Optional[MCPServerConfig] = None):
        """Initialize Event Monitor MCP server"""
        if config is None:
            config = MCPServerConfig(
                name="Event Monitor MCP Server",
                description="Event monitoring and Pub/Sub coordination",
                version="1.0.0",
                port=8006
            )
        
        super().__init__(config)
        self.event_subscriptions: Dict[str, List] = {}

    async def initialize(self) -> None:
        """Initialize event monitor and register tools"""
        logger.info("Initializing Event Monitor...")
        
        # Register tools that expose event operations
        await self._register_tools()
        
        logger.info("Event Monitor initialized successfully")

    async def _register_tools(self) -> None:
        """Register event monitoring tools"""
        
        # Subscribe to Topic
        self.register_tool(
            name="subscribe_to_topic",
            description="Subscribe to a Pub/Sub topic",
            handler=self._subscribe_to_topic,
            input_schema={
                "properties": {
                    "topic": {"type": "string", "description": "Topic name"},
                    "subscription": {"type": "string", "description": "Subscription name"},
                    "handler_url": {"type": "string", "description": "Handler endpoint URL"}
                }
            },
            required_fields=["topic", "subscription"]
        )
        
        # Publish Event
        self.register_tool(
            name="publish_event",
            description="Publish an event to a topic",
            handler=self._publish_event,
            input_schema={
                "properties": {
                    "topic": {"type": "string", "description": "Topic name"},
                    "event_type": {"type": "string", "description": "Type of event"},
                    "data": {"type": "object", "description": "Event data"},
                    "metadata": {"type": "object", "description": "Event metadata"}
                }
            },
            required_fields=["topic", "event_type", "data"]
        )
        
        # List Subscriptions
        self.register_tool(
            name="list_subscriptions",
            description="List all active subscriptions",
            handler=self._list_subscriptions,
            input_schema={
                "properties": {
                    "topic": {"type": "string", "description": "Filter by topic"}
                }
            },
            required_fields=[]
        )
        
        # Get Event
        self.register_tool(
            name="get_event",
            description="Get a specific event by ID",
            handler=self._get_event,
            input_schema={
                "properties": {
                    "event_id": {"type": "string", "description": "Event ID"}
                }
            },
            required_fields=["event_id"]
        )
        
        # Replay Events
        self.register_tool(
            name="replay_events",
            description="Replay events from a specific time",
            handler=self._replay_events,
            input_schema={
                "properties": {
                    "topic": {"type": "string", "description": "Topic name"},
                    "from_time": {"type": "string", "description": "Start time (ISO format)"},
                    "to_time": {"type": "string", "description": "End time (ISO format)"}
                }
            },
            required_fields=["topic", "from_time"]
        )
        
        # Monitor Health
        self.register_tool(
            name="monitor_health",
            description="Monitor system health and event flow",
            handler=self._monitor_health,
            input_schema={
                "properties": {
                    "component": {"type": "string", "description": "Component to monitor"},
                    "metrics": {"type": "array", "items": {"type": "string"}, "description": "Metrics to check"}
                }
            },
            required_fields=[]
        )
        
        # Acknowledge Event
        self.register_tool(
            name="acknowledge_event",
            description="Acknowledge event processing",
            handler=self._acknowledge_event,
            input_schema={
                "properties": {
                    "event_id": {"type": "string", "description": "Event ID"},
                    "status": {"type": "string", "enum": ["processed", "failed", "retry"]},
                    "message": {"type": "string", "description": "Status message"}
                }
            },
            required_fields=["event_id", "status"]
        )

    async def _subscribe_to_topic(self, topic: str, subscription: str,
                                 handler_url: str = None) -> Dict[str, Any]:
        """Subscribe to topic"""
        try:
            log_operation("subscribe_to_topic", self.config.name, "started",
                         {"topic": topic, "subscription": subscription})
            
            if topic not in self.event_subscriptions:
                self.event_subscriptions[topic] = []
            
            sub_info = {
                "topic": topic,
                "subscription": subscription,
                "handler_url": handler_url,
                "created_at": asyncio.get_event_loop().time()
            }
            self.event_subscriptions[topic].append(sub_info)
            
            log_operation("subscribe_to_topic", self.config.name, "completed",
                         {"topic": topic, "subscription": subscription})
            
            return {
                "status": "subscribed",
                "topic": topic,
                "subscription": subscription
            }
            
        except Exception as e:
            logger.error(f"Error subscribing to topic: {e}")
            self.log_error(e, {"operation": "subscribe_to_topic"})
            raise

    async def _publish_event(self, topic: str, event_type: str, data: Dict[str, Any],
                            metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Publish event"""
        try:
            log_operation("publish_event", self.config.name, "started",
                         {"topic": topic, "event_type": event_type})
            
            event = {
                "event_id": f"{topic}_{event_type}_{asyncio.get_event_loop().time()}",
                "topic": topic,
                "event_type": event_type,
                "data": data,
                "metadata": metadata or {},
                "status": "published"
            }
            
            log_operation("publish_event", self.config.name, "completed",
                         {"event_id": event["event_id"]})
            
            return event
            
        except Exception as e:
            logger.error(f"Error publishing event: {e}")
            self.log_error(e, {"operation": "publish_event"})
            raise

    async def _list_subscriptions(self, topic: str = None) -> Dict[str, Any]:
        """List subscriptions"""
        try:
            log_operation("list_subscriptions", self.config.name, "started", {})
            
            if topic:
                subs = self.event_subscriptions.get(topic, [])
            else:
                subs = []
                for topic_subs in self.event_subscriptions.values():
                    subs.extend(topic_subs)
            
            log_operation("list_subscriptions", self.config.name, "completed",
                         {"count": len(subs)})
            
            return {
                "subscriptions": subs,
                "count": len(subs)
            }
            
        except Exception as e:
            logger.error(f"Error listing subscriptions: {e}")
            self.log_error(e, {"operation": "list_subscriptions"})
            raise

    async def _get_event(self, event_id: str) -> Dict[str, Any]:
        """Get event"""
        try:
            log_operation("get_event", self.config.name, "started", {"event_id": event_id})
            
            # Mock implementation
            event = {
                "event_id": event_id,
                "status": "found",
                "timestamp": asyncio.get_event_loop().time()
            }
            
            log_operation("get_event", self.config.name, "completed", {})
            return event
            
        except Exception as e:
            logger.error(f"Error getting event: {e}")
            self.log_error(e, {"operation": "get_event"})
            raise

    async def _replay_events(self, topic: str, from_time: str,
                            to_time: str = None) -> Dict[str, Any]:
        """Replay events"""
        try:
            log_operation("replay_events", self.config.name, "started",
                         {"topic": topic, "from_time": from_time})
            
            # Mock implementation
            replayed_events = {
                "topic": topic,
                "from_time": from_time,
                "to_time": to_time,
                "count": 0,
                "status": "replaying"
            }
            
            log_operation("replay_events", self.config.name, "completed", {})
            return replayed_events
            
        except Exception as e:
            logger.error(f"Error replaying events: {e}")
            self.log_error(e, {"operation": "replay_events"})
            raise

    async def _monitor_health(self, component: str = None,
                             metrics: List[str] = None) -> Dict[str, Any]:
        """Monitor health"""
        try:
            log_operation("monitor_health", self.config.name, "started",
                         {"component": component or "all"})
            
            health_status = {
                "component": component or "all",
                "status": "healthy",
                "metrics": metrics or ["latency", "throughput", "error_rate"],
                "timestamp": asyncio.get_event_loop().time()
            }
            
            log_operation("monitor_health", self.config.name, "completed", {})
            return health_status
            
        except Exception as e:
            logger.error(f"Error monitoring health: {e}")
            self.log_error(e, {"operation": "monitor_health"})
            raise

    async def _acknowledge_event(self, event_id: str, status: str,
                                message: str = None) -> Dict[str, Any]:
        """Acknowledge event"""
        try:
            log_operation("acknowledge_event", self.config.name, "started",
                         {"event_id": event_id, "status": status})
            
            acknowledgment = {
                "event_id": event_id,
                "status": status,
                "message": message or "",
                "acknowledged_at": asyncio.get_event_loop().time()
            }
            
            log_operation("acknowledge_event", self.config.name, "completed", {})
            return acknowledgment
            
        except Exception as e:
            logger.error(f"Error acknowledging event: {e}")
            self.log_error(e, {"operation": "acknowledge_event"})
            raise


async def create_and_start_event_monitor_server(port: int = 8006) -> EventMonitorMCPServer:
    """
    Factory function to create and start Event Monitor MCP server
    
    Args:
        port: Port to run server on
        
    Returns:
        Started EventMonitorMCPServer instance
    """
    config = MCPServerConfig(
        name="Event Monitor MCP Server",
        description="Event monitoring via MCP",
        version="1.0.0",
        port=port
    )
    
    server = EventMonitorMCPServer(config)
    await server.initialize()
    await server.start(port)
    
    return server


if __name__ == "__main__":
    # For local testing
    import asyncio
    
    async def main():
        server = await create_and_start_event_monitor_server()
        print(f"Event Monitor MCP Server running on port {server.config.port}")
        print(f"Available tools: {len(server.list_tools())}")
        for tool in server.list_tools():
            print(f"  - {tool['name']}: {tool['description']}")
    
    asyncio.run(main())
