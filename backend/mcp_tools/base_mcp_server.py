"""
Base MCP Server
Foundation class for all MCP server implementations
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Callable, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

from .mcp_types import Tool, Resource, ToolInput, ToolUseBlock, ToolResultBlock
from .mcp_types import ToolNotFoundError, InvalidInputError, MCPServerError
from .utils import format_error, validate_input, extract_field, sanitize_input, log_operation

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    """Configuration for MCP server"""
    name: str
    description: str
    version: str = "1.0.0"
    host: str = "localhost"
    port: int = 8000
    debug: bool = False
    max_concurrent_requests: int = 100
    request_timeout_seconds: int = 30


class BaseMCPServer(ABC):
    """
    Base class for all MCP servers
    Provides common functionality for all agent MCP servers
    """

    def __init__(self, config: MCPServerConfig):
        """Initialize MCP server"""
        self.config = config
        self.tools: Dict[str, Tool] = {}
        self.resources: Dict[str, Resource] = {}
        self.is_running = False
        self._request_counter = 0
        self._error_log = []
        
        logger.info(f"Initializing {config.name} MCP Server v{config.version}")

    def register_tool(
        self,
        name: str,
        description: str,
        handler: Callable,
        input_schema: Dict[str, Any],
        required_fields: List[str] = None
    ) -> None:
        """
        Register a tool that clients can call
        
        Args:
            name: Tool name (e.g., 'create_task')
            description: Human-readable description
            handler: Async function to handle tool calls
            input_schema: JSON schema for input validation
            required_fields: List of required input fields
        """
        tool = Tool(
            name=name,
            description=description,
            inputSchema=ToolInput(
                type="object",
                properties=input_schema.get("properties", {}),
                required=required_fields or input_schema.get("required", [])
            ),
            handler=handler
        )
        
        self.tools[name] = tool
        logger.info(f"Registered tool: {name}")

    def register_resource(
        self,
        uri: str,
        name: str,
        description: str,
        handler: Callable
    ) -> None:
        """
        Register a resource that clients can access
        
        Args:
            uri: Resource URI (e.g., '/tasks/{task_id}')
            name: Resource name
            description: Resource description
            handler: Async function to handle resource requests
        """
        resource = Resource(
            uri=uri,
            name=name,
            description=description,
            handler=handler
        )
        
        self.resources[uri] = resource
        logger.info(f"Registered resource: {uri}")

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool call
        
        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool
            
        Returns:
            Tool result as dictionary
            
        Raises:
            ToolNotFoundError: If tool doesn't exist
            InvalidInputError: If arguments are invalid
        """
        self._request_counter += 1
        
        # Validate tool exists
        if tool_name not in self.tools:
            error = f"Tool not found: {tool_name}"
            logger.error(error)
            log_operation("call_tool", self.config.name, "error", {"tool": tool_name, "error": error})
            raise ToolNotFoundError(error)
        
        tool = self.tools[tool_name]
        
        # Sanitize input
        try:
            safe_arguments = sanitize_input(arguments)
        except Exception as e:
            error = f"Input sanitization failed: {str(e)}"
            logger.error(error)
            raise InvalidInputError(error)
        
        # Validate input
        if tool.inputSchema.required:
            if not validate_input(safe_arguments, tool.inputSchema.required):
                missing = [f for f in tool.inputSchema.required if f not in safe_arguments]
                error = f"Missing required fields: {missing}"
                logger.error(error)
                log_operation("call_tool", self.config.name, "error", {"tool": tool_name, "missing_fields": missing})
                raise InvalidInputError(error)
        
        # Call handler
        try:
            log_operation("call_tool", self.config.name, "started", {"tool": tool_name})
            
            result = await asyncio.wait_for(
                tool.handler(**safe_arguments),
                timeout=self.config.request_timeout_seconds
            )
            
            log_operation("call_tool", self.config.name, "completed", {"tool": tool_name})
            return {
                "status": "success",
                "result": result,
                "tool": tool_name,
                "timestamp": datetime.now().isoformat()
            }
            
        except asyncio.TimeoutError:
            error = f"Tool execution timeout: {tool_name}"
            logger.error(error)
            log_operation("call_tool", self.config.name, "timeout", {"tool": tool_name})
            raise MCPServerError(error)
            
        except Exception as e:
            error_info = format_error(e)
            logger.error(f"Tool execution error: {error_info}")
            log_operation("call_tool", self.config.name, "error", {"tool": tool_name, "error": str(e)})
            raise MCPServerError(f"Tool execution failed: {str(e)}")

    async def get_resource(self, uri: str) -> Dict[str, Any]:
        """
        Get a resource
        
        Args:
            uri: Resource URI
            
        Returns:
            Resource content
            
        Raises:
            ToolNotFoundError: If resource doesn't exist
        """
        if uri not in self.resources:
            raise ToolNotFoundError(f"Resource not found: {uri}")
        
        resource = self.resources[uri]
        
        try:
            result = await resource.handler()
            return {
                "status": "success",
                "uri": uri,
                "content": result,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Resource access error: {e}")
            raise MCPServerError(f"Failed to access resource: {str(e)}")

    def list_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": {
                    "type": tool.inputSchema.type,
                    "properties": tool.inputSchema.properties,
                    "required": tool.inputSchema.required
                }
            }
            for tool in self.tools.values()
        ]

    def list_resources(self) -> List[Dict[str, Any]]:
        """Get list of available resources"""
        return [
            {
                "uri": resource.uri,
                "name": resource.name,
                "description": resource.description
            }
            for resource in self.resources.values()
        ]

    async def start(self, port: int = None) -> None:
        """
        Start the MCP server
        Must be implemented by subclasses for specific transport
        """
        self.is_running = True
        port = port or self.config.port
        logger.info(f"Started {self.config.name} on port {port}")

    async def stop(self) -> None:
        """Stop the MCP server"""
        self.is_running = False
        logger.info(f"Stopped {self.config.name}")

    def get_health(self) -> Dict[str, Any]:
        """Get server health status"""
        return {
            "status": "healthy" if self.is_running else "stopped",
            "server": self.config.name,
            "uptime_requests": self._request_counter,
            "tools_registered": len(self.tools),
            "resources_registered": len(self.resources),
            "timestamp": datetime.now().isoformat()
        }

    def get_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent errors"""
        return self._error_log[-limit:]

    def log_error(self, error: Exception, context: Dict[str, Any] = None) -> None:
        """Log an error for audit trail"""
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "error": str(error),
            "type": type(error).__name__,
            "context": context or {}
        }
        self._error_log.append(error_entry)
        if len(self._error_log) > 100:  # Keep last 100 errors
            self._error_log = self._error_log[-100:]

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize server-specific components
        Must be implemented by subclasses
        """
        pass
