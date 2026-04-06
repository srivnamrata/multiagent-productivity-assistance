"""
MCP Server Launcher

Launches the appropriate MCP server based on environment variables
Used by Docker to start the correct MCP service
"""

import asyncio
import os
import logging
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MCPServerType(str, Enum):
    """MCP server types"""
    TASK = "task"
    CALENDAR = "calendar"
    NOTES = "notes"
    CRITIC = "critic"
    AUDITOR = "auditor"
    EVENT_MONITOR = "event_monitor"
    RESEARCH = "research"
    NEWS = "news"


async def launch_mcp_server():
    """
    Launch the appropriate MCP server based on MCP_SERVER environment variable
    """
    
    # Get configuration from environment
    server_type = os.getenv("MCP_SERVER", "task").lower()
    port = int(os.getenv("PORT", os.getenv("MCP_PORT", "8080")))
    logger.info(f"Starting MCP Server: {server_type} on port {port}")
    
    try:
        if server_type == MCPServerType.TASK:
            from backend.mcp_tools.task_mcp_server import create_and_start_task_server
            server = await create_and_start_task_server(port)
            
        elif server_type == MCPServerType.CALENDAR:
            from backend.mcp_tools.calendar_mcp_server import create_and_start_calendar_server
            server = await create_and_start_calendar_server(port)
            
        elif server_type == MCPServerType.NOTES:
            from backend.mcp_tools.notes_mcp_server import create_and_start_notes_server
            server = await create_and_start_notes_server(port)
            
        elif server_type == MCPServerType.CRITIC:
            from backend.mcp_tools.critic_mcp_server import create_and_start_critic_server
            server = await create_and_start_critic_server(port)
            
        elif server_type == MCPServerType.AUDITOR:
            from backend.mcp_tools.auditor_mcp_server import create_and_start_auditor_server
            server = await create_and_start_auditor_server(port)
            
        elif server_type == MCPServerType.EVENT_MONITOR:
            from backend.mcp_tools.event_monitor_mcp_server import create_and_start_event_monitor_server
            server = await create_and_start_event_monitor_server(port)
            
        elif server_type == MCPServerType.RESEARCH:
            from backend.mcp_tools.research_mcp_server import create_and_start_research_server
            server = await create_and_start_research_server(port)
            
        elif server_type == MCPServerType.NEWS:
            from backend.mcp_tools.news_mcp_server import create_and_start_news_server
            server = await create_and_start_news_server(port)
            
        else:
            raise ValueError(f"Unknown MCP server type: {server_type}")
        
        logger.info(f"✅ {server_type.upper()} MCP Server started successfully")
        
        # Keep server running
        await asyncio.Event().wait()
        
    except Exception as e:
        logger.error(f"❌ Failed to start MCP server: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    logger.info("📦 MCP Server Launcher Started")
    asyncio.run(launch_mcp_server())
