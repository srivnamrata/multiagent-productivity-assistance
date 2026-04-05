"""
Calendar Agent MCP Server

Wraps the CalendarAgent in an MCP server for distributed processing
Exposes calendar management operations as MCP tools
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any

from base_mcp_server import BaseMCPServer, MCPServerConfig
from utils import log_operation

# Import the existing CalendarAgent
import sys
sys.path.insert(0, '../agents')
from calendar_agent import CalendarAgent

logger = logging.getLogger(__name__)


class CalendarMCPServer(BaseMCPServer):
    """
    MCP server for Calendar Agent
    Provides distributed calendar and meeting management
    """

    def __init__(self, config: Optional[MCPServerConfig] = None):
        """Initialize Calendar MCP server"""
        if config is None:
            config = MCPServerConfig(
                name="Calendar MCP Server",
                description="Manages calendar events and meetings",
                version="1.0.0",
                port=8002
            )
        
        super().__init__(config)
        self.agent: Optional[CalendarAgent] = None

    async def initialize(self) -> None:
        """Initialize calendar agent and register tools"""
        logger.info("Initializing Calendar Agent...")
        
        # Initialize the agent
        self.agent = CalendarAgent()
        
        # Register tools that expose agent methods
        await self._register_tools()
        
        logger.info("Calendar Agent initialized successfully")

    async def _register_tools(self) -> None:
        """Register calendar management tools"""
        
        # Create Event
        self.register_tool(
            name="create_event",
            description="Create a calendar event",
            handler=self._create_event,
            input_schema={
                "properties": {
                    "title": {"type": "string", "description": "Event title"},
                    "description": {"type": "string", "description": "Event description"},
                    "start_time": {"type": "string", "description": "Start time (ISO format)"},
                    "end_time": {"type": "string", "description": "End time (ISO format)"},
                    "location": {"type": "string", "description": "Event location"},
                    "attendees": {"type": "array", "items": {"type": "string"}, "description": "List of attendee emails"}
                }
            },
            required_fields=["title", "start_time", "end_time"]
        )
        
        # Update Event
        self.register_tool(
            name="update_event",
            description="Update a calendar event",
            handler=self._update_event,
            input_schema={
                "properties": {
                    "event_id": {"type": "string", "description": "Event ID"},
                    "title": {"type": "string", "description": "New title"},
                    "description": {"type": "string", "description": "New description"},
                    "start_time": {"type": "string", "description": "New start time (ISO format)"},
                    "end_time": {"type": "string", "description": "New end time (ISO format)"},
                    "location": {"type": "string", "description": "New location"},
                    "attendees": {"type": "array", "items": {"type": "string"}, "description": "Updated attendee list"}
                }
            },
            required_fields=["event_id"]
        )
        
        # Delete Event
        self.register_tool(
            name="delete_event",
            description="Delete a calendar event",
            handler=self._delete_event,
            input_schema={
                "properties": {
                    "event_id": {"type": "string", "description": "Event ID"}
                }
            },
            required_fields=["event_id"]
        )
        
        # List Events
        self.register_tool(
            name="list_events",
            description="List calendar events for a date range",
            handler=self._list_events,
            input_schema={
                "properties": {
                    "start_date": {"type": "string", "description": "Start date (ISO format)"},
                    "end_date": {"type": "string", "description": "End date (ISO format)"},
                    "limit": {"type": "integer", "description": "Maximum number of events"}
                }
            },
            required_fields=["start_date", "end_date"]
        )
        
        # Find Available Slots
        self.register_tool(
            name="find_available_slots",
            description="Find available time slots for meeting",
            handler=self._find_available_slots,
            input_schema={
                "properties": {
                    "start_date": {"type": "string", "description": "Start date (ISO format)"},
                    "end_date": {"type": "string", "description": "End date (ISO format)"},
                    "duration_minutes": {"type": "integer", "description": "Duration in minutes"},
                    "attendees": {"type": "array", "items": {"type": "string"}, "description": "Attendee emails"}
                }
            },
            required_fields=["start_date", "end_date", "duration_minutes"]
        )
        
        # Add Attendee
        self.register_tool(
            name="add_attendee",
            description="Add attendee to event",
            handler=self._add_attendee,
            input_schema={
                "properties": {
                    "event_id": {"type": "string", "description": "Event ID"},
                    "attendee_email": {"type": "string", "description": "Attendee email"}
                }
            },
            required_fields=["event_id", "attendee_email"]
        )
        
        # Remove Attendee
        self.register_tool(
            name="remove_attendee",
            description="Remove attendee from event",
            handler=self._remove_attendee,
            input_schema={
                "properties": {
                    "event_id": {"type": "string", "description": "Event ID"},
                    "attendee_email": {"type": "string", "description": "Attendee email"}
                }
            },
            required_fields=["event_id", "attendee_email"]
        )

    async def _create_event(self, title: str, start_time: str, end_time: str,
                           description: str = None, location: str = None,
                           attendees: List[str] = None) -> Dict[str, Any]:
        """Create a calendar event"""
        try:
            log_operation("create_event", self.config.name, "started", {"title": title, "start": start_time})
            
            event = await self.agent.create_event(
                title=title,
                description=description or "",
                start_time=start_time,
                end_time=end_time,
                location=location or "",
                attendees=attendees or []
            )
            
            log_operation("create_event", self.config.name, "completed", {"event_id": event.get("id")})
            return event
            
        except Exception as e:
            logger.error(f"Error creating event: {e}")
            self.log_error(e, {"operation": "create_event"})
            raise

    async def _update_event(self, event_id: str, title: str = None, description: str = None,
                           start_time: str = None, end_time: str = None,
                           location: str = None, attendees: List[str] = None) -> Dict[str, Any]:
        """Update a calendar event"""
        try:
            log_operation("update_event", self.config.name, "started", {"event_id": event_id})
            
            event = await self.agent.update_event(
                event_id=event_id,
                title=title,
                description=description,
                start_time=start_time,
                end_time=end_time,
                location=location,
                attendees=attendees
            )
            
            log_operation("update_event", self.config.name, "completed", {"event_id": event_id})
            return event
            
        except Exception as e:
            logger.error(f"Error updating event: {e}")
            self.log_error(e, {"operation": "update_event", "event_id": event_id})
            raise

    async def _delete_event(self, event_id: str) -> Dict[str, Any]:
        """Delete a calendar event"""
        try:
            log_operation("delete_event", self.config.name, "started", {"event_id": event_id})
            
            result = await self.agent.delete_event(event_id=event_id)
            
            log_operation("delete_event", self.config.name, "completed", {"event_id": event_id})
            return result
            
        except Exception as e:
            logger.error(f"Error deleting event: {e}")
            self.log_error(e, {"operation": "delete_event", "event_id": event_id})
            raise

    async def _list_events(self, start_date: str, end_date: str, limit: int = 20) -> Dict[str, Any]:
        """List calendar events"""
        try:
            log_operation("list_events", self.config.name, "started", {"start": start_date, "end": end_date})
            
            events = await self.agent.list_events(
                start_date=start_date,
                end_date=end_date,
                limit=limit
            )
            
            log_operation("list_events", self.config.name, "completed", {"count": len(events)})
            return {"events": events, "count": len(events)}
            
        except Exception as e:
            logger.error(f"Error listing events: {e}")
            self.log_error(e, {"operation": "list_events"})
            raise

    async def _find_available_slots(self, start_date: str, end_date: str,
                                   duration_minutes: int, attendees: List[str] = None) -> Dict[str, Any]:
        """Find available time slots"""
        try:
            log_operation("find_available_slots", self.config.name, "started",
                         {"start": start_date, "duration": duration_minutes})
            
            slots = await self.agent.find_available_slots(
                start_date=start_date,
                end_date=end_date,
                duration_minutes=duration_minutes,
                attendees=attendees or []
            )
            
            log_operation("find_available_slots", self.config.name, "completed", {"count": len(slots)})
            return {"available_slots": slots, "count": len(slots)}
            
        except Exception as e:
            logger.error(f"Error finding slots: {e}")
            self.log_error(e, {"operation": "find_available_slots"})
            raise

    async def _add_attendee(self, event_id: str, attendee_email: str) -> Dict[str, Any]:
        """Add attendee to event"""
        try:
            log_operation("add_attendee", self.config.name, "started",
                         {"event_id": event_id, "attendee": attendee_email})
            
            event = await self.agent.add_attendee(event_id=event_id, attendee_email=attendee_email)
            
            log_operation("add_attendee", self.config.name, "completed", {"event_id": event_id})
            return event
            
        except Exception as e:
            logger.error(f"Error adding attendee: {e}")
            self.log_error(e, {"operation": "add_attendee", "event_id": event_id})
            raise

    async def _remove_attendee(self, event_id: str, attendee_email: str) -> Dict[str, Any]:
        """Remove attendee from event"""
        try:
            log_operation("remove_attendee", self.config.name, "started",
                         {"event_id": event_id, "attendee": attendee_email})
            
            event = await self.agent.remove_attendee(event_id=event_id, attendee_email=attendee_email)
            
            log_operation("remove_attendee", self.config.name, "completed", {"event_id": event_id})
            return event
            
        except Exception as e:
            logger.error(f"Error removing attendee: {e}")
            self.log_error(e, {"operation": "remove_attendee", "event_id": event_id})
            raise


async def create_and_start_calendar_server(port: int = 8002) -> CalendarMCPServer:
    """
    Factory function to create and start Calendar MCP server
    
    Args:
        port: Port to run server on
        
    Returns:
        Started CalendarMCPServer instance
    """
    config = MCPServerConfig(
        name="Calendar MCP Server",
        description="Calendar management via MCP",
        version="1.0.0",
        port=port
    )
    
    server = CalendarMCPServer(config)
    await server.initialize()
    await server.start(port)
    
    return server


if __name__ == "__main__":
    # For local testing
    import asyncio
    
    async def main():
        server = await create_and_start_calendar_server()
        print(f"Calendar MCP Server running on port {server.config.port}")
        print(f"Available tools: {len(server.list_tools())}")
        for tool in server.list_tools():
            print(f"  - {tool['name']}: {tool['description']}")
    
    asyncio.run(main())
