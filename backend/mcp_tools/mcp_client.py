"""
MCP Client

Client library for calling MCP servers
Used by Orchestrator to communicate with agent MCP servers
"""

import asyncio
import logging
import httpx
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class MCPServerType(str, Enum):
    """Types of MCP servers"""
    TASK = "task"
    CALENDAR = "calendar"
    NOTES = "notes"
    CRITIC = "critic"
    AUDITOR = "auditor"
    EVENT_MONITOR = "event_monitor"
    RESEARCH = "research"
    NEWS = "news"


class MCPClientConfig:
    """Configuration for MCP client"""
    
    # Server configurations
    SERVERS = {
        MCPServerType.TASK: {"host": "localhost", "port": 8001},
        MCPServerType.CALENDAR: {"host": "localhost", "port": 8002},
        MCPServerType.NOTES: {"host": "localhost", "port": 8003},
        MCPServerType.CRITIC: {"host": "localhost", "port": 8004},
        MCPServerType.AUDITOR: {"host": "localhost", "port": 8005},
        MCPServerType.EVENT_MONITOR: {"host": "localhost", "port": 8006},
        MCPServerType.RESEARCH: {"host": "localhost", "port": 8007},
        MCPServerType.NEWS: {"host": "localhost", "port": 8008},
    }
    
    # Timeout settings
    DEFAULT_TIMEOUT = 30.0  # seconds
    CONNECT_TIMEOUT = 5.0   # seconds
    
    @classmethod
    def set_server_host(cls, server_type: MCPServerType, host: str, port: int) -> None:
        """
        Override server configuration
        
        Args:
            server_type: Type of server
            host: Hostname/IP address
            port: Port number
        """
        cls.SERVERS[server_type] = {"host": host, "port": port}


class MCPClient:
    """
    Client for calling MCP servers
    Provides a simple interface for calling tools on remote MCP servers
    """
    
    def __init__(self, server_type: MCPServerType, timeout: float = None):
        """
        Initialize MCP client
        
        Args:
            server_type: Type of server to connect to
            timeout: Request timeout in seconds
        """
        self.server_type = server_type
        self.timeout = timeout or MCPClientConfig.DEFAULT_TIMEOUT
        
        # Get server config
        server_config = MCPClientConfig.SERVERS.get(server_type)
        if not server_config:
            raise ValueError(f"Unknown server type: {server_type}")
        
        self.host = server_config["host"]
        self.port = server_config["port"]
        self.base_url = f"http://{self.host}:{self.port}"
        self._client = None
        
        logger.info(f"Initialized MCP client for {server_type} server at {self.base_url}")
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if not self._client:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout, connect=MCPClientConfig.CONNECT_TIMEOUT)
            )
        return self._client
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool on the MCP server
        
        Args:
            tool_name: Name of the tool to call
            arguments: Arguments for the tool
            
        Returns:
            Tool result
        """
        client = await self._get_client()
        
        try:
            logger.debug(f"Calling {tool_name} on {self.server_type} server")
            
            response = await client.post(
                f"{self.base_url}/tools/call",
                json={
                    "tool_name": tool_name,
                    "arguments": arguments
                }
            )
            
            response.raise_for_status()
            result = response.json()
            
            logger.debug(f"Tool {tool_name} completed successfully")
            return result
            
        except httpx.TimeoutException:
            error_msg = f"Timeout calling {tool_name} on {self.server_type}"
            logger.error(error_msg)
            raise TimeoutError(error_msg)
        except httpx.ConnectError:
            error_msg = f"Connection failed to {self.server_type} server at {self.base_url}"
            logger.error(error_msg)
            raise ConnectionError(error_msg)
        except httpx.HTTPStatusError as e:
            error_msg = f"Error calling {tool_name}: {e.response.text}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error calling {tool_name}: {str(e)}"
            logger.error(error_msg)
            raise
    
    async def get_tools(self) -> List[Dict[str, Any]]:
        """
        Get list of available tools on the server
        
        Returns:
            List of tool definitions
        """
        client = await self._get_client()
        
        try:
            response = await client.get(f"{self.base_url}/tools/list")
            response.raise_for_status()
            return response.json().get("tools", [])
        except Exception as e:
            logger.error(f"Error getting tools list: {e}")
            return []
    
    async def get_health(self) -> Dict[str, Any]:
        """
        Get server health status
        
        Returns:
            Health status
        """
        client = await self._get_client()
        
        try:
            response = await client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"Health check failed for {self.server_type}: {e}")
            return {"status": "unhealthy", "error": str(e)}
    
    async def close(self) -> None:
        """Close the client connection"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()


class MCPClientPool:
    """
    Pool of MCP clients for managing multiple connections
    Provides connection pooling and load balancing
    """
    
    def __init__(self):
        """Initialize MCP client pool"""
        self._clients: Dict[MCPServerType, MCPClient] = {}
        self._lock = asyncio.Lock()
        logger.info("Initialized MCP client pool")
    
    async def get_client(self, server_type: MCPServerType) -> MCPClient:
        """
        Get a client for a specific server type
        
        Args:
            server_type: Type of server
            
        Returns:
            MCPClient instance
        """
        async with self._lock:
            if server_type not in self._clients:
                self._clients[server_type] = MCPClient(server_type)
            return self._clients[server_type]
    
    async def call_tool(self, server_type: MCPServerType, tool_name: str,
                       arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool via the pool
        
        Args:
            server_type: Type of server
            tool_name: Name of the tool
            arguments: Tool arguments
            
        Returns:
            Tool result
        """
        client = await self.get_client(server_type)
        return await client.call_tool(tool_name, arguments)
    
    async def get_health(self) -> Dict[MCPServerType, Dict[str, Any]]:
        """
        Get health status of all servers
        
        Returns:
            Health status for each server type
        """
        health_status = {}
        
        for server_type in MCPServerType:
            try:
                client = await self.get_client(server_type)
                health_status[server_type] = await client.get_health()
            except Exception as e:
                health_status[server_type] = {"status": "error", "error": str(e)}
        
        return health_status
    
    async def close_all(self) -> None:
        """Close all client connections"""
        async with self._lock:
            for client in self._clients.values():
                await client.close()
            self._clients.clear()
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close_all()


# Global client pool instance
_global_client_pool: Optional[MCPClientPool] = None


def initialize_client_pool() -> MCPClientPool:
    """Initialize global MCP client pool"""
    global _global_client_pool
    _global_client_pool = MCPClientPool()
    return _global_client_pool


def get_client_pool() -> Optional[MCPClientPool]:
    """Get global MCP client pool"""
    return _global_client_pool


async def call_tool(server_type: MCPServerType, tool_name: str,
                   arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to call a tool via the global pool
    
    Args:
        server_type: Type of server
        tool_name: Name of the tool
        arguments: Tool arguments
        
    Returns:
        Tool result
    """
    pool = get_client_pool()
    if not pool:
        raise RuntimeError("Client pool not initialized. Call initialize_client_pool() first.")
    return await pool.call_tool(server_type, tool_name, arguments)
